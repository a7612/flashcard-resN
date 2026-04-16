QUESTIONS_DIR = "questions"
LOG_DIR = "logs"
EXPORT_DIR = "exports"
TRASH_DIR = "trash"
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
MAX_GENERATE_NORMAL_ANSWERS = 4   # số đáp án khi chơi 1 file (Cần ít nhất 4 để thấy sự khác biệt)
MAX_GENERATE_ALL_ANSWERS = 4     # số đáp án khi chơi all

KEYWORD = [
    # english
    "english - translate", "english - fill in the blanks",

    # other
    "mục đích chính",
]

# KEYWORD.sort()
# print(KEYWORD)


KEYWORD_BOOL = ["đúng hay sai"]