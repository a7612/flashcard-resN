#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import csv
import uuid
import random
import string
import datetime
import getpass
import re
import logging
import time
from logging.handlers import TimedRotatingFileHandler
from functools import lru_cache
from types import SimpleNamespace

# --- import user config: keep expecting same uppercase variables (colors, dirs, limits) ---
from config import *  # keep the existing config pattern

# Build simple CONFIG namespace to avoid repeated attribute lookups on module
_CONFIG = SimpleNamespace(**{k: v for k, v in globals().items() if k.isupper()})

# --- Ensure dirs exist (do once) ---
os.makedirs(_CONFIG.LOG_DIR, exist_ok=True)
os.makedirs(_CONFIG.EXPORT_DIR, exist_ok=True)
os.makedirs(_CONFIG.QUESTIONS_DIR, exist_ok=True)

# --- Logging: use timed rotating handler (daily) to avoid manual open/append ---
logger = logging.getLogger("flashcard")
logger.setLevel(logging.INFO)
log_file = os.path.join(_CONFIG.LOG_DIR, f"flashcard.log")
if not logger.handlers:
    handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=14, encoding="utf-8")
    handler.setFormatter(logging.Formatter('%(asctime)s | %(user)s | %(action)s | %(detail)s'))
    logger.addHandler(handler)

def log_action(action: str, detail: str = ""):
    """Log with structured info and current user. Uses logging handler above."""
    user = current_user()
    # Use extra to inject into format
    logger.info("", extra={"user": user, "action": action, "detail": detail})

def timestamp_now():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def current_user():
    try:
        return getpass.getuser()
    except Exception:
        return "unknown_user"

