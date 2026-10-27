import json, os
from src.process_menu import MenuManager
from src.core import console, _clear_screen, _CONFIG, time

SETTINGS_FILE = "settings.json"

def load_settings():
    """Load settings từ file JSON, nếu không có thì trả về rỗng hoặc settings mặc định"""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_setting(key, value):
    """Cập nhật giá trị cấu hình vào file JSON"""
    if not os.path.exists(SETTINGS_FILE):
        settings = {}
    else:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            try:
                settings = json.load(f)
            except Exception:
                settings = {}
    settings[key] = value
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

if __name__ == "__main__":
    try:
        manager = MenuManager()
        is_num = _CONFIG.MENU_MODE == "numeric"
        manager.run_menu("🎮 HỆ THỐNG HỌC TẬP FLASHCARD", {
            ("1" if is_num else "/train"): (lambda: manager.play_action(), "[green]Thử thách: Luyện tập[/]"),
            ("2" if is_num else "/play"): (lambda: manager.play_action(all_files=True), f"[green]Thử thách: Quiz[/]"),
            ("3" if is_num else "/mistakes"): (lambda: manager.show_mistake_stats(), "[cyan]Kiểm tra lỗi sai[/]"),
            ("4" if is_num else "/manage"): (lambda: manager.manage_q_menu(), "[yellow]Quản lý hệ thống[/]"),
            ("5" if is_num else "/settings"): (lambda: manager.settings_menu(), f"[yellow]Cài đặt[/]"),
            ("6" if is_num else "/clear_history"): (lambda: manager.clear_history(), "[red]Xóa sạch lịch sử[/]"),
            ("7" if is_num else "/clear_log"): (lambda: manager.clear_logs(), "[red]Xóa sạch log[/]"),
            ("8" if is_num else "/clear_trash"): (lambda: manager.empty_trash(), f"[red]Xóa sạch thùng rác[/]"),
            ("0" if is_num else "/exit"): (lambda: None, "Thoát chương trình")
        })
        _clear_screen()
        console.print("[bold red]👋 Chào tạm biệt![/]")
    except (KeyboardInterrupt, EOFError):
        _clear_screen()
        console.print("[bold yellow]⚠️ Đã nhận tín hiệu dừng (Ctrl+C). Đang dọn dẹp hệ thống...[/]")
        # Delay nhỏ để logger kịp flush buffer thông qua atexit
        time.sleep(0.5)
        console.print("[bold green]✅ Đã thoát an toàn.[/]")