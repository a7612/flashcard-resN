import os, getpass, re
from src.core import _CONFIG, console, _clear_screen, _get_now
from src.utils import (
    _handle_error, _move_to_trash,
    _show_stats_util, _get_history_table_util, _choose_file_path_util, _play_action_util,
    _check_all_integrity_util, _clear_history_util, _empty_trash_util, _safe_input,
    _handle_manage_questions_for_path_util, _handle_file_deletion_util,
    _clear_logs_util,
    _manage_filter_categories_util
)
from src.process_file import FileManager
from src.process_flashcard import FlashcardManager
from src.process_log import LogManager, log_action
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich import box
from rich.console import Group
from rich.columns import Columns
import src.process_input as inp
from src.utils import _clear_screen


class MenuManager:
    def __init__(self):
        self.file_mgr = FileManager()
        self.card_mgr = FlashcardManager()

    def show_stats(self):
        return _show_stats_util(self.file_mgr)

    def get_history_table(self):
        return _get_history_table_util()

    def _choose_file_path(self, allow_all=False, show=True):
        return _choose_file_path_util(self.file_mgr, allow_all, show=show)

    def run_menu(self, title, options, show_file_list=False, show_sidebar=True, clear=True, show_questions_path=None):
        while True:
            if clear: _clear_screen()
            header = f"[bold white]🚀 {title} 🚀[/]\n[{_CONFIG.COLOR_INFO}]User: {getpass.getuser()} | {_get_now().strftime('%d/%m/%Y %H:%M')}[/]"
            console.print(Panel(Align.center(header), box=box.DOUBLE, border_style=_CONFIG.COLOR_HEADER))
            opt_table = Table(show_header=False, box=box.ROUNDED, border_style=_CONFIG.COLOR_MENU)
            for k, v in options.items():
                # Xác định màu sắc: /exit đỏ, lệnh bắt đầu bằng / xanh lá, còn lại (số) xanh lơ
                style = "bold red" if k == "/exit" else "bold green" if k.startswith("/") else "bold cyan"
                opt_table.add_row(f"[{style}]{k}[/]", v[1])

            menu_panel = Panel(opt_table, title=f"[bold {_CONFIG.COLOR_MENU}]🎮 MENU[/]", border_style=_CONFIG.COLOR_MENU, expand=False)
            
            # Chuẩn bị nội dung bên phải (Ưu tiên File List, sau đó tới History)
            right_content = None
            if show_file_list:
                _, right_content = self.file_mgr.list_files(show=False, return_table=True)
            elif show_sidebar and _CONFIG.SHOW_HISTORY:
                right_content = self.get_history_table()

            if show_sidebar or show_file_list:
                left_elements = [menu_panel]
                if show_sidebar and _CONFIG.SHOW_STATS:
                    left_elements.append(self.show_stats())
                
                left_col = Group(*left_elements)
                if right_content:
                    console.print(Columns([left_col, right_content], padding=(0, 4), expand=False))
                else:
                    console.print(left_col)
            else:
                console.print(menu_panel)

            if show_questions_path: self.card_mgr.show_questions(show_questions_path)
            ch = inp.input_menu_choice()
            if ch in options: options[ch][0]()
            if ch in ["0", "exit", "/exit"]: 
                break

    def play_action(self, all_files=False):
        _play_action_util(self.file_mgr, self.card_mgr, self, all_files)

    def check_all_integrity(self):
        log_action("SYSTEM_CHECK", "Started comprehensive integrity scan")
        _check_all_integrity_util(self.file_mgr, self.card_mgr)

    def _handle_manage_questions_for_path(self):
        _handle_manage_questions_for_path_util(self.file_mgr, self.card_mgr, self)

    def _run_question_crud_menu(self, path):
        """Chạy menu CRUD cho các câu hỏi trong một file cụ thể."""
        m = self.card_mgr
        opts = {
            "1": (lambda: (m.add_question(path), self.file_mgr._count_cache.pop(os.path.basename(path), None)), "📝 Thêm câu"),
            "2": (lambda: (m.delete_question(path), self.file_mgr._count_cache.pop(os.path.basename(path), None)), "🗑️ Xoá câu"),
            "3": (lambda: m.edit_question(path), "🛠️ Sửa tổng lực"),
            "4": (lambda: m.edit_question(path, 2), "🔍 Sửa câu hỏi"),
            "5": (lambda: m.edit_question(path, 1), "💡 Sửa đáp án"),
            "0": (lambda: None, "Quay lại")
        }
        self.run_menu(f"⚙️ BIÊN TẬP: {os.path.basename(path)}", opts, show_file_list=False, show_sidebar=False, clear=False)

    def manage_q_menu(self):
        self.file_mgr.search_keyword = None # Reset tìm kiếm khi bắt đầu vào menu
        opts = {
            "/c": (self._handle_manage_questions_for_path, "📂 Biên tập nội dung"),
            "/keyword": (lambda: _manage_filter_categories_util(self.file_mgr, self.card_mgr), f"🏷️ Quản lý từ khóa\n{"[red]="*22}"),
            "/create": (self._handle_create_file_flow, "🆕 Tạo bộ đề mới"),
            "/rename": (self._handle_rename_flow, "🏷️ Đổi tên bộ đề"),
            "/delete": (lambda: (self._handle_file_deletion(show_list=False), self.card_mgr.clear_cache()), f"⚠️ Xoá bộ đề\n{"[red]="*22}"),
            "/check": (self.check_all_integrity, "🔍 Kiểm tra lỗi dữ liệu"),            
            "/search": (self._handle_search_files, f"🔍 Tìm kiếm bộ đề\n{"[red]="*22}"),
            "/exit": (lambda: None, "Quay lại")
        }
        self.run_menu("📦 QUẢN LÝ HỆ THỐNG", opts, show_file_list=True, show_sidebar=True, clear=True)

    def _handle_search_files(self):
        """Xử lý nhập từ khóa và gán vào FileManager."""
        kw = inp.input_search_file()
        self.file_mgr.search_keyword = kw if kw else None

    def clear_history(self):
        _clear_history_util()

    def clear_logs(self):
        _clear_logs_util()

    def empty_trash(self):
        _empty_trash_util()

    def _handle_file_deletion(self, show_list=True):
        _handle_file_deletion_util(self.file_mgr, show_list=show_list)

    def _handle_create_file_flow(self):
        """Luồng tạo file mới."""
        self.file_mgr.create_file()

    def _handle_rename_flow(self):
        path = self._choose_file_path(show=False)
        if path:
            self.file_mgr.rename_file(path)
            self.card_mgr.clear_cache(path) # Xoá cache đường dẫn cũ

    def settings_menu(self):
        """Menu quản lý các cài đặt trong config.py."""
        while True:
            _clear_screen()
            header = f"[bold white]⚙️ CÀI ĐẶT HỆ THỐNG ⚙️[/]\n[{_CONFIG.COLOR_INFO}]Cấu hình hiện tại có hiệu lực ngay lập tức[/]"
            console.print(Panel(Align.center(header), box=box.DOUBLE, border_style=_CONFIG.COLOR_HEADER))

            table = Table(show_header=False, box=box.ROUNDED, border_style=_CONFIG.COLOR_MENU)
            opts_info = [
                ("1", "Tự động xoá màn hình (CLEAR_SCREEN)", str(_CONFIG.CLEAR_SCREEN)),
                ("2", "Thời gian chờ thông báo (ERROR_DELAY)", f"{_CONFIG.ERROR_DELAY} giây"),
                ("3", "Cột lọc trùng lặp (DEDUPLICATE_INDEX)", "ID (0)" if _CONFIG.DEDUPLICATE_COLUMN_INDEX == 0 else "Nội dung (2)"),
                ("4", "Hiển thị Thống kê (SHOW_STATS)", str(_CONFIG.SHOW_STATS)),
                ("5", "Hiển thị Lịch sử (SHOW_HISTORY)", str(_CONFIG.SHOW_HISTORY)),
                ("6", "Sắp xếp hiển thị (FILE_DISPLAY_SORT_BY)", str(_CONFIG.FILE_DISPLAY_SORT_BY)),
                ("7", "Sắp xếp câu hỏi (QUESTION_SORT_BY)", str(_CONFIG.QUESTION_SORT_BY)),
                ("0", "Quay lại", "")
            ]
            for k, label, val in opts_info:
                table.add_row(k, f"{label}: [bold green]{val}[/]" if val else label)

            console.print(Panel(table, title=f"[bold {_CONFIG.COLOR_MENU}]🛠️ TÙY CHỈNH[/]", border_style=_CONFIG.COLOR_MENU, expand=False))
            
            ch = inp.input_menu_choice()
            if ch == "1":
                _CONFIG.CLEAR_SCREEN = not _CONFIG.CLEAR_SCREEN
                self._update_config_persistence("CLEAR_SCREEN", _CONFIG.CLEAR_SCREEN)
            elif ch == "2":
                val = inp.input_setting_delay()
                if val and val.isdigit():
                    _CONFIG.ERROR_DELAY = int(val)
                    self._update_config_persistence("ERROR_DELAY", _CONFIG.ERROR_DELAY)
            elif ch == "3":
                val = inp.input_setting_dedup()
                if val in ["0", "2"]:
                    _CONFIG.DEDUPLICATE_COLUMN_INDEX = int(val)
                    self._update_config_persistence("DEDUPLICATE_COLUMN_INDEX", _CONFIG.DEDUPLICATE_COLUMN_INDEX)
            elif ch == "4":
                _CONFIG.SHOW_STATS = not _CONFIG.SHOW_STATS
                self._update_config_persistence("SHOW_STATS", _CONFIG.SHOW_STATS)
            elif ch == "5":
                _CONFIG.SHOW_HISTORY = not _CONFIG.SHOW_HISTORY
                self._update_config_persistence("SHOW_HISTORY", _CONFIG.SHOW_HISTORY)
            elif ch == "6":
                modes = ["count_desc", "count_asc", "name_asc", "name_desc", "mtime_desc", "mtime_asc"]
                idx = modes.index(_CONFIG.FILE_DISPLAY_SORT_BY) if _CONFIG.FILE_DISPLAY_SORT_BY in modes else 0
                _CONFIG.FILE_DISPLAY_SORT_BY = modes[(idx + 1) % len(modes)]
                self._update_config_persistence("FILE_DISPLAY_SORT_BY", _CONFIG.FILE_DISPLAY_SORT_BY)
            elif ch == "7":
                modes = [
                    "id_asc", "id_desc", 
                    "answer_asc", "answer_desc", 
                    "question_asc", "question_desc",
                    "hint_asc", "hint_desc",
                    "desc_asc", "desc_desc"
                ]
                idx = modes.index(_CONFIG.QUESTION_SORT_BY) if _CONFIG.QUESTION_SORT_BY in modes else 0
                _CONFIG.QUESTION_SORT_BY = modes[(idx + 1) % len(modes)]
                self._update_config_persistence("QUESTION_SORT_BY", _CONFIG.QUESTION_SORT_BY)
                self.card_mgr.clear_cache() # Xóa cache để nạp lại và sắp xếp theo chuẩn mới
            elif ch in ["0", "q", "exit"]:
                break

    def _update_config_persistence(self, key, value):
        """Cập nhật giá trị vào file config.py để lưu lại sau khi thoát."""
        path = "config.py"
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(path, "w", encoding="utf-8") as f:
                for line in lines:
                    if re.match(rf"^\s*{key}\s*=", line):
                        # Giữ lại comment nếu có
                        comment = line[line.find("#"):].strip() if "#" in line else ""
                        f.write(f"{key} = {repr(value)} {'# ' + comment if comment else ''}\n".replace(" # #", " #"))
                    else:
                        f.write(line)
            log_action("CONFIG_CHANGE", f"{key} set to {value}")
        except Exception as e:
            _handle_error(f"Lỗi khi lưu cấu hình: {e}")