class FlashCard:
    def __init__(self, qdir=None):
        self.qdir = qdir or _CONFIG.QUESTIONS_DIR
        os.makedirs(self.qdir, exist_ok=True)

        # Prebuild color_map once for fast replacement
        self.color_map = self._build_color_map()
        # compile token regex for speed: matches {TOKEN}
        self._color_token_re = re.compile(r"\{[A-Z0-9_]+\}")

        # small in-memory caches
        self._file_counts_cache = {}  # filename -> count (invalidated on writes)

    # ----------------- Utilities -----------------
    @staticmethod
    def clearsrc():
        if _CONFIG.CLEAR_SCREEN:
            os.system("cls" if os.name == "nt" else "clear")

    def _build_color_map(self):
        import config as cfg
        return {
            f"{{{k}}}": v
            for k, v in vars(cfg).items()
            if k.isupper() and isinstance(v, str) and v.startswith("\033")
        }

    def _replace_colors(self, text):
        """Fast replacement of {TOKEN} -> ANSI using prebuilt map and compiled regex."""
        # 1. Chống crash nếu text là None hoặc rỗng
        if not text:
            return ""

        # 2. XỬ LÝ LỖI TUPLE (Fix lỗi bạn đang gặp)
        # Nếu lỡ truyền cả một dòng (Tuple) vào, ta chỉ lấy phần tử nội dung (thường là index 1)
        if isinstance(text, (tuple, list)):
            # Thường row là (id, back, front...), ta lấy index 1 (back) hoặc index 0 tùy cấu trúc
            # Ở đây mình ép về chuỗi của phần tử đầu tiên để an toàn
            text = str(text[1]) if len(text) > 1 else str(text[0])
        else:
            # Nếu là kiểu dữ liệu khác (int, float...), cũng ép về string luôn
            text = str(text)

        # 3. Thực hiện chuẩn hóa như bình thường
        text = text.replace("\\n", "\n").replace("\\t", "\t")
        text = text.replace(".\n", "\n")        
        text = text.replace("{BACKSLASH}", "\\")
        
        # 4. Swap tokens
        return self._color_token_re.sub(lambda m: self.color_map.get(m.group(0), m.group(0)), text)

    # ----------------- File listing -----------------
    def _files(self):
        return [f for f in os.listdir(self.qdir) if f.endswith(".csv")]

    def _list_files(self, show=True):
        files = self._files()
        if not files:
            if show: print("⚠️ Không có file câu hỏi.")
            return []

        if show:
            # 1. Tìm độ dài của tên file dài nhất để làm chuẩn (min là 25)
            max_name_len = max(len(f) for f in files) if files else 25
            print(f"{BRIGHT_BLACK}{'─' * (max_name_len + max_name_len%4)}{RESET}")
            print(f"{BRIGHT_GREEN}📂 DANH SÁCH BỘ ĐỀ:{RESET}")
            print(f"{BRIGHT_BLACK}{'─' * (max_name_len + max_name_len%4)}{RESET}")
            # 2. Render danh sách với padding động
            out = []
            for i, f in enumerate(files, 1):
                count = self._count_questions_cached(f)
                if count >= 64:
                    count_color = BRIGHT_GREEN  # Hoàn hảo
                    status_icon = "✅"
                elif count >= 32:
                    count_color = BRIGHT_CYAN # Trung bình
                    status_icon = "🟡"
                elif count >= 16:
                    count_color = BRIGHT_YELLOW # Trung bình
                    status_icon = "🟡"
                elif count >= 8:
                    count_color = BRIGHT_MAGENTA # Trung bình
                    status_icon = "🟡"
                else:
                    count_color = BRIGHT_RED   # Ít câu hỏi
                    status_icon = "❗"
                # Dùng f-string với biến độ dài {max_name_len}
                # :>2 là căn phải số thứ tự, :<{max_name_len} là căn trái tên file
                line = (f" {BRIGHT_BLUE}{i:>2}.{RESET} "
                        f"{count_color}{f:<{max_name_len}}{RESET} "
                        f"{BRIGHT_BLACK}─{RESET} "
                        f"({count_color}{count:>5} câu{RESET})")
                        # f"{status_icon} ({count_color}{count:>3}{RESET} {BRIGHT_WHITE}câu{RESET})")
                out.append(line)
            
            print("\n".join(out))
            print(f"{BRIGHT_BLACK}{'─' * (max_name_len + max_name_len%4)}{RESET}")
            
        return files

    def _count_questions_cached(self, fname):
        if fname in self._file_counts_cache:
            return self._file_counts_cache[fname]
        
        path = os.path.join(self.qdir, fname)
        try:
            with open(path, encoding="utf-8-sig") as f:
                # Đếm tất cả dòng trừ dòng tiêu đề, đảm bảo không âm
                count = max(0, sum(1 for _ in f) - 1)
        except Exception:
            count = 0

        self._file_counts_cache[fname] = count
        return count

    # ----------------- CSV loading/saving (cached) -----------------
    @lru_cache(maxsize=64)
    def _load_flashcard(self, path):
        if not os.path.exists(path): return []
        with open(path, encoding="utf-8-sig") as f:
            src = os.path.basename(path)
            # Đảm bảo trả về ĐÚNG 6 giá trị theo thứ tự: id, a, q, d, r, src
            return [
                (
                    r.get("id", "").strip() or str(uuid.uuid4()), 
                    r.get("answer", "").strip(),
                    r.get("question", "").strip(),
                    r.get("hint", "").strip(),
                    r.get("desc", "").strip(),
                    src
                )
                for r in csv.DictReader(f)
            ]
    def _save_flashcard(self, path, data):
        """Save sorted data and invalidate caches (LRU cache + counts)."""
        data_sorted = sorted(data, key=lambda x: (x[1].lower().strip(), x[2].lower().strip()))
        # data_sorted = sorted(data, key=lambda x: (x[2].lower().strip(), x[1].lower().strip()))
        # data_sorted = sorted(data, key=lambda x: (x[3].lower().strip(), x[1].lower().strip()))
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "answer", "question", "hint", "desc"])
            for row in data_sorted:
                writer.writerow(row[:5])

        # invalidate caches
        try:
            self._load_flashcard.cache_clear()
        except Exception:
            pass
        # invalidate count cache for this filename
        basename = os.path.basename(path)
        if basename in self._file_counts_cache:
            del self._file_counts_cache[basename]

    # ----------------- Small input helper to avoid repeating loops -----------------
    def _safe_input(self, prompt, validator=None, allow_exit=True, lower=False):
        while True:
            try:
                v = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                return None
            if allow_exit and (v.lower() == "/exit"): return None
            if lower: v_check = v.lower()
            else: v_check = v
            if validator is None: return v
            res = validator(v_check)
            if isinstance(res, tuple):
                ok, val = res
            else:
                ok, val = bool(res), v
            if ok:
                return val
            print("⚠️ Lựa chọn không hợp lệ, nhập lại đi!")
    # ----------------- File choose / show / CRUD -----------------
    def _choose_file(self, action="chọn"):
        files = self._list_files()
        if not files:
            return None
        prompt = f"\n👉 Nhập ID để {action} (hoặc gõ /exit để thoát): "
        def validator(x):
            if x.isdigit() and 0 < int(x) <= len(files):
                return True, os.path.join(self.qdir, files[int(x) - 1])
            return False
        return self._safe_input(prompt, validator=validator)

    def _show(self, path, show=True):
        data = self._load_flashcard(path)
        if not data:
            if show:
                print("❌ File trống.")
            return []
        if show:
            print("\n📋 DANH SÁCH CÂU HỎI:")
            for i, (_, a, q, d, r, source) in enumerate(data, 1):
                q_disp = self._replace_colors(q)
                a_disp = self._replace_colors(a)
                d_disp = self._replace_colors(d)
                r_disp = self._replace_colors(r)
                print(f"\n{BRIGHT_CYAN}{i:>2}){'-'*60}\n\n❓\tCâu hỏi: {RESET}{q_disp}")
                print(f"{GREEN}➤\tĐáp án: {RESET}{a_disp}")
                if d_disp:
                    print(f"{YELLOW}💡\tGợi ý: {RESET}\n{d_disp}{RESET}")
                if r_disp:
                    print(f"{CYAN}🔗\tMô Tả: {RESET}\n{r_disp}{RESET}")
                
        return data

    def _ask_index(self, data, action="chọn"):
        if not data:
            return None
        def validator(x):
            if x.isdigit() and 1 <= int(x) <= len(data):
                return True, int(x)-1
            return False, None
        return self._safe_input(f"\n🔢 Nhập ID để {action} (hoặc nhập /exit để thoát): ", validator=validator)

    # CRUD split into smaller ops to avoid repeat-loading
    def _add_question(self, path):
        data = list(self._load_flashcard(path))
        while True:
            self._show(path, show=True)
            q = self._safe_input(f"\n❓ Nhập câu hỏi (hoặc nhập /exit để thoát):{RESET} ")
            if q is None: break
            a = self._safe_input(f"✅ Nhập đáp án (hoặc nhập /exit để thoát):{RESET} ")
            if a is None: break
            if not q or not a:
                continue
            # check duplicate
            ql = q.lower().strip()
            al = a.lower().strip()
            is_dup = any(ql == old_q.lower().strip() and al == old_a.lower().strip() for _, old_a, old_q, *_ in data)
            if is_dup:
                self.clearsrc()
                print(f"{RED}⚠️ Câu hỏi đã tồn tại, bỏ qua!{RESET}")
                continue
            d = self._safe_input("💡 Gợi ý (có thể bỏ trống): ")
            r = self._safe_input("🔗 Mô Tả (có thể bỏ trống): ")
            data.append((str(uuid.uuid4()), a, q, d or "", r or ""))
            self._save_flashcard(path, data)
            log_action("ADD_Q", f"{os.path.basename(path)} | Q: {q}")
            self.clearsrc()
            print(f"{GREEN}➕ Đã thêm câu hỏi mới.{RESET}")

    def _delete_question(self, path):
        data = list(self._load_flashcard(path))
        while True:
            self._show(path)
            idx = self._ask_index(data, "xoá")
            if idx is None:
                break
            removed = data.pop(idx)
            self._save_flashcard(path, data)
            log_action("DEL_Q", f"{os.path.basename(path)} | Q: {removed[2]}")
            self.clearsrc()
            print(f"🗑️ Đã xoá: {removed[2]}")

    def _edit_question(self, path, mode="sửa"):
        data = list(self._load_flashcard(path))
        field_map = {"sửaQ": 2, "sửaA": 1, "sửaD": 3, "sửaR": 4}
        while True:
            self._show(path)
            idx = self._ask_index(data, "sửa")
            if idx is None:
                break
            entry = list(data[idx])
            if mode == "sửa":
                new_q = self._safe_input(f"❓ Câu hỏi mới (cũ: {entry[2]}): ")
                new_a = self._safe_input(f"✅ Đáp án mới (cũ: {entry[1]}): ")
                new_d = self._safe_input(f"💡 Gợi ý mới (cũ: {entry[3]}): ")
                new_r = self._safe_input(f"🔗 Mô Tả mới (cũ: {entry[4]}): ")
                entry[2] = new_q or entry[2]
                entry[1] = new_a or entry[1]
                entry[3] = new_d or entry[3]
                entry[4] = new_r or entry[4]
            else:
                fi = field_map.get(mode)
                if fi is None:
                    return
                new_val = self._safe_input(f"✏️ Nhập giá trị mới (cũ: {entry[fi]}): ")
                if new_val:
                    entry[fi] = new_val
            data[idx] = tuple(entry)
            self._save_flashcard(path, data)
            log_action("EDIT_Q", f"{os.path.basename(path)} | Q: {entry[2]}")
            self.clearsrc()
            print("✅ Đã sửa thành công.")

    def _crud(self, mode):
        path = self._choose_file(mode)
        if not path:
            return
        if mode == "thêm":
            self._add_question(path)
        elif mode == "xoá":
            self._delete_question(path)
        elif mode in ("sửa", "sửaQ", "sửaA", "sửaD", "sửaR"):
            self._edit_question(path, mode=mode)
        else:
            print("⚠️ Mode không được hỗ trợ.")

    # ----------------- Game logic (performance aware) -----------------
    def _options(self, correct, pool, n):
        # remove special tokens and correct answer from candidate pool
        pool_set = set(pool)
        pool_set.discard(correct)
        pool_set.discard("Đúng")
        pool_set.discard("Sai")
        pool = list(pool_set)
        # sample up to n-1 others and add correct
        sample = random.sample(pool, min(len(pool), max(0, n - 1)))
        sample.append(correct)
        return sample

    def _progress_bar(self, percent, width=30):
        filled = int(width * percent // 100)
        return "[" + "=" * filled + " " * (width - filled) + f"] {percent:.1f}%"

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        ql = q.lower()
        
        # 1. Xử lý câu hỏi Đúng/Sai
        if any(kw in ql for kw in _CONFIG.KEYWORD_BOOL):
            return ["Đúng", "Sai"]
        
        # 2. Xử lý theo Keyword đặc biệt trong Config
        for kw in _CONFIG.KEYWORD:
            if kw in ql:
                # group khởi tạo với đáp án đúng của câu hiện tại
                group = {a}
                for row in data:
                    # row: (id, ans, ques, hint, desc, source)
                    # Chỉ lấy đáp án từ những câu hỏi KHÁC ID hiện tại nhưng có cùng keyword
                    if row[0] != qid and kw in row[2].lower():
                        group.add(row[1])
                
                # Nếu group quá ít (không đủ n_opts), lấy thêm từ all_ans cho đủ
                if len(group) < (n_opts or 4):
                    group.update(random.sample(all_ans, min(len(all_ans), 10)))

                opts = self._options(a, list(group), n_opts)
                return [self._replace_colors(opt) for opt in dict.fromkeys(opts)]

        # 3. Mặc định lấy từ toàn bộ danh sách đáp án (nhưng lọc bỏ ID hiện tại nếu cần)
        opts = self._options(a, all_ans, n_opts)
        return [self._replace_colors(opt) for opt in dict.fromkeys(opts)]

    def _feedback(self, ok, chosen, q, a, d, r, qid):
        if ok:
            if chosen != a :
                if r:
                    print(f"\n{CYAN}🔗 Mô tả:{RESET}\n{r}")
                print(f"\n{BRIGHT_GREEN}{'O'*48}\nHAY! - {GREEN}Đáp án là: {RESET}{chosen}\n{GREEN}{'O'*48}\n")
                log_action(f"CHOSEN:{qid}", f"{chosen} - {q} Đúng + 1 điểm")
            else:
                if r:
                    print(f"\n{CYAN}🔗 Mô tả:{RESET}\n{r}")
                print(f"\n{BRIGHT_GREEN}{'O'*48}\nHAY! - {GREEN}Đáp án là: {RESET}{a}\n{GREEN}{'O'*48}\n")
                log_action(f"CHOSEN:{qid}", f"{chosen} - {q} Đúng + 1 điểm")
        else:
            if r:
                print(f"\n{CYAN}🔗 Mô tả:{RESET}\n{r}")
            print(f"\n{BRIGHT_RED}{'X'*48}\nGÀ! - {RED}Đáp án là: {RESET}{a}\n{RED}{'X'*48}\n")
            log_action(f"CHOSEN:{qid}", f"{chosen} - {q} Sai")

    def _export_results(self, results, score, total):
        wrong = total - score
        percent = (score / total * 100) if total else 0.0
        print("\n" + "=" * 60)
        print(f"{BLUE}🎯 BẢNG ĐIỂM CHI TIẾT{RESET}")
        print(f"{'#':>3}  {'RESULT':^8}  {'CORRECT':^20}")
        print("-" * 60)
        for r in results:
            res_sym = f"{GREEN}✅{RESET}" if r["ok"] else f"{RED}❌{RESET}"
            print(f"{RESET}{r['index']:>3})  {res_sym:^8}   {r['correct']:<20}{RESET}")
        print("-" * 60)
        print(f"{GREEN}✅ Đúng : {score}{RESET}    {RED}❌ Sai : {wrong}{RESET}    {CYAN}📊 Tỉ lệ: {percent:.1f}%{RESET}")
        print(self._progress_bar(percent))

        # Export CSV
        csv_path = os.path.join(_CONFIG.EXPORT_DIR, f"quiz_results_{timestamp_now()}.csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", datetime.datetime.now().isoformat()])
            w.writerow(["user", current_user()])
            w.writerow(["total_questions", total])
            w.writerow(["score", score])
            w.writerow(["wrong", wrong])
            w.writerow(["percent", f"{percent:.1f}"])
            w.writerow([])
            w.writerow(["idx", "question", "correct", "ok", "hint", "Mô Tả"])
            for r in results:
                w.writerow([r["index"], r["question"], r["correct"], r["ok"], r["hint"], r.get("desc", "")])
        print(f"{BRIGHT_GREEN}✅ Đã export kết quả: {csv_path}{RESET}")

    def _check_answer(self, chosen, qid, data):
        # 1. Tìm đúng câu hỏi trong data dựa trên ID
        target_card = next((row for row in data if row[0] == qid), None)
        if not target_card: return False
        
        # 2. Lấy đáp án đúng (raw) từ data
        correct_ans_raw = target_card[1]
        
        # 3. Hàm làm sạch "siêu cấp": Xóa ANSI + Xóa {TOKEN}
        def _super_clean(text):
            if not text: return ""
            # Xóa mã ANSI terminal (\x1B...)
            ansi_re = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            text = ansi_re.sub('', str(text))
            # Xóa các token màu do bạn định nghĩa (ví dụ: {BRIGHT_GREEN})
            text = re.sub(r'\{[A-Z0-9_]+\}', '', text)
            # Loại bỏ khoảng trắng, đưa về chữ thường và xóa dấu chấm cuối
            return text.strip().lower().rstrip('.')

        # 4. So sánh 2 bên sau khi đã được "tắm rửa" sạch sẽ
        return _super_clean(chosen) == _super_clean(correct_ans_raw)

    def _quiz(self, data, n_opts=None, max_qs=None, source=None):
        if not data:
            print("❌ Không có dữ liệu câu hỏi.")
            return

        # 1. Chuẩn bị pool câu hỏi (Lấy mẫu ngẫu nhiên nếu có max_qs)
        pool = data[:] if not max_qs else random.sample(data, min(max_qs, len(data)))
        
        # Quan trọng: all_ans phải chứa cả ID để tránh trùng lặp nội dung nhưng khác ID
        # Cấu trúc data giả định: (qid, a, q, d, r, source)
        all_ans = data[:] 
        
        results = []
        score = 0
        total_qs = len(pool)

        for i, (qid, a, q, d, r, src) in enumerate(pool, 1):
            self.clearsrc()
            print(f"{BRIGHT_MAGENTA}📊 Tiến độ: {i}/{total_qs} | {BRIGHT_GREEN}Đúng: {score}{RESET}")
            print(f"{BRIGHT_BLUE}{'='*50}{RESET}")

            # Chuẩn hóa hiển thị (render màu và xuống dòng)
            q_disp = self._replace_colors(q)
            a_disp = self._replace_colors(a) # Đây là đáp án đúng CỦA CÂU NÀY
            d_disp = self._replace_colors(d) if d else ""
            r_disp = self._replace_colors(r) if r else ""

            print(f"{RESET}Câu hỏi {i} [ID: {BRIGHT_BLACK}{qid}{RESET}]:")
            if _CONFIG.DEBUG:
                print(f"{BRIGHT_BLACK}Nguồn: {src}{RESET}")
            
            print(f"\n{q_disp}\n")

            # 2. TỐI ƯU OPTIONS: Lấy đáp án nhiễu dựa trên ID để không bị lẫn
            # Hàm _get_options mới nên nhận vào qid của câu hiện tại để loại trừ chính xác
            opts = self._get_options(qid, q, a, data, all_ans, n_opts)
            random.shuffle(opts)
            
            keys = string.ascii_uppercase[:len(opts)]
            mapping = dict(zip(keys, opts))

            for k, v in mapping.items():
                # v ở đây là nội dung text của đáp án
                print(f"  {BRIGHT_CYAN}{k}.{RESET} {v}")

            print(f"\n{BRIGHT_BLUE}{'='*50}{RESET}")

            # 3. Vòng lặp nhận input
            while True:
                user_input = input(f"👉 Trả lời ({BRIGHT_YELLOW}A-{keys[-1]}{RESET}), '?' (Gợi ý), hoặc 'exit': ").strip().upper()
                
                if user_input == 'EXIT':
                    self._export_results(results, score, len(results))
                    return

                if user_input == '?':
                    # Đảm bảo d_disp là của qid hiện tại (đã xử lý ở trên)
                    print(f"\n{YELLOW}💡 Gợi ý (ID: {qid}):{RESET}\n{d_disp}\n")
                    continue

                if user_input in mapping:
                    chosen_text = mapping[user_input]
                    break
                
                print(f"{BRIGHT_RED}❌ Lựa chọn không hợp lệ.{RESET}")

            # 4. KIỂM TRA ĐÁP ÁN: So sánh trực tiếp nội dung text đã chọn với a_disp của câu hiện tại
            # Vì ta đã xác định a_disp theo qid ở đầu vòng lặp, nên so sánh này là tuyệt đối đúng
            ok = self._check_answer(chosen_text, qid, data) # So sánh text thô (a) chưa qua render màu
            
            if ok:
                score += 1
            
            # Lưu kết quả khớp 100% với qid
            results.append({
                "index": i, "question": q_disp, "correct": a_disp,
                "hint": d_disp, "desc": r_disp, "ok": ok, "qid": qid
            })

            # 5. FEEDBACK: Truyền thẳng qid vào để hàm feedback không bốc nhầm data
            self._feedback(ok, chosen_text, q_disp, a_disp, d_disp, r_disp, qid)
            
            if i < total_qs:
                input(f"\n{BRIGHT_BLACK}Nhấn Enter để qua câu tiếp theo...{RESET}")

        self._export_results(results, score, len(results))

    def play_file(self):
        print(f"{'='*16} Chơi theo file {'='*16}\n")
        path = self._choose_file("chơi")
        menu_text = (
            f"{BRIGHT_WHITE}┌{'─'*60}┐\n"
            f"│{BRIGHT_CYAN}{' CHỌN ĐỘ KHÓ QUYẾT CHIẾN ':^60}{BRIGHT_WHITE}│\n"
            f"├{'─'*60}┤\n"
            f"│ {BRIGHT_GREEN}0 - Mặc định:{RESET} {_CONFIG.MAX_GENERATE_NORMAL_QUESTIONS} thẻ, {_CONFIG.MAX_GENERATE_NORMAL_ANSWERS} đáp án                             {BRIGHT_WHITE}│\n"
            f"│ {BRIGHT_BLUE}1 - Dễ:{RESET} 10 thẻ, 1 đáp án {BRIGHT_BLACK}(Thích hợp để học){RESET}                {BRIGHT_WHITE}│\n"
            f"│ {BRIGHT_YELLOW}2 - Trung bình:{RESET} 20 thẻ, 4 đáp án {BRIGHT_BLACK}(Khuyến nghị){RESET}             {BRIGHT_WHITE}│\n"
            f"│ {BRIGHT_RED}3 - Khó:{RESET} 50 thẻ, 6 đáp án                                  {BRIGHT_WHITE}│\n"
            f"│ {BRIGHT_MAGENTA}4 - Hardcore:{RESET} 100 thẻ, 8 ~ 24 đáp án                       {BRIGHT_WHITE}│\n"
            f"└{'─'*60}┘\n"
            f"\n👉 {BRIGHT_YELLOW}Lựa chọn của bạn{RESET} (hoặc {BRIGHT_RED}'/exit'{RESET} để thoát): "
        )

        difficult_choice = int(input(menu_text))
        if difficult_choice == 0:
            if path:
                self._quiz(self._load_flashcard(path), n_opts=_CONFIG.MAX_GENERATE_NORMAL_ANSWERS, max_qs=_CONFIG.MAX_GENERATE_NORMAL_QUESTIONS)
        if difficult_choice == 1:            
            if path:
                self._quiz(self._load_flashcard(path), n_opts=1, max_qs=10)
        if difficult_choice == 2:
            if path:
                self._quiz(self._load_flashcard(path), n_opts=4, max_qs=20)
        if difficult_choice == 3:
            if path:
                self._quiz(self._load_flashcard(path), n_opts=6, max_qs=50)
        if difficult_choice == 4:
            if path:
                self._quiz(self._load_flashcard(path), n_opts=random.randint(8, 24), max_qs=100)

    def play_all(self):
        print(f"{'='*16} Chơi ngẫu nhiên {'='*16}\n")
        data = []
        for f in self._files():
            data.extend(self._load_flashcard(os.path.join(self.qdir, f)))
        menu_text = (
            f"{BRIGHT_WHITE}┌{'─'*60}┐\n"
            f"│{BRIGHT_CYAN}{' CHỌN ĐỘ KHÓ QUYẾT CHIẾN ':^60}{BRIGHT_WHITE}│\n"
            f"├{'─'*60}┤\n"
            f"│ {BRIGHT_GREEN}0 - Mặc định:{RESET} {_CONFIG.MAX_GENERATE_NORMAL_QUESTIONS} thẻ, {_CONFIG.MAX_GENERATE_NORMAL_ANSWERS} đáp án                             {BRIGHT_WHITE}│\n"
            f"│ {BRIGHT_BLUE}1 - Dễ:{RESET} 10 thẻ, 1 đáp án {BRIGHT_BLACK}(Thích hợp để học){RESET}                {BRIGHT_WHITE}│\n"
            f"│ {BRIGHT_YELLOW}2 - Trung bình:{RESET} 20 thẻ, 4 đáp án {BRIGHT_BLACK}(Khuyến nghị){RESET}             {BRIGHT_WHITE}│\n"
            f"│ {BRIGHT_RED}3 - Khó:{RESET} 50 thẻ, 6 đáp án                                  {BRIGHT_WHITE}│\n"
            f"│ {BRIGHT_MAGENTA}4 - Hardcore:{RESET} 100 thẻ, 8 ~ 24 đáp án                       {BRIGHT_WHITE}│\n"
            f"└{'─'*60}┘\n"
            f"\n👉 {BRIGHT_YELLOW}Lựa chọn của bạn{RESET} (hoặc {BRIGHT_RED}'/exit'{RESET} để thoát): "
        )
        difficult_choice = int(input(menu_text))
        self.clearsrc()
        if difficult_choice == 0:
            self._quiz(data, n_opts=_CONFIG.MAX_GENERATE_ALL_ANSWERS, max_qs=_CONFIG.MAX_GENERATE_ALL_QUESTIONS)
        if difficult_choice == 1:            
            self._quiz(data, n_opts=1, max_qs=10)
        if difficult_choice == 2:
            self._quiz(data, n_opts=4, max_qs=20)
        if difficult_choice == 3:
            self._quiz(data, n_opts=6, max_qs=50)
        if difficult_choice == 4:
            self._quiz(data, n_opts=random.randint(8, 24), max_qs=100)
        
            
    # ----------------- File management -----------------
    def _create_file(self, act):
        name = self._safe_input("📄 Nhập tên file mới (không cần .csv): ")
        if not name:
            return
        path = os.path.join(self.qdir, f"{name}.csv")
        if os.path.exists(path):
            print("⚠️ File đã tồn tại.")
        else:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(["id", "answer", "question", "hint", "desc"])
            log_action(act, path)
            self.clearsrc()
            print(f"✅ Đã tạo {name}.csv")

    def _delete_file(self, act):
        path = self._choose_file("xoá")
        if path and self._safe_input(f"❓ Xoá {os.path.basename(path)} (y/n)\n> ", validator=lambda x: (x.lower() == "y", x)) == "y":
            os.remove(path)
            log_action(act, path)
            # invalidate caches
            self._file_counts_cache.pop(os.path.basename(path), None)
            try:
                self._load.cache_clear()
            except Exception:
                pass
            self.clearsrc()
            print(f"🗑️ Đã xoá file. {path}")

    def _rename_file(self, act):
        path = self._choose_file("đổi tên")
        if not path:
            return
        new = self._safe_input("✏️ Nhập tên mới\n> ")
        if not new:
            return
        newpath = os.path.join(self.qdir, f"{new}.csv")
        os.rename(path, newpath)
        log_action(act, f"{path} -> {newpath}")
        # adjust caches
        self._file_counts_cache.pop(os.path.basename(path), None)
        self._file_counts_cache.pop(os.path.basename(newpath), None)
        try:
            self._load.cache_clear()
        except Exception:
            pass
        self.clearsrc()
        print(f"✅ Đã đổi tên file. {path}")

    # ----------------- Menus -----------------
    def show_stats(self):
        """Hiển thị tổng số file và tổng số câu hỏi trong toàn bộ kho dữ liệu."""
        files = self._files()
        # Tính tổng bằng List Comprehension để tối ưu tốc độ
        total_q = sum(self._count_questions_cached(f) for f in files)
        
        print(f"{BRIGHT_WHITE}┌{'─'*40}┐{RESET}")
        print(f"{BRIGHT_WHITE}│{BRIGHT_CYAN}{' 📊 THỐNG KÊ KHO CÂU HỎI ':^39}{BRIGHT_WHITE}│{RESET}")
        print(f"{BRIGHT_WHITE}├{'─'*40}┤{RESET}")
        print(f"{BRIGHT_WHITE}│{RESET}  📂 Tổng số bộ đề: {BRIGHT_YELLOW}{len(files):<20}{RESET}{BRIGHT_WHITE}│{RESET}")
        print(f"{BRIGHT_WHITE}│{RESET}  ❓ Tổng số câu hỏi: {BRIGHT_GREEN}{total_q:<18}{RESET}{BRIGHT_WHITE}│{RESET}")
        print(f"{BRIGHT_WHITE}└{'─'*40}┘{RESET}")

    def manage_questions(self):
        actions = {
            "1": ("thêm",   f"{RESET}{BRIGHT_GREEN}➕ Thêm nội dung"),
            "2": ("xoá",    f"{RESET}{BRIGHT_RED}🗑️ Xoá nội dung"),
            "3": ("sửa",    f"{RESET}{BRIGHT_YELLOW}✏️ Sửa toàn bộ nội dung"),
            "4": ("sửaQ",   f"{RESET}{BRIGHT_YELLOW}✏️ Sửa câu hỏi cụ thể"),
            "5": ("sửaA",   f"{RESET}{BRIGHT_YELLOW}✏️ Sửa đáp án cụ thể"),
            "6": ("sửaD",   f"{RESET}{BRIGHT_YELLOW}✏️ Sửa gợi ý cụ thể"),
            "7": ("sửaR",   f"{RESET}{BRIGHT_YELLOW}✏️ Sửa mô tả cụ thẻ"),
        }
        while True:
            self.clearsrc()
            print(f"\n{BRIGHT_YELLOW}{"@"*22}{BRIGHT_YELLOW} 📋 QUẢN LÝ NỘI DUNG  {RESET}{BRIGHT_YELLOW}{"@"*22}{RESET}")
            self.show_stats()
            # print(f"\n{BRIGHT_YELLOW}Các chức năng hiện tại:\n{RESET}")
            [print(f"{BRIGHT_YELLOW} {k}) {label}{RESET}") for k, (_, label) in actions.items()]
            ch = input(f"\n{BRIGHT_CYAN}👉 Nhập lựa chọn hoặc nhập {BRIGHT_RED}/exit{BRIGHT_CYAN} để quay lại: {RESET}").strip().lower()
            self.clearsrc()
            if ch == "/exit":
                break
            if ch in actions:
                self._crud(actions[ch][0])
            else:
                print("⚠️ Lựa chọn không hợp lệ.")

    def manage_files(self):
        actions = {
            "1": ("CREATE_FILE", f"➕ {BRIGHT_GREEN}Tạo file{RESET}", self._create_file),
            "2": ("DELETE_FILE", f"🗑️ {BRIGHT_RED}Xoá file{RESET}", self._delete_file),
            "3": ("RENAME_FILE", f"✏️ {BRIGHT_YELLOW}Đổi tên file{RESET}", self._rename_file),
        }
        while True:
            try:
                print(f"\n{BRIGHT_CYAN}{"@"*22}{BRIGHT_GREEN} 📂 QUẢN LÝ FILE  {RESET}{BRIGHT_CYAN}{"@"*22}{RESET}")
                self.show_stats()
                self._list_files()
                # print(f"\n{BRIGHT_CYAN}Các chức năng hiện tại:\n{RESET}")
                [print(f"{BRIGHT_CYAN} {k}) {label}{RESET}") for k, (_, label, _) in actions.items()]
                ch = input(f"\n{BRIGHT_CYAN}👉 Nhập lựa chọn hoặc nhập {BRIGHT_RED}/exit{BRIGHT_CYAN} để quay lại: {RESET}").strip().lower()
                if ch == "/exit":
                    break
                if ch in actions:
                    act, _, func = actions[ch]
                    func(act)
                else:
                    print("⚠️ Lựa chọn không hợp lệ.")
            except FileNotFoundError:
                break

    def menu(self):
        actions = {
            "1": (self.play_file, f"{BRIGHT_GREEN}🎯 Chơi theo bộ{RESET}"),
            "2": (self.play_all, f"{BRIGHT_GREEN}🌍 Chơi tất cả{RESET}"),
            "3": (self.manage_questions, f"{BRIGHT_YELLOW}📋 Quản lý câu hỏi{RESET}"),
            "4": (self.manage_files, f"{BRIGHT_YELLOW}📂 Quản lý file{RESET}"),
            "0": (lambda: print(f"{BRIGHT_RED}👋 Tạm biệt!"), f"{BRIGHT_RED}🚪 Thoát{RESET}"),
        }
        while True:
            print(f"{BRIGHT_BLUE}{"@"*22} 📚 FLASHCARD QUIZ GAME {"@"*22}{RESET}")
            self.show_stats()
            for k, (_, label) in actions.items():
                print(f" {k}) {label}")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch in actions:
                self.clearsrc()
                log_action("MENU", f"{ch}:{actions[ch][1]}")
                if ch == "0": return
                actions[ch][0]()
            else:
                self.clearsrc()
                print("⚠️ Sai lựa chọn.")

# Entry
if __name__ == "__main__":
    FlashCard().menu()