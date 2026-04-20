import os, getpass
from src.core import _CONFIG, console, _clear_screen, _get_now
from src.utils import (
    _handle_error, _move_to_trash,
    _show_stats_util, _get_history_table_util, _choose_file_path_util, _play_action_util,
    _check_all_integrity_util, _clear_history_util, _empty_trash_util, _safe_input,
    _handle_manage_questions_for_path_util, _handle_file_deletion_util,
    _clear_logs_util
)
from src.process_file import FileManager
from src.process_flashcard import FlashcardManager
from src.process_categories import CategoryManager
from src.process_log import LogManager, log_action
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich import box
from rich.console import Group
from rich.columns import Columns

class MenuManager:
    def __init__(self):
        self.file_mgr = FileManager()
        self.card_mgr = FlashcardManager()
        self.cate_mgr = CategoryManager()

    def show_stats(self):
        return _show_stats_util(self.file_mgr)

    def get_history_table(self):
        return _get_history_table_util()

    def _choose_file_path(self, allow_all=False):
        return _choose_file_path_util(self.file_mgr, allow_all)

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
            ch = console.input(f"\n👉 Lệnh của bạn: ").strip().lower()
            if ch in options: options[ch][0]()
            if ch in ["0", "exit", "/exit"]: break

    def play_action(self, all_files=False):
        _play_action_util(self.file_mgr, self.card_mgr, self, all_files)

    def check_all_integrity(self):
        _check_all_integrity_util(self.file_mgr, self.card_mgr)

    def _handle_manage_questions_for_path(self):
        _handle_manage_questions_for_path_util(self.file_mgr, self.card_mgr, self)

    def _run_category_crud_menu(self):
        """Chạy menu CRUD cho quản lý từ khóa lọc."""
        c = self.cate_mgr
        opts = {
            "1": (c.add_category, "📝 Thêm từ khóa"),
            "2": (c.delete_category, "🗑️ Xoá từ khóa"),
            "3": (c.edit_category, "🛠️ Sửa từ khóa"),
            "0": (lambda: None, "Quay lại")
        }
        self.run_menu("🏷️ QUẢN LÝ TỪ KHÓA LỌC", opts, show_sidebar=False, clear=True)

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
            "2": (self._handle_manage_questions_for_path, "📂 Chọn bộ đề biên tập"),
            "3": (self._run_category_crud_menu, "🏷️ Quản lý từ khóa lọc"),
            "0": (lambda: None, "Quay lại")
        }
        self.run_menu("📦 QUẢN LÝ NỘI DUNG", opts, show_sidebar=False, clear=True)

    def clear_history(self):
        _clear_history_util()

    def clear_logs(self):
        _clear_logs_util()

    def empty_trash(self):
        _empty_trash_util()

    def _handle_file_deletion(self):
        _handle_file_deletion_util(self.file_mgr)

    def _handle_create_file_flow(self):
        """Luồng tạo file mới và hỏi người dùng có muốn thêm nội dung ngay không."""
        path = self.file_mgr.create_file()
        if path:
            fname = os.path.basename(path)
            confirm = _safe_input(f"\n💡 Bạn vừa tạo file [{fname}], bạn có muốn thêm nội dung ngay không? (y/n): ")
            if confirm and confirm.lower() == 'y':
                self.card_mgr.add_question(path)

    def manage_f_menu(self):
        opts = {
            "1": (self._handle_create_file_flow, "🆕 Tạo bộ đề"),
            "2": (lambda: (self._handle_file_deletion(), self.card_mgr.clear_cache()), "⚠️ Xoá bộ đề"),
            "3": (self._handle_rename_flow, "🏷️ Đổi tên"),
            "0": (lambda: None, "Quay lại")
        }
        self.run_menu("📂 HỆ THỐNG LƯU TRỮ", opts, show_file_list=True, show_sidebar=False, clear=False)

    def _handle_rename_flow(self):
        path = self._choose_file_path()
        if path:
            self.file_mgr.rename_file(path)
            self.card_mgr.clear_cache(path) # Xoá cache đường dẫn cũ