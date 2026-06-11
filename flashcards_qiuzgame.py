#!/usr/bin/env python3
from src.process_menu import MenuManager
from src.core import console, _clear_screen, _CONFIG, time

if __name__ == "__main__":
    try:
        manager = MenuManager()
        is_num = _CONFIG.MENU_MODE == "numeric"
        manager.run_menu("🎮 HỆ THỐNG HỌC TẬP FLASHCARD", {
            ("1" if is_num else "/train"): (lambda: manager.play_action(), "🚀 Thử thách: Luyện tập"),
            ("2" if is_num else "/play"): (lambda: manager.play_action(all_files=True), f"🌍 Thử thách: Quiz\n"),
            ("3" if is_num else "/mistakes"): (lambda: manager.show_mistake_stats(), "❌ Kiểm tra lỗi sai\n"),
            ("4" if is_num else "/manage"): (lambda: manager.manage_q_menu(), "📦 Quản lý hệ thống"),
            ("5" if is_num else "/settings"): (lambda: manager.settings_menu(), f"⚙️ Cài đặt\n"),
            ("6" if is_num else "/clear_history"): (lambda: manager.clear_history(), "🧹 Xóa sạch lịch sử"),
            ("7" if is_num else "/clear_log"): (lambda: manager.clear_logs(), "📝 Xóa sạch log"),
            ("8" if is_num else "/clear_trash"): (lambda: manager.empty_trash(), f"🗑️ Xóa sạch thùng rác\n"),
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