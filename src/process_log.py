import os, logging, getpass, atexit, time, csv
from src.core import _CONFIG, console, _get_now, _move_to_trash
import src.process_input as inp

# --- CẤU HÌNH LOGGER ---
logger = logging.getLogger("flashcard")
logger.setLevel(logging.INFO)

_today = _get_now().strftime("%Y-%m-%d")
_temp_log_path = os.path.join(_CONFIG.LOG_DIR, f"log-{_today}-temp.log")
_final_log_path = os.path.join(_CONFIG.LOG_DIR, f"log-{_today}.log")

def _merge_log_file(temp_path):
    """Gộp nội dung từ file temp vào file log chính tương ứng."""
    try:
        if os.path.exists(temp_path):
            final_path = temp_path.replace("-temp.log", ".log")
            with open(temp_path, "r", encoding="utf-8") as src:
                content = src.read()
            if content:
                with open(final_path, "a", encoding="utf-8") as dst:
                    dst.write(content)
            os.remove(temp_path)
            return True
    except: pass
    return False

def _recover_orphaned_logs():
    """Quét và phục hồi các file log tạm bị bỏ rơi từ các phiên trước."""
    try:
        if not os.path.exists(_CONFIG.LOG_DIR): return
        for f in os.listdir(_CONFIG.LOG_DIR):
            fpath = os.path.join(_CONFIG.LOG_DIR, f)
            # Chỉ gộp các file temp không phải của phiên hiện tại
            if f.endswith("-temp.log") and fpath != os.path.abspath(_temp_log_path):
                _merge_log_file(fpath)
    except: pass

def _finalize_logs():
    """Dọn dẹp handler và gộp log phiên hiện tại khi thoát."""
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    _merge_log_file(_temp_log_path)

# Khôi phục log cũ ngay khi import module
_recover_orphaned_logs()

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
        """Xoá toàn bộ file nhật ký (bao gồm cả các file tạm)."""
        try:
            log_dir = _CONFIG.LOG_DIR
            files = [f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
            if not files:
                console.print("[yellow]⚠️ Không có nhật ký để xoá.[/]")
                return

            confirm = inp.input_confirm_generic(f"\n[bold red]⚠️ Bạn có chắc muốn dọn sạch toàn bộ nhật ký? (y/n): [/]")
            if confirm == 'y':
                count = 0
                for f in files:
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