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
    # N
    # "mô hình",
    # Q
    "là gì"
    # = Đâu
    "ở đâu", "kết nối đến đâu",
    # = Nào
    "loại nào", "tầng nào", "thiết bị nào", "cổng nào", "lớp nào", "mô hình mạng nào", "thành phần nào", "cáp nào",
    "ở điểm nào", "thông tin nào",  "hướng nào", "phạm vi nào", "yếu tố nào", 
    # = Gì
    "bao gồm gì", "vai trò gì", "gọi là gì", "làm gì", "chức năng chính là gì", 
    "chức năng gì", "tác dụng gì", "ngăn gì", "điều gì", "trách nhiệm gì", "kết nối gì",
    "giúp ích gì", "nhiệm vụ gì",
    # = other
    "điểm khác biệt", "lợi ích", "chia thành mấy", "tô-pô nào", "bao nhiêu",
]
KEYWORD_BOOL = ["đúng hay sai", "dung"]

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