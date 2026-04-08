import os, csv, datetime, getpass, time
from src.core import _CONFIG, console, log_action, _clear_screen, _safe_input, _handle_error, _get_now
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
        try:
            files = self.file_mgr.get_files()
            total_q = 0
            total_bytes = 0
            for f in files:
                total_q += self.file_mgr.count_questions(f)
                full_path = os.path.join(self.file_mgr.qdir, f)
                if os.path.exists(full_path):
                    total_bytes += os.path.getsize(full_path)
        except Exception as e:
            _handle_error(f"⚠️ Lỗi khi thu thập thống kê hệ thống: {e}")
            total_q, total_bytes, files = 0, 0, []
            
        size_str = f"{total_bytes/1024:.1f} KB" if total_bytes > 1024 else f"{total_bytes} B"
        table = Table(box=box.ROUNDED, show_header=False, min_width=28, border_style=_CONFIG.COLOR_STATS) 
        table.add_row("📂 Bộ đề", str(len(files)))
        table.add_row("❓ Tổng câu", f"[bold green]{total_q}[/]")
        table.add_row("💾 Lưu trữ", f"[bold magenta]{size_str}[/]")
        return Panel(table, title=f"[bold {_CONFIG.COLOR_STATS}]📊 THỐNG KÊ[/]", border_style=_CONFIG.COLOR_STATS, expand=False)

    def get_history_table(self):
        table = Table(box=box.ROUNDED, border_style=_CONFIG.COLOR_HISTORY)
        table.add_column("Thời gian", style="dim", width=11)
        table.add_column("Điểm", justify="center"); table.add_column("%", justify="right", style="bold yellow")
        history_pcts = []
        
        all_exports = os.listdir(_CONFIG.EXPORT_DIR)
        h_files_filtered = []
        for f in all_exports:
            if f.startswith("quiz_results_"):
                h_files_filtered.append(f)
        h_files = sorted(h_files_filtered, reverse=True)[:10]

        for f_name in h_files:
            try:
                with open(os.path.join(_CONFIG.EXPORT_DIR, f_name), encoding="utf-8-sig") as f:
                    meta = {}
                    for r in csv.reader(f):
                        if len(r) >= 2:
                            meta[r[0]] = r[1]
                    pct = float(meta.get('percent', 0)); history_pcts.append(pct)
                    dt = datetime.datetime.fromisoformat(meta["timestamp"]).strftime("%d/%m %H:%M")
                    table.add_row(dt, f"{meta.get('score', 0)}/{meta.get('total', 0)}", f"{pct:.0f}%")
            except: pass
        if history_pcts:
            avg = sum(history_pcts)/len(history_pcts)
            color = "bold green" if avg > 80 else "bold red" if avg < 50 else "bold yellow"
            table.caption = f"[bold white]🎯 Độ chính xác TB: [{color}]{avg:.1f}%[/{color}][/]"
        return Panel(table, title=f"[bold {_CONFIG.COLOR_HISTORY}]📜 LỊCH SỬ[/]", border_style=_CONFIG.COLOR_HISTORY, expand=False)

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
            header = f"[bold white]🚀 {title} 🚀[/]\n[{_CONFIG.COLOR_INFO}]User: {getpass.getuser()} | {_get_now().strftime('%d/%m/%Y %H:%M')}[/]"
            console.print(Panel(Align.center(header), box=box.DOUBLE, border_style=_CONFIG.COLOR_HEADER))
            opt_table = Table(show_header=False, box=box.ROUNDED, border_style=_CONFIG.COLOR_MENU)
            for k, v in options.items(): opt_table.add_row(k, v[1])

            menu_panel = Panel(opt_table, title=f"[bold {_CONFIG.COLOR_MENU}]🎮 MENU[/]", border_style=_CONFIG.COLOR_MENU, expand=False)
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
        try:
            if all_files:
                data = []
                for f in self.file_mgr.get_files(): data.extend(self.card_mgr.load_data(os.path.join(self.file_mgr.qdir, f)))
            else:
                path = self._choose_file_path()
                if not path: return
                data = self.card_mgr.load_data(path)
            
            if data: game.run(data, *game.get_difficulty())
            else: console.print("[yellow]⚠️ Không có dữ liệu để chơi.[/]")
        except Exception as e:
            _handle_error(f"❌ Lỗi khi khởi tạo trò chơi: {e}")

    def check_all_integrity(self):
        """Quét tất cả bộ đề và báo cáo lỗi định dạng."""
        _clear_screen()
        console.print(Panel(Align.center("[bold cyan]🔍 KIỂM TRA TOÀN DIỆN HỆ THỐNG[/]"), border_style="cyan"))
        
        files = self.file_mgr.get_files()
        if not files: return console.print("[yellow]⚠️ Không có file để kiểm tra.[/]")

        table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
        table.add_column("Bộ đề", style="bold white", width=30)
        table.add_column("Kết quả kiểm tra", justify="left")

        files_with_ansi = []
        with console.status("[bold green]Đang quét dữ liệu...[/]"):
            for f_name in files:
                path = os.path.join(self.file_mgr.qdir, f_name)
                errors = self.card_mgr.validate_file(path)
                if any("mã ANSI" in e for e in errors):
                    files_with_ansi.append(path)
                
                res = "\n".join([f"• {e}" for e in errors]) if errors else "[green]✅ Sạch sẽ[/]"
                table.add_row(f_name, res)

        console.print(table)
        
        if files_with_ansi:
            prompt = f"\n[bold yellow]💡 Phát hiện {len(files_with_ansi)} bộ đề chứa mã ANSI cũ. Tự động sửa lỗi? (y/n): [/]"
            if console.input(prompt).strip().lower() == 'y':
                count = 0
                for p in files_with_ansi:
                    if self.card_mgr.fix_ansi_in_file(p): count += 1
                console.print(f"[bold green]✅ Đã tự động chuyển đổi thành công {count} file![/]")
                time.sleep(1.5)
                return self.check_all_integrity() # Quét lại để cập nhật bảng kết quả

        console.input(f"\n[{_CONFIG.COLOR_INFO}]Nhấn Enter để quay lại...[/]")

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
        opts = {
            "1": (self.check_all_integrity, "🔍 Quét lỗi toàn hệ thống"),
            "2": (lambda: (p := self._choose_file_path()) and (self.card_mgr.show_questions(p) or self._run_question_crud_menu(p)), "📂 Chọn bộ đề biên tập"),
            "0": (lambda: None, "Quay lại")
        }
        self.run_menu("📦 QUẢN LÝ NỘI DUNG", opts, show_sidebar=False, clear=True)

    def manage_f_menu(self):
        f = self.file_mgr
        opts = {
            "1": (f.create_file, "🆕 Tạo bộ đề"), "2": (lambda: (p := self._choose_file_path()) and f.delete_file(p), "⚠️ Xoá bộ đề"),
            "3": (lambda: (p := self._choose_file_path()) and f.rename_file(p), "🏷️ Đổi tên"), "0": (lambda: None, "Quay lại")
        }
        self.run_menu("📂 HỆ THỐNG LƯU TRỮ", opts, show_file_list=True, show_sidebar=False, clear=False)