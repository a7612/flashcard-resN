import os, csv, time, datetime, re
from src.core import _CONFIG, console, VN_TZ
from src.utils import _safe_input, _handle_error, _get_now, _move_to_trash
from src.process_log import log_action
from rich.table import Table
from rich import box
import src.process_input as inp

class FileManager:
    def __init__(self):
        self.qdir = _CONFIG.QUESTIONS_DIR
        # Cache lưu cấu trúc: { filename: (last_mtime, last_size, last_count) }
        self._count_cache = {}
        # Dễ dàng chỉnh sửa các mốc phân loại tại đây
        self.thresholds = [
            (1, "[red]🌑 Trống[/]", "red"),
            (16, "[yellow]🚧 Cần bổ sung[/]", "yellow"),
            (22, "[cyan]📂 Đang biên soạn[/]", "cyan"),
            (float('inf'), "[bold green]💎 Đủ chỉ tiêu[/]", "bold green")
        ]
        self.search_keyword = None
        self.auto_cleanup_trash()

    def auto_cleanup_trash(self):
        """Tự động xoá các file trong trash đã cũ hơn 30 ngày."""
        trash_dir = _CONFIG.TRASH_DIR
        if not os.path.exists(trash_dir): return
        
        now = time.time()
        expiry_seconds = 30 * 86400 # 30 ngày
        count = 0
        try:
            for f in os.listdir(trash_dir):
                fpath = os.path.join(trash_dir, f)
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath) > expiry_seconds):
                    os.remove(fpath)
                    count += 1
            if count > 0:
                log_action("AUTO_TRASH_CLEANUP", f"Deleted {count} expired files")
        except: pass

    def _get_full_path(self, fname):
        return os.path.join(self.qdir, fname)

    def get_files(self):
        try:
            files = []
            for f in os.listdir(self.qdir):
                if f.endswith(".csv"):
                    files.append(f)
            # Sử dụng FILE_SORT_BY cho logic sắp xếp nội bộ (chủ yếu theo tên)
            mode = getattr(_CONFIG, 'FILE_SORT_BY', 'name_asc')
            return sorted(files, reverse=(mode == "name_desc"))
        except Exception as e:
            console.print(f"[red]❌ Không thể truy cập thư mục dữ liệu: {e}[/]")
            return []

    def count_questions(self, fname):
        path = self._get_full_path(fname)
        try: 
            # 1. Kiểm tra Metadata của file
            stat = os.stat(path)
            mtime, size = stat.st_mtime, stat.st_size

            # 2. Nếu file không đổi, trả về kết quả trong cache ngay lập tức (O(1))
            if fname in self._count_cache:
                c_mtime, c_size, c_count = self._count_cache[fname]
                if mtime == c_mtime and size == c_size:
                    return c_count

            if size == 0: return 0

            # 3. Nếu file đổi hoặc chưa có trong cache, đếm cực nhanh bằng khối nhị phân
            with open(path, "rb") as f:
                count = sum(buf.count(b'\n') for buf in iter(lambda: f.read(1024 * 1024), b''))
                
                # Kiểm tra nếu byte cuối cùng không phải là newline thì cộng thêm 1 dòng
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b'\n':
                    count += 1
                
            # Trừ 1 dòng header (Giả định file CSV chuẩn luôn có header và kết thúc bằng newline)
            final_count = max(0, count - 1)
            self._count_cache[fname] = (mtime, size, final_count)
            return final_count
        except Exception as e:
            # Đừng dùng _handle_error ở đây để tránh làm gián đoạn luồng hiển thị danh sách
            return 0

    def _get_status_info(self, count):
        """Trả về (văn bản trạng thái, màu sắc) dựa trên số lượng câu hỏi."""
        for limit, label, color in self.thresholds:
            if count < limit or limit == float('inf'):
                return label, color
        return self.thresholds[-1][1], self.thresholds[-1][2]

    def list_files(self, show=True, return_table=False):
        files = self.get_files()
        # Thu thập metadata để hỗ trợ nhiều kiểu sắp xếp: (filename, count, mtime)
        files_meta = []
        for f in files:
            files_meta.append((f, self.count_questions(f), os.path.getmtime(self._get_full_path(f))))

        # Logic sắp xếp dựa trên cấu hình
        mode = getattr(_CONFIG, 'FILE_DISPLAY_SORT_BY', 'count_desc')
        if mode == "name_asc":
            files_meta.sort(key=lambda x: x[0].lower())
        elif mode == "name_desc":
            files_meta.sort(key=lambda x: x[0].lower(), reverse=True)
        elif mode == "count_asc":
            files_meta.sort(key=lambda x: (x[1], x[0].lower()))
        elif mode == "mtime_asc":
            files_meta.sort(key=lambda x: x[2])
        elif mode == "mtime_desc":
            files_meta.sort(key=lambda x: x[2], reverse=True)
        else: # Mặc định: count_desc
            files_meta.sort(key=lambda x: (-x[1], x[0].lower()))

        # Logic Tìm kiếm & Lọc
        if self.search_keyword:
            filtered = [m for m in files_meta if self.search_keyword.lower() in m[0].lower()]
            if not filtered:
                if show:
                    console.print(f"\n[{_CONFIG.COLOR_ERROR}]❌ Không thể tìm thấy bộ đề nào chứa từ khóa: '{self.search_keyword}'[/]")
                return ([], None) if return_table else []
            files_meta = filtered

        table = None
        if show or return_table:
            table = Table(title="📂 KHO DỮ LIỆU HỆ THỐNG", box=box.SIMPLE_HEAD)
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Tên Bộ Đề", style="bold white")
            table.add_column("Số câu", justify="right")
            table.add_column("Trạng thái", justify="left")
            table.add_column("Cập nhật", justify="left")
            
            for i, (f, c, mtime_ts) in enumerate(files_meta, 1):
                status, color = self._get_status_info(c)
                
                mtime_dt = datetime.datetime.fromtimestamp(mtime_ts, tz=VN_TZ)
                diff = _get_now() - mtime_dt
                
                # Xác định màu sắc và nội dung dựa trên độ trễ
                if diff.days < 3:
                    t_style = _CONFIG.COLOR_SUCCESS
                    t_msg = "Hôm nay" if diff.days == 0 else f"{diff.days} ngày trước"
                elif diff.days < 7:
                    t_style = _CONFIG.COLOR_WARNING
                    t_msg = f"{diff.days} ngày trước"
                else:
                    t_style = _CONFIG.COLOR_ERROR
                    t_msg = f"{diff.days // 7} tuần trước" if diff.days >= 14 else f"{diff.days} ngày trước"
                
                updated_display = f"[{t_style}]{mtime_dt.strftime('%d/%m %H:%M')} ({t_msg})[/]"
                # Highlight ID nếu đang ở chế độ tìm kiếm
                id_display = f"[bold yellow]{i}[/]" if self.search_keyword else str(i)
                table.add_row(id_display, f"📚 {f}", f"[{color}]{c}[/]", status, updated_display)
            
            if show:
                console.print(table)
                
        file_list = [m[0] for m in files_meta]
        return (file_list, table) if return_table else file_list

    def create_file(self):
        name = inp.input_deck_name()
        if name is None: return None # Thoát nếu nhập /exit
        
        # Tự động lọc bỏ các ký tự không hợp lệ cho tên file
        name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
        if not name:
            _handle_error("❌ Tên bộ đề không hợp lệ sau khi lọc ký tự đặc biệt!")
            return None

        # Kiểm tra độ dài tên file
        if len(name) > 50:
            _handle_error("❌ Tên bộ đề quá dài (Tối đa 50 ký tự)!")
            return None
        
        filename = name if name.lower().endswith(".csv") else f"{name}.csv"

        # Xác nhận trước khi tạo
        if inp.input_confirm_generic(f"❓ Bạn có chắc muốn tạo bộ đề '{filename}'? (y/n): ") != 'y':
            return None

        p = self._get_full_path(filename)
        if os.path.exists(p):
            console.print("[yellow]⚠️ File đã tồn tại![/]")
            return None
            
        try:
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(["id", "answer", "question", "hint", "desc"])
            log_action("CREATE", p)
            console.print(f"[green]🆕 Đã tạo thành công: {filename}[/]"); time.sleep(1)
            return p
        except Exception as e:
            _handle_error(f"❌ Lỗi hệ thống không thể tạo file '{filename}': {e}")
            return None

    def delete_file(self, path):
        confirm = inp.confirm_delete(os.path.basename(path))
        if confirm != "y": return
        
        try:
            _move_to_trash(path)
            log_action("DELETE", path)
            console.print("[yellow]📂 Đã chuyển file vào thùng rác (trash/).[/]"); time.sleep(1)
        except Exception as e:
            _handle_error(f"❌ Không thể xoá file '{os.path.basename(path)}': {e}")

    def delete_all_files(self):
        files = self.get_files()
        if not files: return
        confirm = inp.confirm_delete(f"{len(files)} bộ đề", is_all=True)
        if confirm != "y": return
        
        for f in files:
            try:
                _move_to_trash(self._get_full_path(f))
            except: pass
        log_action("DELETE_ALL_FILES", f"Removed {len(files)} files")
        console.print("[bold yellow]♻️ Đã dọn sạch kho dữ liệu vào thùng rác![/]"); time.sleep(1)

    def rename_file(self, path):
        old_name = os.path.basename(path)
        new = inp.input_rename_deck()
        if new is None: return # Thoát nếu nhập /exit
        
        # Tự động lọc bỏ các ký tự không hợp lệ cho tên file
        new = re.sub(r'[<>:"/\\|?*]', '', new).strip()
        if not new:
            _handle_error("❌ Tên mới không hợp lệ!")
            return
        
        # Kiểm tra độ dài
        if len(new) > 50:
            _handle_error("❌ Tên mới quá dài (Tối đa 50 ký tự)!")
            return

        new_filename = new if new.lower().endswith(".csv") else f"{new}.csv"
        
        # Xác nhận trước khi đổi tên
        if inp.input_confirm_generic(f"❓ Đổi tên '{old_name}' thành '{new_filename}'? (y/n): ") != 'y':
            return

        new_path = self._get_full_path(new_filename)
        try:
            os.rename(path, new_path)
            log_action("RENAME", f"{path}->{new_path}")
            console.print(f"[green]🏷️ Đã đổi tên bộ đề thành '{new_filename}' thành công.[/]"); time.sleep(1)
        except Exception as e:
            _handle_error(f"❌ Không thể đổi tên thành '{new_filename}': {e}")