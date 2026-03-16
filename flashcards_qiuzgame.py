#!/usr/bin/env python3
import os, csv, uuid, random, string, datetime, getpass, re, logging, time
from logging.handlers import TimedRotatingFileHandler
from functools import lru_cache
from types import SimpleNamespace
from config import *
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

# --- KHỞI TẠO & CÁC HÀM TIỆN ÍCH ---
# Tạo một không gian tên (namespace) đơn giản từ file config để dễ dàng truy cập các biến cấu hình (VD: _CONFIG.LOG_DIR)
_CONFIG = SimpleNamespace(**{k: v for k, v in globals().items() if k.isupper()})
# Đảm bảo các thư mục cần thiết (logs, exports, questions) đã tồn-tại, nếu chưa thì tạo mới
for d in [_CONFIG.LOG_DIR, _CONFIG.EXPORT_DIR, _CONFIG.QUESTIONS_DIR]: os.makedirs(d, exist_ok=True)

# Cấu hình hệ thống ghi log
logger = logging.getLogger("flashcard"); logger.setLevel(logging.INFO)
if not logger.handlers:
    # Sử dụng TimedRotatingFileHandler để tự động xoay vòng file log mỗi ngày, giữ lại 14 file backup
    h = TimedRotatingFileHandler(os.path.join(_CONFIG.LOG_DIR, "flashcard.log"), when="midnight", backupCount=14, encoding="utf-8")
    h.setFormatter(logging.Formatter('%(asctime)s | %(user)s | %(action)s | %(detail)s')); logger.addHandler(h)

# Các hàm tiện ích viết dưới dạng lambda cho ngắn gọn
def current_user(): return getpass.getuser()
log_action = lambda a, d="": logger.info("", extra={"user": current_user(), "action": a, "detail": d})
timestamp_now = lambda: datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
console = Console()

