#!/usr/bin/env python3
from src.process_menu import MenuManager
from src.core import console, _clear_screen, _CONFIG

if __name__ == "__main__":
    try:
        manager = MenuManager()
        is_num = _CONFIG.MENU_MODE == "numeric"
        manager.run_menu("🎮 HỆ THỐNG HỌC TẬP FLASHCARD", {
            ("1" if is_num else "/train"): (lambda: manager.play_action(), "🚀 Luyện tập"),
            ("2" if is_num else "/play"): (lambda: manager.play_action(all_files=True), f"🌍 Thử thách"),
            ("3" if is_num else "/manage"): (lambda: manager.manage_q_menu(), "📦 Quản lý hệ thống"),
            ("4" if is_num else "/settings"): (lambda: manager.settings_menu(), f"⚙️ Cài đặt"),
            ("5" if is_num else "/clear_history"): (lambda: manager.clear_history(), "🧹 Xoá lịch sử"),
            ("6" if is_num else "/clear_log"): (lambda: manager.clear_logs(), "📝 Dọn sạch nhật ký"),
            ("7" if is_num else "/clear_trash"): (lambda: manager.empty_trash(), f"🗑️ Dọn sạch thùng rác"),
            ("0" if is_num else "/exit"): (lambda: None, "Thoát chương trình")
        })
        _clear_screen()
        console.print("[bold red]👋 Chào tạm biệt![/]")
    except KeyboardInterrupt:
        _clear_screen()
        console.print("[bold yellow]⚠️ Đã dừng ứng dụng.[/]")