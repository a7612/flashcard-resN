import os, datetime, time, shutil, csv
from types import SimpleNamespace
from rich.console import Console
from config import *

# Khởi tạo cấu hình và thư mục
_CONFIG = SimpleNamespace(**{k: v for k, v in globals().items() if k.isupper()})
for d in [_CONFIG.LOG_DIR, _CONFIG.EXPORT_DIR, _CONFIG.QUESTIONS_DIR, _CONFIG.TRASH_DIR, "data"]: os.makedirs(d, exist_ok=True)

console = Console(highlight=False)

# Định nghĩa múi giờ GMT+7 dùng chung cho toàn hệ thống
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))

def _get_now():
    return datetime.datetime.now(VN_TZ)

def _clear_screen(): 
    if _CONFIG.CLEAR_SCREEN:
        os.system("cls" if os.name == "nt" else "clear")

def _handle_error(msg, delay=None):
    console.print(msg, style=_CONFIG.COLOR_ERROR)
    time.sleep(delay if delay is not None else _CONFIG.ERROR_DELAY)

def _move_to_trash(path):
    if not os.path.exists(path): return False
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = os.path.basename(path)
        name, ext = os.path.splitext(fname)
        trash_fname = f"{name}_{ts}{ext}"
        shutil.move(path, os.path.join(_CONFIG.TRASH_DIR, trash_fname))
        return True
    except Exception as e:
        console.print(f"[red]❌ Không thể di chuyển vào thùng rác: {e}[/]")
        return False

def _safe_input(prompt, validator=None, allow_exit=True):
    while True:
        try: v = console.input(prompt).strip()
        except (KeyboardInterrupt, EOFError): return None
        if allow_exit and v.lower() in ["exit", "/exit"]: return None
        if validator:
            ok, val = validator(v)
            if ok: return val
            console.print(f"[{_CONFIG.COLOR_ERROR}]⛔ Giá trị không hợp lệ![/]")
        else: return v