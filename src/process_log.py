import os, logging, getpass, atexit, time, csv
from src.core import _CONFIG, console, _get_now, _move_to_trash
import src.process_input as inp

# --- CẤU HÌNH LOGGER ---
logger = logging.getLogger("flashcard")
logger.setLevel(logging.INFO)

_today = _get_now().strftime("%Y-%m-%d")
_temp_log_path = os.path.join(_CONFIG.LOG_DIR, f"log-{_today}-temp.log")
_final_log_path = os.path.join(_CONFIG.LOG_DIR, f"log-{_today}.log")

def _finalize_logs():
    """Chuyển nội dung từ file temp sang file log chính thức khi thoát."""
    try:
        # Đóng tất cả handlers để giải phóng file
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
            
        if os.path.exists(_temp_log_path):
            with open(_temp_log_path, "r", encoding="utf-8") as src:
                content = src.read()
            if content:
                with open(_final_log_path, "a", encoding="utf-8") as dst:
                    dst.write(content)
            os.remove(_temp_log_path)
    except: pass

if not logger.handlers:
    h = logging.FileHandler(_temp_log_path, encoding="utf-8")
    h.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
    logger.addHandler(h)
    atexit.register(_finalize_logs)

# Hàm ghi log tiện ích
def log_action(action, details=""):
    user = getpass.getuser()
    logger.info(f"{user:<12} | {action:<20} | {details}")

def log_difficulty(qid, rating):
    """Ghi nhận đánh giá độ khó của người dùng vào file CSV tập trung."""
    try:
        diff_dir = "data"
        diff_file = os.path.join(diff_dir, "difficult.csv")
        os.makedirs(diff_dir, exist_ok=True)
        file_exists = os.path.isfile(diff_file)
        with open(diff_file, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=';')
            if not file_exists:
                writer.writerow(["id", "độ khó"])
            writer.writerow([qid, rating])
    except: pass

class LogManager:
    @staticmethod
    def clear_logs():
        """Xoá toàn bộ file nhật ký cũ (trừ file temp đang dùng)."""
        try:
            log_dir = _CONFIG.LOG_DIR
            files = [f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
            if not files:
                console.print("[yellow]⚠️ Không có nhật ký để xoá.[/]")
                return

            confirm = inp.input_confirm_generic(f"\n[bold red]⚠️ Bạn có chắc muốn dọn sạch nhật ký cũ? (y/n): [/]")
            if confirm == 'y':
                count = 0
                for f in files:
                    if f.endswith("-temp.log"): continue
                    fpath = os.path.join(log_dir, f)
                    try:
                        os.rename(fpath, fpath) # Kiểm tra file có bận không
                        if _move_to_trash(fpath): count += 1
                    except OSError: continue

                console.print(f"[bold green]✅ Đã dọn dẹp {count} file nhật ký cũ![/]")
                log_action("CLEAR_LOGS", f"Cleaned {count} files")
                time.sleep(1.5)
        except Exception as e:
            console.print(f"[red]❌ Lỗi khi dọn dẹp nhật ký: {e}[/]")