QUESTIONS_DIR = "questions"
LOG_DIR = "logs"
EXPORT_DIR = "exports"
CLEAR_SCREEN = True
DEBUG = False
ERROR_DELAY = 3                      # Giây tạm dừng để đọc thông báo lỗi

# ====== UI THEME COLORS (Rich Styles) ======
COLOR_HEADER  = "bright_blue"
COLOR_MENU    = "magenta"
COLOR_STATS   = "cyan"
COLOR_HISTORY = "yellow"
COLOR_ERROR   = "red"
COLOR_SUCCESS = "green"
COLOR_WARNING = "yellow"
COLOR_INFO    = "cyan"

MAX_GENERATE_NORMAL_QUESTIONS = 20   # số câu hỏi khi chơi 1 file
MAX_GENERATE_ALL_QUESTIONS = 15      # số câu hỏi khi chơi tất cả
MAX_GENERATE_NORMAL_ANSWERS = 1   # số đáp án khi chơi 1 file
MAX_GENERATE_ALL_ANSWERS = 4     # số đáp án khi chơi all

KEYWORD = [
    # số lượng
    "bao nhiêu",

    # gì
    "có tác dụng gì",
    # nào
    "lớp nào", "giai đoạn nào",
]

# KEYWORD.sort()
# print(KEYWORD)


KEYWORD_BOOL = ["đúng hay sai"]