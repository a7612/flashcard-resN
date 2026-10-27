import os, getpass, re
from src.core import _CONFIG, console, _clear_screen, _get_now
from src.utils import (
    _handle_error, _move_to_trash,
    _show_stats_util, _get_history_table_util, _choose_file_path_util, _play_action_util,
    _clear_history_util, _empty_trash_util, _safe_input,
    _handle_manage_questions_for_path_util, _handle_file_deletion_util,
    _clear_logs_util,
    _manage_filter_categories_util,
    _manage_filter_wordbank_util,
    _show_mistake_stats_util,
    _play_mistake_review_util
)
from src.process_file import FileManager
from src.process_flashcard import FlashcardManager
from src.process_log import LogManager, log_action
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
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

    def _choose_file_path(self, allow_all=False, show=True, context_name=""):
        return _choose_file_path_util(self.file_mgr, allow_all, show=show, context_name=context_name)

    def run_menu(self, title, options, show_file_list=False, show_sidebar=True, clear=True, show_questions_path=None):
        while True:
            if clear: _clear_screen()
            
            header_text = Text.from_markup(f"[bold white]🚀 {title} 🚀[/]\n[{_CONFIG.COLOR_INFO}]User: {getpass.getuser()} | {_get_now().strftime('%d/%m/%Y %H:%M')}[/]", justify="center")
            console.print(Panel(header_text, box=box.ROUNDED, border_style=_CONFIG.COLOR_HEADER))
            opt_table = Table(show_header=False, box=None, padding=(0, 1))
            for k, v in options.items():
                # Xác định màu sắc: /exit hoặc 0 đỏ, lệnh bắt đầu bằng / xanh lá, còn lại (số) xanh lơ
                style = "bold red" if k in ["/exit", "0"] else "bold green" if k.startswith("/") else "bold cyan"
                opt_table.add_row(f"[{style}]{k}[/]", v[1])

            menu_panel = Panel(opt_table, title=f"[bold {_CONFIG.COLOR_MENU}]🎮 MENU[/]", border_style=_CONFIG.COLOR_MENU, expand=False)
            
            # Chuẩn bị nội dung bên phải (Ưu tiên File List, Chi tiết câu hỏi, sau đó tới History)
            right_content = None
            if show_file_list:
                _, right_content = self.file_mgr.list_files(show=False, return_table=True)
            elif show_questions_path:
                _, right_content = self.card_mgr.show_questions(show_questions_path, return_table=True)
            elif show_sidebar and _CONFIG.SHOW_HISTORY:
                right_content = self.get_history_table()

            if show_sidebar or show_file_list or show_questions_path:
                left_elements = [menu_panel]
                if show_sidebar and _CONFIG.SHOW_STATS and not show_questions_path:
                    left_elements.append(self.show_stats())
                
                left_col = Group(*left_elements)
                if right_content:
                    console.print(Columns([left_col, right_content], padding=(0, 4), expand=False))
                else:
                    console.print(left_col)
            else:
                console.print(menu_panel)
            ch = inp.input_menu_choice()
            if ch in options: options[ch][0]()
            if ch in ["0", "exit", "/exit"]: 
                break

    def play_action(self, all_files=False):
        _play_action_util(self.file_mgr, self.card_mgr, self, all_files)

    def show_mistake_stats(self):
        _show_mistake_stats_util(self.file_mgr, self.card_mgr)

    def play_mistake_review(self, target_score=10):
        _play_mistake_review_util(self.file_mgr, self.card_mgr, target_score=target_score)

    def _handle_manage_questions_for_path(self):
        _handle_manage_questions_for_path_util(self.file_mgr, self.card_mgr, self)

    def _run_question_crud_menu(self, path):
        """Chạy menu CRUD cho các câu hỏi trong một file cụ thể."""
        m = self.card_mgr
        opts = {
            "1": (lambda: m.add_question(path), "[green]Thêm câu[/]"),
            "2": (lambda: m.delete_question(path), "[red]Xoá câu[/]"),
            "3": (lambda: m.edit_question(path), "[yellow]Sửa tổng lực[/]"),
            "4": (lambda: m.edit_question(path, 2), "[yellow]Sửa câu hỏi[/]"),
            "5": (lambda: m.edit_question(path, 1), "[yellow]Sửa đáp án[/]"),
            "6": (lambda: m.edit_question(path, 3), "[yellow]Sửa gợi ý[/]"),
            "7": (lambda: m.edit_question(path, 4), "[yellow]Sửa mô tả[/]"),
            "0": (lambda: None, "Quay lại")
        }
        self.run_menu(f"⚙️ BIÊN TẬP: {os.path.basename(path)}", opts, show_file_list=False, show_sidebar=False, clear=True, show_questions_path=path)

    def manage_q_menu(self):
        self.file_mgr.search_keyword = None # Reset tìm kiếm khi bắt đầu vào menu
        is_num = _CONFIG.MENU_MODE == "numeric"
        opts = {
            ("1" if is_num else "/c"): (self._handle_manage_questions_for_path, "[green]Biên tập nội dung[/]"),
            ("2" if is_num else "/keyword"): (lambda: _manage_filter_categories_util(self.file_mgr, self.card_mgr), f"[yellow]Quản lý từ khóa[/]"),
            ("3" if is_num else "/wordbank"): (lambda: _manage_filter_wordbank_util(self.file_mgr, self.card_mgr), f"[yellow]Quản lý Word Bank[/]\n"),
            ("4" if is_num else "/create"): (self._handle_create_file_flow, "[green]Tạo bộ đề mới[/]"),
            ("5" if is_num else "/rename"): (self._handle_rename_flow, "[yellow]Đổi tên bộ đề[/]"),
            ("6" if is_num else "/delete"): (lambda: (self._handle_file_deletion(show_list=False), self.card_mgr.clear_cache()), f"[red]Xoá bộ đề[/]"),           
            ("7" if is_num else "/search"): (self._handle_search_files, f"[cyan]Tìm kiếm bộ đề[/]"),
            ("8" if is_num else "/disable"): (self._handle_toggle_disable_flow, "[red]Vô hiệu hóa/[yellow]Mở lại[/]"),
            ("0" if is_num else "/exit"): (lambda: None, "Quay lại")
        }
        self.run_menu("📦 QUẢN LÝ HỆ THỐNG", opts, show_file_list=True, show_sidebar=True, clear=True)

    def _handle_search_files(self):
        """Xử lý nhập từ khóa và gán vào FileManager."""
        kw = inp.input_search_file()
        self.file_mgr.search_keyword = kw if kw else None

    def _handle_toggle_disable_flow(self):
        """Xử lý bật/tắt trạng thái vô hiệu hóa bộ đề."""
        path = self._choose_file_path(show=False, context_name="Vô hiệu hóa/Mở lại")
        if path:
            self.file_mgr.toggle_disable(os.path.basename(path))

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
        path = self._choose_file_path(show=False, context_name="Đổi tên bộ đề")
        if path:
            self.file_mgr.rename_file(path)
            self.card_mgr.clear_cache(path) # Xoá cache đường dẫn cũ

    def settings_menu(self):
        """Menu quản lý các cài đặt trong settings.json."""
        while True:
            _clear_screen()
            header_text = Text.from_markup(f"[bold white]⚙️ CÀI ĐẶT HỆ THỐNG ⚙️[/]\n[{_CONFIG.COLOR_INFO}]Cấu hình được lưu trong settings.json[/]", justify="center")
            console.print(Panel(header_text, box=box.ROUNDED, border_style=_CONFIG.COLOR_HEADER))

            # Nhóm 1: Hệ thống & Tệp tin
            group1 = [
                ("1", "Độ dài tên file tối đa", str(_CONFIG.MAX_FILENAME_LENGTH)),
                ("2", "Cột lọc trùng lặp (ID=0, Nội dung=2)", str(_CONFIG.DEDUPLICATE_COLUMN_INDEX)),
                ("3", "Thời gian chờ thông báo (giây)", str(_CONFIG.ERROR_DELAY))
            ]

            # Nhóm 2: Giao diện & Hiển thị (Đã bổ sung Sắp xếp)
            group2 = [
                ("4", "Tự động xoá màn hình", str(_CONFIG.CLEAR_SCREEN)),
                ("5", "Hiển thị Thống kê", str(_CONFIG.SHOW_STATS)),
                ("6", "Hiển thị Lịch sử", str(_CONFIG.SHOW_HISTORY)),
                ("7", "Sắp xếp bộ đề (File)", str(_CONFIG.FILE_DISPLAY_SORT_BY)),
                ("8", "Sắp xếp câu hỏi (Flashcard)", str(_CONFIG.QUESTION_SORT_BY)),
                ("9", "Chế độ Menu", str(_CONFIG.MENU_MODE).upper())
            ]

            # Nhóm 3: Quiz & Nội dung (Cập nhật bổ sung Fuzzy Matching)
            group3 = [
                ("10", "Thời gian làm bài mỗi câu", f"{getattr(_CONFIG, 'QUIZ_TIME_LIMIT', 0)}s"),
                ("11", "Đánh giá độ khó", "BẬT" if getattr(_CONFIG, 'ENABLE_DIFFICULTY_RATING', False) else "TẮT"),
                ("12", "Fuzzy Matching (Chấm gần đúng)", "BẬT" if getattr(_CONFIG, 'FUZZY_MATCHING_ENABLED', False) else "TẮT"),
                ("13", "Ngưỡng Fuzzy (0.0 - 1.0)", str(_CONFIG.FUZZY_MATCHING_THRESHOLD)),
                ("14", "Từ khóa ĐÚNG/SAI", str(_CONFIG.KEYWORD_BOOL)),
                ("15", "Từ khóa câu hỏi nhập liệu", str(_CONFIG.KEYWORD_Q_INPUT)),
                ("16", "Chỉnh sửa sau khi trả lời", "BẬT" if getattr(_CONFIG, 'EDIT_AFTER_ANSWER', False) else "TẮT")
            ]

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_row("[bold cyan]=== HỆ THỐNG ===[/]", "", "")
            for k, l, v in group1: table.add_row(k, l, f"[bold green]{v}[/]")
            table.add_row("[bold cyan]=== GIAO DIỆN ===[/]", "", "")
            for k, l, v in group2: table.add_row(k, l, f"[bold green]{v}[/]")
            table.add_row("[bold cyan]=== NỘI DUNG/QUIZ ===[/]", "", "")
            for k, l, v in group3: table.add_row(k, l, f"[bold green]{v}[/]")
            table.add_row("0", "[bold red]Quay lại[/]", "")

            console.print(Panel(table, title=f"[bold {_CONFIG.COLOR_MENU}]🛠️ TÙY CHỈNH[/]", border_style=_CONFIG.COLOR_MENU, box=box.ROUNDED, expand=False))

            ch = inp.input_menu_choice()
            if ch == "1":
                val = _safe_input("📏 Độ dài mới: ")
                if val and val.isdigit(): self._update_config_persistence("MAX_FILENAME_LENGTH", int(val))
            elif ch == "2":
                val = _safe_input("🔍 Cột trùng lặp (0/2): ")
                if val in ["0", "2"]: self._update_config_persistence("DEDUPLICATE_COLUMN_INDEX", int(val))
            elif ch == "3":
                val = _safe_input("⏳ Thời gian (giây): ")
                if val and val.isdigit(): self._update_config_persistence("ERROR_DELAY", int(val))
            elif ch == "4":
                self._update_config_persistence("CLEAR_SCREEN", not _CONFIG.CLEAR_SCREEN)
            elif ch == "5":
                self._update_config_persistence("SHOW_STATS", not _CONFIG.SHOW_STATS)
            elif ch == "6":
                self._update_config_persistence("SHOW_HISTORY", not _CONFIG.SHOW_HISTORY)
            elif ch == "7":
                modes = ["count_desc", "count_asc", "name_asc", "name_desc", "mtime_desc", "mtime_asc"]
                idx = modes.index(_CONFIG.FILE_DISPLAY_SORT_BY) if _CONFIG.FILE_DISPLAY_SORT_BY in modes else 0
                self._update_config_persistence("FILE_DISPLAY_SORT_BY", modes[(idx + 1) % len(modes)])
            elif ch == "8":
                modes = ["id_asc", "id_desc", "answer_asc", "answer_desc", "question_asc", "question_desc"]
                idx = modes.index(_CONFIG.QUESTION_SORT_BY) if _CONFIG.QUESTION_SORT_BY in modes else 0
                self._update_config_persistence("QUESTION_SORT_BY", modes[(idx + 1) % len(modes)])
            elif ch == "9":
                self._update_config_persistence("MENU_MODE", "numeric" if _CONFIG.MENU_MODE == "command" else "command")
            elif ch == "10":
                val = _safe_input("⏱️ Giới hạn (giây): ")
                if val and val.isdigit(): self._update_config_persistence("QUIZ_TIME_LIMIT", int(val))
            elif ch == "11":
                self._update_config_persistence("ENABLE_DIFFICULTY_RATING", not getattr(_CONFIG, 'ENABLE_DIFFICULTY_RATING', False))
            elif ch == "12":
                self._update_config_persistence("FUZZY_MATCHING_ENABLED", not getattr(_CONFIG, 'FUZZY_MATCHING_ENABLED', False))
            elif ch == "13":
                val = _safe_input("🎯 Nhập ngưỡng (VD: 0.9): ")
                if val:
                    try: self._update_config_persistence("FUZZY_MATCHING_THRESHOLD", float(val))
                    except: _handle_error("❌ Giá trị không hợp lệ!")
            elif ch == "14":
                val = _safe_input("📝 Danh sách (cách nhau bởi dấu phẩy): ")
                if val: self._update_config_persistence("KEYWORD_BOOL", [k.strip() for k in val.split(',')])
            elif ch == "15":
                val = _safe_input("📝 Danh sách (cách nhau bởi dấu phẩy): ")
                if val: self._update_config_persistence("KEYWORD_Q_INPUT", [k.strip() for k in val.split(',')])
            elif ch == "16":
                self._update_config_persistence("EDIT_AFTER_ANSWER", not getattr(_CONFIG, 'EDIT_AFTER_ANSWER', False))
            elif ch in ["0", "q", "exit"]:
                break

    def _update_config_persistence(self, key, value):
        import json
        try:
            # 1. Cập nhật vào memory
            setattr(_CONFIG, key, value)

            # 2. Lưu lại toàn bộ object _CONFIG vào file settings.json
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(_CONFIG.__dict__, f, indent=4)

            log_action("CONFIG_CHANGE", f"{key} set to {value}")
        except Exception as e:
            _handle_error(f"Lỗi khi lưu cấu hình: {e}")

