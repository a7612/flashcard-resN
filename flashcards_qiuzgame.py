#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimized FlashCard CLI (performance-focused)
- Caches CSV loads
- Uses logging module with daily rotation
- Precompiled color token replacement
- Minimized redundant I/O
- Small helper utilities for repeated patterns
"""

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

    def _replace_colors(self, text: str):
        """Fast replacement of {TOKEN} -> ANSI using prebuilt map and compiled regex."""
        if not text:
            return text
        # Replace escaped sequences first
        text = text.replace("\\n", "\n").replace("\\t", "\t").replace("{BACKSLASH}", "\\")
        # replace ".\n" -> "\n" (as original)
        text = text.replace(".\n", "\n")
        # swap tokens
        return self._color_token_re.sub(lambda m: self.color_map.get(m.group(0), m.group(0)), text)

    # ----------------- File listing -----------------
    def _files(self):
        return [f for f in os.listdir(self.qdir) if f.endswith(".csv")]

    def _list_files(self, show=True):
        files = self._files()
        if not files:
            if show:
                print("⚠️ Không có file câu hỏi.")
            return []
        if show:
            print(f"{BRIGHT_GREEN}\n📂 Danh sách file:{RESET}")
            for i, fname in enumerate(files, 1):
                count = self._count_questions_cached(fname)
                print(f" {i:>2}) {fname:<25} | {count} câu hỏi")
        return files

    def _count_questions_cached(self, fname):
        """Cache simple counts to avoid opening files repeatedly within short-lived runs."""
        if fname in self._file_counts_cache:
            return self._file_counts_cache[fname]
        path = os.path.join(self.qdir, fname)
        try:
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                count = sum(1 for _ in reader) - 1
                if count < 0:
                    count = 0
        except Exception:
            count = 0
        self._file_counts_cache[fname] = count
        return count

    # ----------------- CSV loading/saving (cached) -----------------
    @lru_cache(maxsize=64)
    def _load(self, path):
        """Return list of tuples from CSV. Cached for performance; clear cache on writes."""
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            src = os.path.basename(path)
            data = []
            for r in reader:
                qid = r.get("id", "").strip()
                if not qid:  # Nếu trống -> generate ID mới
                    print("Có dữ liệu thiếu ID. Đang bổ sung... ")
                    qid = str(uuid.uuid4())
                data.append((
                    qid,
                    r.get("answer", "").strip(),
                    r.get("question", "").strip(),
                    r.get("desc", "").strip(),
                    r.get("ref", "").strip(),
                    src
                ))
            return data

    def _save(self, path, data):
        """Save sorted data and invalidate caches (LRU cache + counts)."""
        data_sorted = sorted(data, key=lambda x: (x[1].lower().strip(), x[2].lower().strip()))
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "answer", "question", "desc", "ref"])
            for row in data_sorted:
                writer.writerow(row[:5])

        # invalidate caches
        try:
            self._load.cache_clear()
        except Exception:
            pass
        # invalidate count cache for this filename
        basename = os.path.basename(path)
        if basename in self._file_counts_cache:
            del self._file_counts_cache[basename]

    # ----------------- Small input helper to avoid repeating loops -----------------
    def _safe_input(self, prompt, validator=None, allow_exit=True, lower=False):
        """
        Prompt until validator returns True (validator receives raw input).
        Validator returns (ok, transformed_value) or boolean True.
        """
        while True:
            try:
                v = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                return None
            if allow_exit and (v.lower() == "exit()"):
                return None
            if lower:
                v_check = v.lower()
            else:
                v_check = v
            if validator is None:
                return v
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
        prompt = f"\n👉 Nhập ID để {action} (hoặc gõ exit() để thoát): "
        def validator(x):
            if x.isdigit() and 0 < int(x) <= len(files):
                return True, os.path.join(self.qdir, files[int(x) - 1])
            return False
        return self._safe_input(prompt, validator=validator)

    def _show(self, path, show=True):
        data = self._load(path)
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
                    print(f"{YELLOW}💡\tMô tả: {RESET}\n\n{d_disp}{RESET}")
                if r_disp:
                    print(f"{CYAN}🔗\tReference: {RESET}\n\n{r_disp}{RESET}")
                
        return data

    def _ask_index(self, data, action="chọn"):
        if not data:
            return None
        def validator(x):
            if x.isdigit() and 1 <= int(x) <= len(data):
                return True, int(x)-1
            return False, None
        return self._safe_input(f"\n🔢 Nhập ID để {action} (hoặc nhập exit() để thoát): ", validator=validator)

    # CRUD split into smaller ops to avoid repeat-loading
    def _add_question(self, path):
        data = list(self._load(path))
        while True:
            self._show(path, show=True)
            q = self._safe_input(f"\n❓ Nhập câu hỏi (hoặc nhập exit() để thoát):{RESET} ")
            if q is None: break
            a = self._safe_input(f"✅ Nhập đáp án (hoặc nhập exit() để thoát):{RESET} ")
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
            d = self._safe_input("💡 Mô tả (có thể bỏ trống): ")
            r = self._safe_input("🔗 Reference (có thể bỏ trống): ")
            data.append((str(uuid.uuid4()), a, q, d or "", r or ""))
            self._save(path, data)
            log_action("ADD_Q", f"{os.path.basename(path)} | Q: {q}")
            self.clearsrc()
            print(f"{GREEN}➕ Đã thêm câu hỏi mới.{RESET}")

    def _delete_question(self, path):
        data = list(self._load(path))
        while True:
            self._show(path)
            idx = self._ask_index(data, "xoá")
            if idx is None:
                break
            removed = data.pop(idx)
            self._save(path, data)
            log_action("DEL_Q", f"{os.path.basename(path)} | Q: {removed[2]}")
            self.clearsrc()
            print(f"🗑️ Đã xoá: {removed[2]}")

    def _edit_question(self, path, mode="sửa"):
        data = list(self._load(path))
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
                new_d = self._safe_input(f"💡 Mô tả mới (cũ: {entry[3]}): ")
                new_r = self._safe_input(f"🔗 Reference mới (cũ: {entry[4]}): ")
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
            self._save(path, data)
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

    def _get_options(self, q, a, data, all_ans, n_opts):
        ql = q.lower()
        if any(kw in ql for kw in _CONFIG.KEYWORD_BOOL):
            return ["Đúng", "Sai"]
        # check special keywords map
        for kw in _CONFIG.KEYWORD:
            if kw in ql:
                # limit scanning to only necessary answers
                group = {a}
                for _, ans, ques, *_ in data:
                    if kw in ques.lower():
                        group.add(ans)
                opts = self._options(a, group, n_opts)
                return [self._replace_colors(opt) for opt in dict.fromkeys(opts)]
        opts = self._options(a, all_ans, n_opts)
        return [self._replace_colors(opt) for opt in dict.fromkeys(opts)]

    def _feedback(self, ok, chosen, q, a, d, r, qid):
        if ok:
            print(f"{GREEN}✅ Chính xác! {RESET}{a}\n\n{BRIGHT_GREEN}{'O'*48}\n\tHAY!!!!!!!!!!!!!!!!!!!!!!!!\n{'O'*48}\n")
            log_action(f"CHOSEN:{qid}", f"{chosen} - {q} Đúng + 1 điểm")
        else:
            print(f"{RED}❌ Sai!{RESET} ➤ Đáp án đúng: {RESET}{a}\n\n{BRIGHT_RED}{'X'*48}\n\tQUÁ GÀ !!!!!!!!!!!!!!!!!!!!!!!!\n{'X'*48}\n")
            log_action(f"CHOSEN:{qid}", f"{chosen} - {q} Sai")
        if d:
            print(f"{YELLOW}💡 Mô tả: {RESET}\n{d}\n")
        if r:
            print(f"{CYAN}🔗 Tham chiếu:{RESET}\n{r}\n")

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
            w.writerow(["idx", "question", "correct", "ok", "desc", "reference"])
            for r in results:
                w.writerow([r["index"], r["question"], r["correct"], r["ok"], r["desc"], r.get("ref", "")])
        print(f"{BRIGHT_GREEN}✅ Đã export kết quả: {csv_path}{RESET}")

    def _ask_choice(self, mapping):
        def validator(x):
            return (x in mapping, mapping.get(x))
        return self._safe_input("👉 Nhập đáp án: ", validator=validator, allow_exit=False, lower=True)

    def _check_answer(self, chosen, q, a, data):
        # gather correct answers for q (case-insensitive normalized)
        q_norm = q.strip().lower()
        corrects = (ans for _, ans, ques, *_ in data if ques.strip().lower() == q_norm)
        chosen_norm = chosen.strip().lower()
        return any(chosen_norm == self._replace_colors(ca).strip().lower() for ca in corrects)

    def _quiz(self, data, n_opts=None, max_qs=None, source = None):
        if not data:
            print("❌ Không có câu hỏi.")
            return
        pool = data[:] if not max_qs else random.sample(data, min(max_qs, len(data)))
        all_ans = [a for _, a, _, _, _ , source in data]
        results = []
        score = 0
        for i, (qid, a, q, d, r, source) in enumerate(pool, 1):
            print(f"{RESET}{'='*48}")
            check_continue = input(f'\nNhập {BRIGHT_GREEN}bất kỳ để tiếp tục{RESET} hoặc {BRIGHT_RED}"exit()" để tổng kết ngay{RESET}: ').strip().lower()
            if check_continue in ["exit()", "quit()"]:
                print(f"\n🔚 Tổng kết sau {i-1} câu...\n")
                break
            q_disp = self._replace_colors(q)
            a_disp = self._replace_colors(a)
            d_disp = self._replace_colors(d)
            r_disp = self._replace_colors(r)
            print(f"\nĐang chuẩn bị câu hỏi tiếp theo")
            time.sleep(0.01)
            print(f"{random.randint(0,25)}% - random dataset: {BRIGHT_YELLOW}{source}{RESET}\n{random.randint(26,50)}% - Chọn id: {BRIGHT_CYAN}{qid}{RESET}")
            time.sleep(0.02)
            print(f"{random.randint(50,75)}% - Đang chuẩn bị data: {BRIGHT_CYAN}{qid}{RESET}\n{random.randint(76,99)}% - Random Option: {BRIGHT_CYAN}{qid}{RESET}")
            time.sleep(0.03)
            print(f"100% - Thành công")
            print(f"\n{'='*48}")
            print(f"\n{RESET}{i}❓ {q_disp}\n")
            opts = self._get_options(q_disp, a_disp, data, all_ans, n_opts)
            random.shuffle(opts)
            mapping = dict(zip(string.ascii_lowercase, opts))
            print(f"{'='*48}\n")
            for k, v in list(mapping.items())[:len(opts)]:
                print(f"{RESET}{BRIGHT_GREEN}{k}){RESET} {v}{RESET}\n")
            print(f"{'='*48}")
            if _CONFIG.DEBUG:
                if source:
                    print(f"\n{RESET}File nguồn: {BRIGHT_YELLOW}{source}{RESET}")
                print(f"{RESET}ID Câu hỏi: {BRIGHT_YELLOW}{qid}\n{RESET}")         
            chosen = self._ask_choice(mapping)
            # clearsrc
            self.clearsrc()
            print(f"{'='*48}")
            print(f"{RESET}{i}. ❓ {q_disp}")
            print(f"{YELLOW}Chọn:{RESET} {chosen}")
            ok = self._check_answer(chosen, q, a_disp, data)
            if ok:
                score += 1
            results.append({
                "index": i, "question": q_disp, "correct": a_disp,
                "desc": d_disp, "ref": r_disp, "ok": ok
            })
            self._feedback(ok, chosen, q_disp, a_disp, d_disp, r_disp, qid)
            print(f"{BRIGHT_GREEN}Số câu đúng hiện tại: {score}")
                
        self._export_results(results, score, len(results))

    def play_file(self):
        print(f"{'='*16} Chơi theo file {'='*16}\n")
        path = self._choose_file("chơi")
        difficult_choice = input(f"0 - Mặc định: {_CONFIG.MAX_GENERATE_NORMAL_QUESTIONS} flashcard, {_CONFIG.MAX_GENERATE_NORMAL_ANSWERS} options\n1 - Dễ (10 flashcard, 1 options, thích hợp cho việc học)\n2 - Trung bình (20 flashcard, 4 options / TF, khuyến nghị)\n3 - Khó (50 flashcard, 6 options / TF)\n4 - Hardcore (100 flashcard, 8 ~ 24 options)\n\nVui lòng chọn độ khó hoặc nhập exit() để thoát:")
        if difficult_choice == str(0):
            if path:
                self._quiz(self._load(path), n_opts=_CONFIG.MAX_GENERATE_NORMAL_ANSWERS, max_qs=_CONFIG.MAX_GENERATE_NORMAL_QUESTIONS)
        if difficult_choice == str(1):            
            if path:
                self._quiz(self._load(path), n_opts=1, max_qs=10)
        if difficult_choice == str(2):
            if path:
                self._quiz(self._load(path), n_opts=4, max_qs=20)
        if difficult_choice == str(3):
            if path:
                self._quiz(self._load(path), n_opts=6, max_qs=50)
        if difficult_choice == str(4):
            if path:
                self._quiz(self._load(path), n_opts=random.randint(8, 24), max_qs=100)

    def play_all(self):
        print(f"{'='*16} Chơi ngẫu nhiên {'='*16}\n")
        data = []
        for f in self._files():
            data.extend(self._load(os.path.join(self.qdir, f)))
        difficult_choice = input(f"0 - Mặc định: {_CONFIG.MAX_GENERATE_ALL_QUESTIONS} flashcard, {_CONFIG.MAX_GENERATE_ALL_ANSWERS} options\n1 - Dễ (10 flashcard, 1 options, thích hợp cho việc học)\n2 - Trung bình (20 flashcard, 4 options / TF, khuyến nghị)\n3 - Khó (50 flashcard, 6 options / TF)\n4 - Hardcore (100 flashcard, 8 ~ 24 options)\n\nVui lòng chọn độ khó hoặc nhập exit() để thoát:")
        if difficult_choice == str(0):
            self._quiz(data, n_opts=_CONFIG.MAX_GENERATE_ALL_ANSWERS, max_qs=_CONFIG.MAX_GENERATE_ALL_QUESTIONS)
        if difficult_choice == str(1):            
            self._quiz(data, n_opts=1, max_qs=10)
        if difficult_choice == str(2):
            self._quiz(data, n_opts=4, max_qs=20)
        if difficult_choice == str(3):
            self._quiz(data, n_opts=6, max_qs=50)
        if difficult_choice == str(4):
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
                csv.writer(f).writerow(["id", "answer", "question", "desc", "ref"])
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
    def manage_questions(self):
        actions = {
            "1": ("thêm",   f"{RESET}{BRIGHT_GREEN}➕ Thêm nội dung"),
            "2": ("xoá",    f"{RESET}{BRIGHT_RED}🗑️ Xoá nội dung"),
            "3": ("sửa",    f"{RESET}{BRIGHT_YELLOW}✏️ Sửa toàn bộ nội dung"),
            "4": ("sửaQ",   f"{RESET}{BRIGHT_YELLOW}✏️ Sửa câu hỏi cụ thể"),
            "5": ("sửaA",   f"{RESET}{BRIGHT_YELLOW}✏️ Sửa đáp án cụ thể"),
            "6": ("sửaD",   f"{RESET}{BRIGHT_YELLOW}✏️ Sửa mô tả cụ thểS"),
            "7": ("sửaR",   f"{RESET}{BRIGHT_YELLOW}✏️ Sửa tham khảo cụ thẻS"),
        }
        while True:
            self.clearsrc()
            print(f"\n{BRIGHT_CYAN}====={BRIGHT_GREEN} 📋 QUẢN LÝ NỘI DUNG  {RESET}{BRIGHT_CYAN}====={RESET}")
            print(f"\n{BRIGHT_GREEN}===\nCác chức năng hiện tại:\n{RESET}")
            [print(f"{BRIGHT_GREEN} {k}) {label}{RESET}") for k, (_, label) in actions.items()]
            print(f"\n{BRIGHT_GREEN}Hoặc nhập {BRIGHT_RED}exit(){BRIGHT_GREEN} 🔙 quay lại{RESET}")
            ch = input(f"\n{BRIGHT_GREEN}👉 Nhập lựa chọn: {RESET}").strip().lower()
            if ch == "exit()":
                self.clearsrc()
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
                print(f"\n{BRIGHT_CYAN}====={BRIGHT_GREEN} 📂 QUẢN LÝ FILE  {RESET}{BRIGHT_CYAN}====={RESET}")
                self._list_files()
                print(f"\n{BRIGHT_CYAN}===\nCác chức năng hiện tại:\n{RESET}")
                [print(f"{BRIGHT_CYAN} {k}) {label}{RESET}") for k, (_, label, _) in actions.items()]
                print(f"\n{BRIGHT_CYAN}Hoặc nhập {BRIGHT_RED}exit(){BRIGHT_CYAN} 🔙 quay lại{RESET}")
                ch = input(f"\n{BRIGHT_CYAN}👉 Nhập lựa chọn: {RESET}").strip().lower()
                if ch == "exit()":
                    self.clearsrc()
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
            print(f"{BLUE}\n===== 📚 FLASHCARD QUIZ GAME ====={RESET}")
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
