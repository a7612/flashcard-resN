import os, logging, getpass, datetime, re
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
console = Console()

# --- UTILITIES ---
def _clear_screen(): 
    if _CONFIG.CLEAR_SCREEN:
        os.system("cls" if os.name == "nt" else "clear")

color_map = {f"{{{k}}}": v for k, v in _CONFIG.__dict__.items() if k.isupper() and isinstance(v, str) and v.startswith('\033')}
_color_token_re = re.compile(r"\{[A-Z0-9_]+\}")

def _replace_colors(text):
    if not text: return ""
    text = str(text[1] if isinstance(text, (tuple, list)) and len(text) > 1 else (text[0] if isinstance(text, (tuple, list)) else text))
    return _color_token_re.sub(lambda m: color_map.get(m.group(0), m.group(0)), text.replace("\\n", "\n").replace("\\t", "\t").replace("{BACKSLASH}", "\\"))

def _safe_input(prompt, validator=None, allow_exit=True):
    while True:
        try: v = console.input(prompt).strip()
        except (KeyboardInterrupt, EOFError): return None
        if allow_exit and (v.lower() == "/exit"): return None
        if validator:
            ok, val = validator(v)
            if ok: return val
            console.print("[red]⛔ Giá trị không hợp lệ![/]")
        else: return v