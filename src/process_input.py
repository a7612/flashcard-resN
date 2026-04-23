from src.utils import _safe_input
from src.core import console

def input_deck_name():
    return _safe_input("📝 Tên bộ đề mới (hoặc /exit): ")

def input_keyword(old_v=""):
    return _safe_input(f"🔑 Từ khóa{f' ({old_v})' if old_v else ''}: ")

def input_rename_deck():
    return _safe_input("🏷️ Tên mới (hoặc /exit): ")

def confirm_delete(target_name, is_all=False):
    msg = f"🔥 CẢNH BÁO: Bạn có chắc muốn xoá vĩnh viễn TOÀN BỘ {target_name}? (y/n) " if is_all \
          else f"❗ Xác nhận xoá vĩnh viễn {target_name}? (y/n) "
    return _safe_input(msg)

def input_question_details(old_q="", old_a="", old_d="", old_r="", is_edit=False):
    """Xử lý nhập 4 thông tin cơ bản của một câu hỏi."""
    prefix = "✏️ " if is_edit else "❓ "
    q = _safe_input(f"{prefix}Câu hỏi{f' ({old_q})' if old_q else ''}: ")
    if q is None: return None, None, None, None
    
    a = _safe_input(f"✅ Đáp án chuẩn{f' ({old_a})' if old_a else ''}: ")
    if a is None: return q, None, None, None
    
    d = _safe_input(f"💡 Gợi ý{f' ({old_d})' if old_d else ''} (Enter để bỏ qua): ")
    if d is None: return q, a, None, None
    
    r = _safe_input(f"📖 Mô tả thêm{f' ({old_r})' if old_r else ''} (Enter để bỏ qua): ")
    return q, a, d, r

def input_selection(prompt, max_val=None, allow_all=False):
    """Hàm dùng chung để chọn STT (Index) từ danh sách."""
    def validator(x):
        if allow_all and x.lower() == "/all": return True, "/all"
        if x.isdigit() and 1 <= int(x) <= (max_val if max_val else 9999):
            return True, int(x) - 1
        return False, x
    return _safe_input(prompt, validator)

def input_quiz_choice(mapping):
    """Nhập đáp án A, B, C trong khi chơi Quiz."""
    while True:
        try:
            u = console.input(f"\n👉 Đáp án: ").strip().upper()
            if u in ['/EXIT', 'EXIT']: return "EXIT_SIGNAL"
            if u == '?': return "HINT_SIGNAL"
            if u in mapping: return u
            console.print("[red]❌ Sai cú pháp![/]")
        except (EOFError, KeyboardInterrupt): return "EXIT_SIGNAL"

def input_difficulty_rating():
    """Nhập đánh giá độ khó sau mỗi câu hỏi."""
    try:
        prompt = "[bold yellow]⭐ Hãy đánh giá độ khó (1-5, hoặc Enter bỏ qua): [/]"
        val = console.input(prompt).strip()
        return int(val) if val.isdigit() and 1 <= int(val) <= 5 else None
    except: return None

def input_menu_choice():
    """Nhập lệnh từ Menu chính."""
    try:
        return console.input(f"\n👉 Lệnh của bạn: ").strip().lower()
    except: return "exit"

def input_difficulty_custom():
    """Nhập thông số tùy chỉnh cho Quiz."""
    qs = int(_safe_input("📝 Số lượng câu hỏi: ") or 10)
    opts = int(_safe_input("🔢 Số lượng đáp án hiển thị: ") or 4)
    return opts, qs

def input_confirm_generic(msg):
    return _safe_input(msg)

def input_difficulty_mode():
    try:
        val = console.input(f"\n👉 Lựa chọn của bạn: ")
        return int(val) if val.isdigit() else 1
    except: return 1

def input_setting_delay():
    """Nhập thời gian tạm dừng mới."""
    return _safe_input("⏳ Nhập thời gian tạm dừng mới (giây, hiện tại mặc định là 3): ")

def input_setting_dedup():
    """Nhập lựa chọn cột để loại bỏ trùng lặp."""
    return _safe_input("🔍 Chọn cột để kiểm tra trùng lặp (0: Theo ID, 2: Theo Nội dung câu hỏi): ")

def input_search_file():
    """Nhập từ khóa tìm kiếm tên file."""
    return _safe_input("🔍 Nhập từ khóa tìm kiếm (Tên bộ đề): ")