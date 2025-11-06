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
    # ai
    "cho ai", "là ai", "ai là",
    # chính
    "mục tiêu chính",
    # đâu
    "ở đâu", "đến đâu",
    # gì
    "bằng gì", "điều gì", "làm gì", "nhiệm vụ gì", "là gì", "tác dụng gì", "bao gồm gì", "trách nhiệm gì", "kết nối gì", "chức năng gì", "vai trò gì", "mục đích gì", "việc gì", "đặc điểm gì?", "gọi là gì",
    # nào
    "nguyên nhân nào", "thiết bị nào", "tầng nào", "giao thức nào", "yếu tố nào", "cổng nào", "thiết bị nào", "thông tin nào", "như thế nào", "phạm vi nào", "bằng cách nào", "hướng nào", "lớp nào", "dấu hiệu nào", "công nghệ nền nào", "hiện tượng nào", "cáp nào", "điểm nào", "hoạt động nào", "tấn công nào", "giai đoạn nào", "công cụ nào", "kỹ thuật nào", "bảng nào", "vai trò nào", "thành phần nào", "quy tắc nào", "tư duy nào",
    # other
    "mặc định", "thiết bị", "tại sao", "mấy lớp", "mấy tầng", "bao nhiêu",
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