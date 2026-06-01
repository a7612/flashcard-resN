# ==============================================================================
#                                SYSTEM PATHS
# ==============================================================================
QUESTIONS_DIR = "data/questions"
LOG_DIR = "logs"
EXPORT_DIR = "exports"
TRASH_DIR = "trash"

# ==============================================================================
#                               INTERFACE SETTINGS
# ==============================================================================
CLEAR_SCREEN = True
ERROR_DELAY = 3                      # Giây tạm dừng để đọc thông báo lỗi
SHOW_STATS = True # Bật/Tắt bảng Thống kê ở Menu
SHOW_HISTORY = True # Bật/Tắt bảng Lịch sử ở Menu
MENU_MODE = 'numeric' # Chế độ hiển thị menu: "numeric" (phím số) hoặc "command" (lệnh /)
MAX_FILENAME_LENGTH = 100 # Giới hạn độ dài tên bộ đề (ký tự)

# ==============================================================================
#                              UI THEME COLORS
# ==============================================================================
COLOR_HEADER  = "bright_blue"
COLOR_MENU    = "magenta"
COLOR_STATS   = "cyan"
COLOR_HISTORY = "yellow"
COLOR_ERROR   = "red"
COLOR_SUCCESS = "green"
COLOR_WARNING = "yellow"
COLOR_INFO    = "cyan"

# ==============================================================================
#                             DATA PROCESSING & SORTING
# ==============================================================================

# --- Trùng lặp câu hỏi ---
# 0: Theo ID (row[0]) - Khuyến nghị
# 2: Theo Nội dung câu hỏi (row[2])
DEDUPLICATE_COLUMN_INDEX = 2 

# --- Giới hạn tần suất Keyword ---
MAX_SAME_KEYWORD_PER_QUIZ = 5 # Số câu hỏi tối đa có cùng keyword trong một lượt chơi

# --- Cấu hình nhận diện câu hỏi nhập liệu (Fill-in-the-blank) ---
KEYWORD_BOOL = ["đúng hay sai"] # Keywords cho dạng câu hỏi [Đúng/Sai]
KEYWORD_Q_INPUT = ["stand for", "tên đầy đủ", "viết tắt của"] # Keywords cho dạng nhập liệu trực tiếp

# --- Cấu hình So khớp mờ (Fuzzy Matching) ---
FUZZY_MATCHING_ENABLED = True # Bật/Tắt tính năng chấp nhận đáp án gần đúng
FUZZY_MATCHING_THRESHOLD = 0.9 # Tỉ lệ tương đồng (0.9 tương đương sai lệch ~1-2 ký tự trong chuỗi dài)

# --- Sắp xếp File nội bộ (Dùng cho logic nạp dữ liệu) ---
# 'name_asc', 'name_desc'
FILE_SORT_BY = "name_asc"

# --- Sắp xếp hiển thị trên bảng "KHO DỮ LIỆU HỆ THỐNG" ---
# 'count_desc', 'count_asc', 'name_asc', 'name_desc', 'mtime_desc', 'mtime_asc'
FILE_DISPLAY_SORT_BY = 'name_asc' 

# --- Sắp xếp nội dung câu hỏi trong phần Biên tập ---
# 'id_asc', 'id_desc', 'answer_asc', 'answer_desc', 'question_asc', 'question_desc'
# 'hint_asc', 'hint_desc', 'desc_asc', 'desc_desc'
QUESTION_SORT_BY = 'question_asc' 