# --- LỚP LOGIC XỬ LÝ GAME QUIZ ---
class QuizGame:
    """Tách riêng logic xử lý game để giảm tải cho class FlashCard chính."""
    def __init__(self, app): self.app = app

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        """Tạo ra các phương án trả lời (trắc nghiệm) một cách thông minh."""
        # 1. Nếu câu hỏi là dạng Đúng/Sai, chỉ trả về 2 phương án này
        if any(k in q.lower() for k in _CONFIG.KEYWORD_BOOL): return ["Đúng", "Sai"]
        # 2. Ưu tiên lấy các đáp án nhiễu từ cùng một chủ đề (dựa trên keyword trong câu hỏi)
        target = {a}; related = [r[1] for r in data if r[1].strip() != a.strip() and any(k in r[2].lower() for k in _CONFIG.KEYWORD if k in q.lower())]
        target.update(related)
        # 3. Nếu vẫn thiếu, lấy ngẫu nhiên từ toàn bộ kho đáp án
        candidates = [x[1] for x in all_ans if x[1].strip() != a.strip() and x[1] not in target]
        if len(target) < (n_opts or 4): target.update(random.sample(candidates, min(len(candidates), (n_opts or 4) - len(target))))
        final = list(target - {a, "Đúng", "Sai"}); opts = random.sample(final, min(len(final), max(0, (n_opts or 4) - 1))) + [a]
        return [self.app._replace_colors(o) for o in dict.fromkeys(opts)]

    def _feedback(self, ok, chosen, q, a, d, r, qid):
        log_action(f"CHOSEN:{qid}", f"{chosen} - {q} {'Đúng' if ok else 'Sai'}")
        
        if ok:
            # Sử dụng Text.from_ansi để hiển thị đúng màu của đáp án (nếu có)
            console.print(Text().append("\n ✅ CHÍNH XÁC! ", style="bold white on green").append(" ").append(Text.from_ansi(chosen)))
        else:
            answer_text = Text.from_ansi(a)
            answer_text.stylize("bold yellow")
            console.print(Text().append("\n ❌ SAI RỒI... ", style="bold white on red").append(" Đáp án đúng: ").append(answer_text))
        
        if r: console.print(Text("   🔗 ", style="cyan").append(Text.from_ansi(r)))
        console.print("") # Padding

    def _export_results(self, results, score, total):
        """Hiển thị bảng điểm cuối game và xuất kết quả ra file CSV."""
        wrong, pct = total - score, (score / total * 100) if total else 0.0
        # In bảng điểm chi tiết
        table = Table(title="🎯 BẢNG ĐIỂM CHI TIẾT", box=box.ROUNDED)
        table.add_column("STT", justify="right", style="cyan")
        table.add_column("KẾT QUẢ", justify="center")
        table.add_column("ĐÁP ÁN ĐÚNG", style="green")
        for r in results: table.add_row(str(r['index']), "✅" if r['ok'] else "❌", r['correct'])
        console.print(table)
        # In thống kê tổng quan và thanh tiến trình
        bar = "="*int(30*pct//100) + " "*(30-int(30*pct//100))
        console.print(f"\n[green]✅ Đúng: {score:<5}[/] [red]❌ Sai: {wrong:<5}[/] [cyan]📊 {pct:.1f}% [{bar}][/]\n")
        
        # Ghi kết quả ra file CSV trong thư mục exports
        csv_path = os.path.join(_CONFIG.EXPORT_DIR, f"quiz_results_{timestamp_now()}.csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows([["timestamp", datetime.datetime.now().isoformat()], ["user", current_user()], ["total", total], ["score", score], ["percent", f"{pct:.1f}"], [], ["idx", "question", "correct", "ok", "hint", "desc"]] + [[r["index"], r["question"], r["correct"], r["ok"], r["hint"], r.get("desc", "")] for r in results])
        print(f"{BRIGHT_GREEN}✅ Export: {csv_path}{RESET}")

    def get_difficulty(self):
        """Hiển thị menu chọn độ khó và trả về cấu hình tương ứng (số đáp án, số câu hỏi)."""
        table = Table(title="CHỌN ĐỘ KHÓ", box=box.SIMPLE)
        table.add_column("Key", style="bold cyan", justify="right")
        table.add_column("Mô tả", style="white")
        for k, v in [("0", f"Mặc định ({_CONFIG.MAX_GENERATE_NORMAL_QUESTIONS} câu)"), ("1", "Dễ (10 câu)"), ("2", "Vừa (20 câu)"), ("3", "Khó (50 câu)"), ("4", "Hardcore (100 câu)")]:
            table.add_row(k, v)
        console.print(table)
        try: ch = int(console.input(f"\n👉 Chọn mode: "))
        except: ch = 0
        return {1: (1, 10), 2: (4, 20), 3: (6, 50), 4: (random.randint(8, 24), 100)}.get(ch, (_CONFIG.MAX_GENERATE_NORMAL_ANSWERS, _CONFIG.MAX_GENERATE_NORMAL_QUESTIONS))

    def run(self, data, n_opts=None, max_qs=None, source=None):
        """Vòng lặp chính của game quiz."""
        if not data: return print("❌ Không có dữ liệu.")
        # Chọn ngẫu nhiên một số câu hỏi từ bộ dữ liệu nếu có giới hạn max_qs
        pool, results, score = (random.sample(data, min(max_qs, len(data))) if max_qs else data[:]), [], 0
        
        # Bắt đầu lặp qua từng câu hỏi
        for i, (qid, a, q, d, r, src) in enumerate(pool, 1):
            self.app.clearsrc()
            # Header câu hỏi đẹp hơn
            console.rule(f"[bold white on blue] QUIZ [/] [cyan]Câu {i}/{len(pool)}[/] │ [green]Score: {score}[/] │ [dim]ID: {qid[-6:]}[/]")
            # Thay thế token màu sắc để hiển thị
            q_d, a_d, d_d, r_d = map(self.app._replace_colors, (q, a, d or "", r or ""))
            
            # Dùng Text.from_ansi để parse mã màu ANSI trong nội dung câu hỏi
            console.print(Text("\n").append(Text.from_ansi(q_d)).append("\n"), style="bold white", justify="left")
            
            # Lấy các phương án trắc nghiệm và xáo trộn chúng
            opts = self._get_options(qid, q, a, data, data, n_opts); random.shuffle(opts)
            mapping = {k: v for k, v in zip(string.ascii_uppercase[:len(opts)], opts)}
            for k, v in mapping.items(): 
                console.print(Text().append(f"  [{k}] ", style="bold cyan").append(Text.from_ansi(v)))

            # Vòng lặp chờ người dùng nhập câu trả lời
            while True:
                u = console.input(f"\n👉 Chọn ([bold cyan]A-{list(mapping)[-1]}[/]) / '?' / '/exit': ").strip().upper()
                if u == 'EXIT': return self._export_results(results, score, len(results))
                if u == '?': print(f"\n{YELLOW}💡 Gợi ý:{RESET}\n{d_d}\n"); continue
                if u in mapping: chosen = mapping[u]; break
                print(f"{BRIGHT_RED}❌ Sai lựa chọn.{RESET}")

            # Hàm lambda để "làm sạch" chuỗi: xóa mã màu ANSI, token màu, khoảng trắng thừa...
            clean = lambda t: re.sub(r'\{[A-Z0-9_]+\}|\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', str(t)).strip().lower().rstrip('.')
            # So sánh câu trả lời đã làm sạch với đáp án đúng đã làm sạch
            ok = clean(chosen) == clean(a)
            if ok: score += 1
            
            # Lưu lại kết quả của câu hỏi này
            results.append({"index": i, "question": q_d, "correct": a_d, "hint": d_d, "desc": r_d, "ok": ok})
            self._feedback(ok, chosen, q_d, a_d, d_d, r_d, qid)
            if i < len(pool): input(f"{BRIGHT_BLACK}[Enter] tiếp tục...{RESET}")
        
        # Kết thúc game, xuất kết quả
        self._export_results(results, score, len(pool))

# --- LỚP CHÍNH QUẢN LÝ FLASHCARD ---
class FlashCard:
    def __init__(self, qdir=None):
        """Khởi tạo: thiết lập đường dẫn, tải màu sắc, và các cache."""
        self.qdir = qdir or _CONFIG.QUESTIONS_DIR; os.makedirs(self.qdir, exist_ok=True)
        # Map token sang mã ANSI gốc từ config (hỗ trợ "set color" thay vì nesting)
        self.color_map = {f"{{{k}}}": v for k, v in _CONFIG.__dict__.items() if k.isupper() and isinstance(v, str) and v.startswith('\033')}
        self._color_token_re = re.compile(r"\{[A-Z0-9_]+\}")
        self._file_counts_cache = {}

    @staticmethod
    def clearsrc(): os.system("cls" if os.name == "nt" else "clear") if _CONFIG.CLEAR_SCREEN else None

    def _replace_colors(self, text):
        """Thay thế các token màu trong chuỗi bằng mã màu ANSI để hiển thị trên terminal."""
        if not text: return ""
        # Xử lý trường hợp đầu vào là tuple/list do csv reader đôi khi trả về
        text = str(text[1] if isinstance(text, (tuple, list)) and len(text) > 1 else (text[0] if isinstance(text, (tuple, list)) else text))
        # Thay thế token {TOKEN} bằng mã ANSI
        text = self._color_token_re.sub(lambda m: self.color_map.get(m.group(0), m.group(0)), text.replace("\\n", "\n").replace("\\t", "\t").replace(".\\n", "\n").replace("{BACKSLASH}", "\\"))
        return text

    def _files(self):
        return [f for f in os.listdir(self.qdir) if f.endswith(".csv")]

    def _list_files(self, show=True):
        """Liệt kê tất cả các file .csv trong thư mục questions."""
        files = self._files()
        if not files: return console.print("[yellow]⚠️ Không có file.[/]") if show else []
        if show:
            table = Table(title="📂 KHO DỮ LIỆU", box=box.SIMPLE_HEAD)
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Tên Bộ Đề", style="bold white")
            table.add_column("Số câu", justify="right")
            for i, f in enumerate(files, 1):
                c = self._count_questions_cached(f)
                color = "green" if c >= 64 else "cyan" if c >= 32 else "yellow" if c >= 16 else "magenta" if c >= 8 else "red"
                table.add_row(str(i), f, f"[{color}]{c}[/]")
            console.print(table)
        return files

    def _count_questions_cached(self, fname):
        """Đếm số dòng (câu hỏi) trong file, sử dụng cache để tăng tốc độ."""
        if fname not in self._file_counts_cache:
            try: self._file_counts_cache[fname] = max(0, sum(1 for _ in open(os.path.join(self.qdir, fname), encoding="utf-8-sig")) - 1)
            except: self._file_counts_cache[fname] = 0
        return self._file_counts_cache[fname]

    @lru_cache(maxsize=64)
    def _load_flashcard(self, path):
        """Tải dữ liệu từ file CSV. Sử dụng lru_cache để lưu kết quả vào bộ nhớ, tránh đọc file nhiều lần."""
        if not os.path.exists(path): return []
        with open(path, encoding="utf-8-sig") as f:
            return [(r.get("id","").strip() or str(uuid.uuid4()), r.get("answer","").strip(), r.get("question","").strip(), r.get("hint","").strip(), r.get("desc","").strip(), os.path.basename(path)) for r in csv.DictReader(f)]

    def _save_flashcard(self, path, data):
        """Lưu dữ liệu vào file CSV, tự động sắp xếp và xóa cache cũ."""
        data.sort(key=lambda x: (x[1].lower().strip(), x[2].lower().strip()))
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows([["id", "answer", "question", "hint", "desc"]] + [row[:5] for row in data])
        self._load_flashcard.cache_clear(); self._file_counts_cache.pop(os.path.basename(path), None)

    def _safe_input(self, prompt, validator=None, allow_exit=True, lower=False):
        """Hàm nhập liệu an toàn, có hỗ trợ validator, lệnh /exit và xử lý lỗi."""
        while True:
            try: v = console.input(Text.from_ansi(prompt) if isinstance(prompt, str) else prompt).strip()
            except (KeyboardInterrupt, EOFError): return None
            if allow_exit and (v.lower() == "/exit"): return None
            if validator:
                res = validator(v.lower() if lower else v)
                ok, val = (res, v) if not isinstance(res, tuple) else res
                if ok: return val
                console.print("[red]⚠️ Sai lựa chọn![/]")
            else: return v

    def _choose_file(self, action="chọn"):
        """Hiển thị danh sách file và cho phép người dùng chọn bằng số thứ tự."""
        files = self._list_files()
        validator = lambda x: (True, os.path.join(self.qdir, files[int(x)-1])) if x.isdigit() and 0 < int(x) <= len(files) else False
        return self._safe_input(f"\n👉 Nhập ID để {action} (hoặc gõ /exit): ", validator=validator) if files else None

    def _show(self, path, show=True):
        """Hiển thị chi tiết tất cả các câu hỏi trong một file."""
        data = self._load_flashcard(path)
        if show and data:
            table = Table(title=f"📋 {os.path.basename(path)}", box=box.ROUNDED, show_lines=True, header_style="bold magenta")
            table.add_column("ID", justify="right", style="cyan", width=4)
            table.add_column("Câu Hỏi & Đáp Án", style="white")
            table.add_column("Thông tin thêm", style="dim")

            for i, (_, a, q, d, r, _) in enumerate(data, 1):
                qa = Text()
                qa.append("❓ ", style="bold blue").append(Text.from_ansi(self._replace_colors(q)))
                qa.append("✅ ", style="bold green").append(Text.from_ansi(self._replace_colors(a)))

                extra = Text()
                if d: extra.append("💡 ", style="yellow").append(Text.from_ansi(self._replace_colors(d))).append("\n")
                if r: extra.append("🔗 ", style="cyan").append(Text.from_ansi(self._replace_colors(r)))

                table.add_row(str(i), qa, extra)
            
            console.print(table)
        elif show: console.print("[red]❌ File trống.[/]")
        return data

    def _ask_index(self, data, action="chọn"):
        """Hỏi người dùng nhập số thứ tự của một câu hỏi trong danh sách."""
        return self._safe_input(f"\n🔢 Nhập ID để {action} (hoặc /exit): ", validator=lambda x: (True, int(x)-1) if x.isdigit() and 1 <= int(x) <= len(data) else (False, None)) if data else None

    def _add_question(self, path):
        """Thêm một câu hỏi mới vào file đã chọn."""
        data = list(self._load_flashcard(path))
        while True:
            self._show(path, show=True)
            q = self._safe_input(f"\nFile: {BRIGHT_YELLOW}{path}{RESET}\n❓ Nhập câu hỏi (/exit):{RESET} ")
            if not q: break
            a = self._safe_input(f"✅ Nhập đáp án (/exit):{RESET} ")
            if not a: break
            if any(q.lower().strip() == old_q.lower().strip() and a.lower().strip() == old_a.lower().strip() for _, old_a, old_q, *_ in data):
                self.clearsrc(); console.print(Text("⚠️ Câu hỏi đã tồn tại!", style="bold red")); continue
            d, r = self._safe_input("💡 Gợi ý: "), self._safe_input("🔗 Mô Tả: ")
            data.append((str(uuid.uuid4()), a, q, d or "", r or "")); self._save_flashcard(path, data)
            log_action("ADD_Q", f"{os.path.basename(path)} | Q: {q}"); self.clearsrc(); console.print(Text("➕ Đã thêm.", style="bold green"))

    def _delete_question(self, path):
        """Xóa một câu hỏi khỏi file đã chọn."""
        data = list(self._load_flashcard(path))
        while True:
            self._show(path); idx = self._ask_index(data, "xoá")
            if idx is None: break
            removed = data.pop(idx); self._save_flashcard(path, data)
            log_action("DEL_Q", f"{os.path.basename(path)} | Q: {removed[2]}"); self.clearsrc(); console.print(Text("🗑️ Đã xoá: ").append(Text.from_ansi(removed[2])))

    def _edit_question(self, path, mode="sửa"):
        """Sửa một câu hỏi trong file đã chọn."""
        data, fields = list(self._load_flashcard(path)), {"sửaQ": 2, "sửaA": 1, "sửaD": 3, "sửaR": 4}
        while True:
            self._show(path); idx = self._ask_index(data, "sửa")
            if idx is None: break
            e = list(data[idx])
            if mode == "sửa":
                e[2] = self._safe_input(f"❓ Câu hỏi (cũ: {e[2]}): ") or e[2]
                e[1] = self._safe_input(f"✅ Đáp án (cũ: {e[1]}): ") or e[1]
                e[3] = self._safe_input(f"💡 Gợi ý (cũ: {e[3]}): ") or e[3]
                e[4] = self._safe_input(f"🔗 Mô Tả (cũ: {e[4]}): ") or e[4]
            elif mode in fields:
                val = self._safe_input(f"✏️ Giá trị mới (cũ: {e[fields[mode]]}): ")
                if val: e[fields[mode]] = val
            data[idx] = tuple(e); self._save_flashcard(path, data)
            log_action("EDIT_Q", f"{os.path.basename(path)} | Q: {e[2]}"); self.clearsrc(); console.print("[green]✅ Đã sửa.[/]")

    def _crud(self, mode):
        """Hàm điều phối, gọi các hàm thêm/sửa/xóa câu hỏi tương ứng."""
        path = self._choose_file(mode)
        if path: {"thêm": self._add_question, "xoá": self._delete_question}.get(mode, lambda p: self._edit_question(p, mode))(path)

    def play_file(self):
        """Chơi quiz với các câu hỏi từ một file duy nhất."""
        path = self._choose_file("chơi")
        if path:
            game = QuizGame(self)
            game.run(self._load_flashcard(path), *game.get_difficulty())

    def play_all(self):
        """Chơi quiz với tất cả câu hỏi từ tất cả các file."""
        game = QuizGame(self)
        all_data = [row for f in self._files() for row in self._load_flashcard(os.path.join(self.qdir, f))]
        game.run(all_data, *game.get_difficulty())

    def _create_file(self, act):
        """Tạo một file .csv mới."""
        name = self._safe_input("📄 Tên file (không .csv): ")
        if name and not os.path.exists(p := os.path.join(self.qdir, f"{name}.csv")):
            with open(p, "w", encoding="utf-8-sig", newline="") as f: csv.writer(f).writerow(["id", "answer", "question", "hint", "desc"])
            log_action(act, p); self.clearsrc(); console.print(f"[green]✅ Đã tạo {name}.csv[/]")
        else: console.print("[yellow]⚠️ File tồn tại/Lỗi.[/]")

    def _delete_file(self, act):
        """Xóa một file .csv."""
        if (path := self._choose_file("xoá")) and self._safe_input(f"❓ Xoá {os.path.basename(path)}? (y/n) ", lambda x: (x=="y",x)) == "y":
            os.remove(path); log_action(act, path); self._file_counts_cache.pop(os.path.basename(path), None); self._load_flashcard.cache_clear(); self.clearsrc(); console.print("[red]🗑️ Đã xoá.[/]")

    def _rename_file(self, act):
        """Đổi tên một file .csv."""
        if (path := self._choose_file("đổi tên")) and (new := self._safe_input("✏️ Tên mới: ")):
            os.rename(path, (np := os.path.join(self.qdir, f"{new}.csv")))
            log_action(act, f"{path}->{np}"); self._file_counts_cache.pop(os.path.basename(path),None); self._file_counts_cache.pop(os.path.basename(np),None); self._load_flashcard.cache_clear(); self.clearsrc(); console.print("[green]✅ Đã đổi tên.[/]")

    def show_stats(self):
        """Hiển thị thống kê tổng quan (tổng số bộ đề, tổng số câu hỏi)."""
        files = self._files()
        total_q = sum(self._count_questions_cached(f) for f in files)
        table = Table(title="📊 THỐNG KÊ", box=box.ROUNDED, show_header=False)
        table.add_column("Mục", style="cyan")
        table.add_column("Giá trị", justify="right", style="bold yellow")
        table.add_row("📂 Số lượng bộ đề", str(len(files)))
        table.add_row("❓ Tổng số câu hỏi", f"[green]{total_q}[/]")
        console.print(table)

    def _run_menu(self, title, options):
        """Hàm chạy menu chung, giúp tái sử dụng code cho các menu khác nhau."""
        while True:
            self.clearsrc()
            console.rule(f"[bold blue]{title}[/]")
            self.show_stats()
            if title == "QL FILE": self._list_files()
            
            table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
            table.add_column("Key", justify="right", style="cyan")
            table.add_column("Option", style="white")
            for k, v in options.items(): table.add_row(k, v[1])
            console.print(table)
            
            ch = console.input(f"\n👉 Chọn (hoặc /exit): ").strip()
            if ch in options: 
                if ch == "0": break
                self.clearsrc(); log_action("MENU", options[ch][1]); options[ch][0]()
                if title == "FLASHCARD": continue
            elif ch == "/exit": break
            else: console.print("[red]⚠️ Sai.[/]")

    def manage_questions(self):
        """Menu quản lý nội dung câu hỏi (thêm, sửa, xóa)."""
        opts = {"1": ("thêm", "➕ Thêm"), "2": ("xoá", "🗑️ Xoá"), "3": ("sửa", "✏️ Sửa All"), "4": ("sửaQ", "✏️ Sửa Q"), "5": ("sửaA", "✏️ Sửa A"), "6": ("sửaD", "✏️ Sửa Hint"), "7": ("sửaR", "✏️ Sửa Desc")}
        self._run_menu("QL DATA", {k: (lambda m=v[0]: self._crud(m), v[1]) for k, v in opts.items()})

    def manage_files(self):
        """Menu quản lý file (tạo, xóa, đổi tên)."""
        self._run_menu("QL FILE", {"1": (lambda: self._create_file("CREATE"), "➕ Tạo file"), "2": (lambda: self._delete_file("DELETE"), "🗑️ Xoá file"), "3": (lambda: self._rename_file("RENAME"), "✏️ Đổi tên")})

    def menu(self):
        """Menu chính của ứng dụng."""
        self._run_menu("FLASHCARD", {"1": (self.play_file, "🎯 Chơi bộ"), "2": (self.play_all, "🌍 Chơi all"), "3": (self.manage_questions, "📋 QL Data"), "4": (self.manage_files, "📂 QL File"), "0": (lambda: console.print("[bold red]Bye![/]"), "🚪 Thoát")})

# Điểm khởi chạy của chương trình
if __name__ == "__main__":
    FlashCard().menu()