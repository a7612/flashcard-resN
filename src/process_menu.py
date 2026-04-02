import os, csv, datetime, getpass, time # Import 'time' for time.sleep
from src.core import _CONFIG, console, log_action, _clear_screen, _safe_input 
from src.process_file import FileManager
from src.process_flashcard import FlashcardManager
from src.engine import QuizGame
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.panel import Panel
from rich.align import Align
from rich import box
from rich.console import Group

class MenuManager:
    def __init__(self):
        self.file_mgr = FileManager()
        self.card_mgr = FlashcardManager()

    def show_stats(self):
        files = self.file_mgr.get_files()
        total_q = sum(self.file_mgr.count_questions(f) for f in files)
        total_bytes = sum(os.path.getsize(os.path.join(self.file_mgr.qdir, f)) for f in files)
        size_str = f"{total_bytes/1024:.1f} KB" if total_bytes > 1024 else f"{total_bytes} B"
        table = Table(box=box.ROUNDED, show_header=False, min_width=28, border_style="dim") 
        table.add_row("📂 Bộ đề", str(len(files)))
        table.add_row("❓ Tổng câu", f"[bold green]{total_q}[/]")
        table.add_row("💾 Lưu trữ", f"[bold magenta]{size_str}[/]")
        return Panel(table, title="[bold cyan]📊 THỐNG KÊ[/]", border_style="cyan", expand=False)

    def get_history_table(self):
        table = Table(box=box.ROUNDED, border_style="dim")
        table.add_column("Thời gian", style="dim", width=11)
        table.add_column("Điểm", justify="center"); table.add_column("%", justify="right", style="bold yellow")
        history_pcts = []
        h_files = sorted([f for f in os.listdir(_CONFIG.EXPORT_DIR) if f.startswith("quiz_results_")], reverse=True)[:10]
        for f_name in h_files:
            try:
                with open(os.path.join(_CONFIG.EXPORT_DIR, f_name), encoding="utf-8-sig") as f:
                    meta = {r[0]: r[1] for r in csv.reader(f) if len(r) >= 2}
                    pct = float(meta.get('percent', 0)); history_pcts.append(pct)
                    dt = datetime.datetime.fromisoformat(meta["timestamp"]).strftime("%d/%m %H:%M")
                    table.add_row(dt, f"{meta.get('score', 0)}/{meta.get('total', 0)}", f"{pct:.0f}%")
            except: pass
        if history_pcts:
            avg = sum(history_pcts)/len(history_pcts)
            color = "bold green" if avg > 80 else "bold red" if avg < 50 else "bold yellow"
            table.caption = f"[bold white]🎯 Độ chính xác TB: [{color}]{avg:.1f}%[/{color}][/]"
        return Panel(table, title="[bold yellow]📜 LỊCH SỬ[/]", border_style="yellow", expand=False)

    def _choose_file_path(self):
        files = self.file_mgr.list_files(show=True) # Đảm bảo luôn hiển thị danh sách file
        if not files:
            console.print("[yellow]⚠️ Thư mục hiện đang trống.[/]")
            time.sleep(1) # Cho người dùng thời gian đọc thông báo
            return None
        return _safe_input("👉 Nhập ID bộ đề (hoặc /exit): ", lambda x: (x.isdigit() and 1 <= int(x) <= len(files), os.path.join(self.file_mgr.qdir, files[int(x)-1])))

    def run_menu(self, title, options, show_file_list=False, show_sidebar=True, clear=True, show_questions_path=None):
        while True:
            if clear: _clear_screen()
            header = Text.from_ansi(f"{_CONFIG.BRIGHT_WHITE}🚀 {title} 🚀\n{_CONFIG.CYAN}User: {getpass.getuser()} | {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
            console.print(Panel(Align.center(header), box=box.DOUBLE, border_style="bright_blue"))
            opt_table = Table(show_header=False, box=box.ROUNDED, border_style="dim")
            for k, v in options.items(): opt_table.add_row(k, v[1])

            menu_panel = Panel(opt_table, title="[bold magenta]🎮 MENU[/]", border_style="magenta", expand=False)
            if show_sidebar:
                left_col = Group(menu_panel, self.show_stats())
                console.print(Columns([left_col, self.get_history_table()], padding=(0, 4), expand=False))
            else:
                console.print(menu_panel)

            if show_file_list: self.file_mgr.list_files()
            if show_questions_path: self.card_mgr.show_questions(show_questions_path)
            ch = console.input(f"\n👉 Lệnh của bạn: ").strip()
            if ch in ["0", "/exit"]: break
            if ch in options: options[ch][0]()

    def play_action(self, all_files=False):
        game = QuizGame(self)
        if all_files:
            data = []
            for f in self.file_mgr.get_files(): data.extend(self.card_mgr.load_data(os.path.join(self.file_mgr.qdir, f)))
        else:
            path = self._choose_file_path()
            if not path: return
            data = self.card_mgr.load_data(path)
        game.run(data, *game.get_difficulty())

    def _run_question_crud_menu(self, path):
        """Chạy menu CRUD cho các câu hỏi trong một file cụ thể."""
        m = self.card_mgr
        opts = {
            "1": (lambda: m.add_question(path), "📝 Thêm câu"),
            "2": (lambda: m.delete_question(path), "🗑️ Xoá câu"),
            "3": (lambda: m.edit_question(path), "🛠️ Sửa tổng lực"),
            "4": (lambda: m.edit_question(path, 2), "🔍 Sửa câu hỏi"),
            "5": (lambda: m.edit_question(path, 1), "💡 Sửa đáp án"),
            "0": (lambda: None, "Quay lại")
        }
        self.run_menu(f"⚙️ BIÊN TẬP: {os.path.basename(path)}", opts, show_file_list=False, show_sidebar=False, clear=False)

    def manage_q_menu(self):
        while True: # Vòng lặp cho phép quản lý nhiều file liên tiếp
            _clear_screen()
            console.print(Panel(Align.center(Text("📦 QUẢN LÝ NỘI DUNG", style="bold yellow")), box=box.DOUBLE, border_style="yellow"))
            path = self._choose_file_path() # Hiển thị danh sách file và yêu cầu chọn
            if not path: # Người dùng chọn /exit hoặc nhập sai
                break
            self.card_mgr.show_questions(path) # Hiển thị danh sách lần đầu để có STT chọn lệnh
            self._run_question_crud_menu(path) # Chạy menu CRUD cho file đã chọn

    def manage_f_menu(self):
        f = self.file_mgr
        opts = {
            "1": (f.create_file, "🆕 Tạo bộ đề"), "2": (lambda: (p := self._choose_file_path()) and f.delete_file(p), "⚠️ Xoá bộ đề"),
            "3": (lambda: (p := self._choose_file_path()) and f.rename_file(p), "🏷️ Đổi tên"), "0": (lambda: None, "Quay lại")
        }
        self.run_menu("📂 HỆ THỐNG LƯU TRỮ", opts, show_file_list=True, show_sidebar=False, clear=False)