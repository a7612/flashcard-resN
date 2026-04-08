import os, csv, time, datetime
from src.core import _CONFIG, console, log_action, _safe_input, _handle_error, _get_now
from rich.table import Table
from rich import box

class FileManager:
    def __init__(self):
        self.qdir = _CONFIG.QUESTIONS_DIR
        self._cache = {}
        # Dễ dàng chỉnh sửa các mốc phân loại tại đây
        self.thresholds = [
            (1, "[red]🌑 Trống[/]", "red"),
            (16, "[yellow]🚧 Cần bổ sung[/]", "yellow"),
            (22, "[cyan]📂 Đang biên soạn[/]", "cyan"),
            (float('inf'), "[bold green]💎 Đủ chỉ tiêu[/]", "bold green")
        ]

    def _get_full_path(self, fname):
        return os.path.join(self.qdir, fname)

    def get_files(self):
        try:
            files = []
            for f in os.listdir(self.qdir):
                if f.endswith(".csv"):
                    files.append(f)
            return sorted(files)
        except Exception as e:
            console.print(f"[red]❌ Không thể truy cập thư mục dữ liệu: {e}[/]")
            return []

    def count_questions(self, fname):
        if fname in self._cache:
            return self._cache[fname]
            
        try: 
            with open(self._get_full_path(fname), encoding="utf-8-sig") as f:
                count = max(0, sum(1 for _ in f) - 1)
                self._cache[fname] = count
                return count
        except Exception as e:
            _handle_error(f"❌ Lỗi đếm câu hỏi trong file '{fname}': {e}")
            return 0

    def _get_status_info(self, count):
        """Trả về (văn bản trạng thái, màu sắc) dựa trên số lượng câu hỏi."""
        for limit, label, color in self.thresholds:
            if count < limit or limit == float('inf'):
                return label, color
        return self.thresholds[-1][1], self.thresholds[-1][2]

    def list_files(self, show=True):
        files = self.get_files()
        if show:
            table = Table(title="📂 KHO DỮ LIỆU HỆ THỐNG", box=box.SIMPLE_HEAD)
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Tên Bộ Đề", style="bold white")
            table.add_column("Số câu", justify="right")
            table.add_column("Trạng thái", justify="left")
            table.add_column("Cập nhật", justify="left")
            
            for i, f in enumerate(files, 1):
                c = self.count_questions(f)
                status, color = self._get_status_info(c)
                
                # Lấy thời gian cập nhật cuối cùng của file
                mtime_ts = os.path.getmtime(self._get_full_path(f))
                mtime_dt = datetime.datetime.fromtimestamp(mtime_ts, tz=datetime.timezone(datetime.timedelta(hours=7)))
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
                table.add_row(str(i), f"📚 {f}", f"[{color}]{c}[/]", status, updated_display)
                
            console.print(table)
        return files

    def create_file(self):
        name = _safe_input("📝 Tên bộ đề mới (không cần .csv): ")
        if not name: return
        
        p = self._get_full_path(f"{name}.csv")
        if os.path.exists(p):
            return console.print("[yellow]⚠️ File đã tồn tại![/]")
            
        try:
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(["id", "answer", "question", "hint", "desc"])
            log_action("CREATE", p)
            console.print(f"[green]🆕 Đã tạo thành công: {name}.csv[/]"); time.sleep(1)
        except Exception as e:
            _handle_error(f"❌ Lỗi hệ thống không thể tạo file '{name}.csv': {e}")

    def delete_file(self, path):
        confirm = _safe_input(f"❗ Xác nhận xoá vĩnh viễn {os.path.basename(path)}? (y/n) ")
        if confirm != "y": return
        
        try:
            os.remove(path)
            self._cache.pop(os.path.basename(path), None)
            log_action("DELETE", path)
            console.print("[red]🗑️ Đã xoá file thành công.[/]"); time.sleep(1)
        except Exception as e:
            _handle_error(f"❌ Không thể xoá file '{os.path.basename(path)}': {e}")

    def rename_file(self, path):
        new = _safe_input("🏷️ Tên mới: ")
        if not new: return
        
        new_path = self._get_full_path(f"{new}.csv")
        try:
            os.rename(path, new_path)
            self._cache.clear() # Xoá cache để cập nhật thông tin mới
            log_action("RENAME", f"{path}->{new_path}")
            console.print("[green]🏷️ Đã đổi tên bộ đề thành công.[/]"); time.sleep(1)
        except Exception as e:
            _handle_error(f"❌ Không thể đổi tên thành '{new}.csv': {e}")