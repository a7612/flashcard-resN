import os, logging, getpass, datetime, re, time
from logging.handlers import TimedRotatingFileHandler
from types import SimpleNamespace
from rich.console import Console
from config import *

# Khởi tạo cấu hình và thư mục
_CONFIG = SimpleNamespace(**{k: v for k, v in globals().items() if k.isupper()})
for d in [_CONFIG.LOG_DIR, _CONFIG.EXPORT_DIR, _CONFIG.QUESTIONS_DIR]: os.makedirs(d, exist_ok=True)

# Thiết lập Logger
logger = logging.getLogger("flashcard"); logger.setLevel(logging.INFO)
if not logger.handlers:
    h = TimedRotatingFileHandler(os.path.join(_CONFIG.LOG_DIR, "flashcard.log"), when="midnight", backupCount=14, encoding="utf-8")
    h.setFormatter(logging.Formatter('%(asctime)s | %(message)s')); logger.addHandler(h)

log_action = lambda a, d="": logger.info(f"{getpass.getuser():<12} | {a:<20} | {d}")
console = Console(highlight=False)

# --- UTILITIES ---
def _clear_screen(): 
    if _CONFIG.CLEAR_SCREEN:
        os.system("cls" if os.name == "nt" else "clear")

def _handle_error(msg, delay=None):
    """In thông báo lỗi theo theme và tạm dừng hệ thống."""
    console.print(msg, style=_CONFIG.COLOR_ERROR)
    time.sleep(delay if delay is not None else _CONFIG.ERROR_DELAY)

def _get_now():
    """Trả về thời gian hiện tại theo múi giờ GMT+7."""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))

def _replace_colors(text):
    if not text: return ""
    if isinstance(text, (tuple, list)):
        text = text[1] if len(text) > 1 else text[0]
    # Chuyển đổi các ký tự điều khiển
    t = str(text).replace("\\n", "\n").replace("\\t", "\t").replace("{BACKSLASH}", "\\")
    # Thủ thuật KISS: Để 1 dấu [/] reset toàn bộ màu phía sau mà không gây crash:
    # Ta thay [/] bằng [/][white] và bọc toàn bộ chuỗi trong thẻ [white]...[/]
    return f"[white]{t.replace('[/]', '[/][white]')}[/]"

def _safe_input(prompt, validator=None, allow_exit=True):
    while True:
        try: v = console.input(prompt).strip()
        except (KeyboardInterrupt, EOFError): return None
        if allow_exit and (v.lower() == "/exit"): return None
        if validator:
            ok, val = validator(v)
            if ok: return val
            console.print(f"[{_CONFIG.COLOR_ERROR}]⛔ Giá trị không hợp lệ![/]")
        else: return v