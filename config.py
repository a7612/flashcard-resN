QUESTIONS_DIR = "questions"
LOG_DIR = "logs"
EXPORT_DIR = "exports"
CLEAR_SCREEN = True
DEBUG = False

MAX_GENERATE_NORMAL_QUESTIONS = 20   # số câu hỏi khi chơi 1 file
MAX_GENERATE_ALL_QUESTIONS = 15      # số câu hỏi khi chơi tất cả
MAX_GENERATE_NORMAL_ANSWERS = 1   # số đáp án khi chơi 1 file
MAX_GENERATE_ALL_ANSWERS = 4     # số đáp án khi chơi all

KEYWORD = [
    # Tổng quan
    "định nghĩa",
    # chính
    "chức năng chính", "có tác dụng gì", "điều gì", "để làm gì", "như thế nào",
    # tên
    "tên đầy đủ", "tên gọi là gì", "được gọi là gì",
    # sao
    "vì sao", "tại sao",        
    # Ai
    "ai là tác giả của câu nói này?", "đâu là nhân vật",
    # Thời gian, số
    "chính xác là bao nhiêu", "có bao nhiêu", "khoảng bao nhiêu", "được phát triển", "giai đoạn nào", "ngày, tháng nào",
    # Lệnh và thư mục
    "lệnh nào", "viết câu lệnh đó như thế nào", "tùy chọn nào", "thư mục nào",
    # Giao thức
    "giao thức nào", "giao thức đưa gói tin nào",
    # Thiết bị
    "thiết bị nào",
    
    "kỹ thuật nào", "thuật ngữ nào", "quy trình nào", "tầng nào", "phân loại nào", "dạng nào", "mục tiêu nào", "lớp nào", "cờ nào", "cáp nào",   
    "translate to english",
]


# KEYWORD.sort()
# print(KEYWORD)


KEYWORD_BOOL = ["đúng hay sai"]

# ====== ANSI COLORS ======
RESET   = "\033[0m"   # reset về mặc định
BLACK   = "\033[30m"
RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
BLUE    = "\033[34m"
MAGENTA = "\033[35m"
CYAN    = "\033[36m"   
WHITE   = "\033[37m"
BRIGHT_BLACK   = "\033[90m"
BRIGHT_RED     = "\033[91m"
BRIGHT_GREEN   = "\033[92m"
BRIGHT_YELLOW  = "\033[93m"
BRIGHT_BLUE    = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN    = "\033[96m"
BRIGHT_WHITE   = "\033[97m"
BG_RED     = "\033[41m"
BG_GREEN   = "\033[42m"
BG_YELLOW  = "\033[43m"
BG_BLUE    = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN    = "\033[46m"
BG_WHITE   = "\033[47m"