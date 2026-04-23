#!/usr/bin/env python3
from src.process_menu import MenuManager
from src.core import console, _clear_screen

if __name__ == "__main__":
    try:
        manager = MenuManager()
        manager.run_menu("🎮 HỆ THỐNG HỌC TẬP FLASHCARD", {
            "/train": (lambda: manager.play_action(), "🚀 Luyện tập"),
            "/play": (lambda: manager.play_action(all_files=True), f"🌍 Thử thách\n{"[red]="*22}"),
            "/manage": (lambda: manager.manage_q_menu(), "📦 Quản lý hệ thống"),
            "/settings": (lambda: manager.settings_menu(), f"⚙️ Cài đặt\n{"[red]="*22}"),
            "/clear_history": (lambda: manager.clear_history(), "🧹 Xoá lịch sử"),
            "/clear_log": (lambda: manager.clear_logs(), "📝 Dọn sạch nhật ký"),
            "/clear_trash": (lambda: manager.empty_trash(), f"🗑️ Dọn sạch thùng rác\n{"[red]="*22}"),
            "/exit": (lambda: None, "Thoát chương trình")
        })
        _clear_screen()
        console.print("[bold red]👋 Chào tạm biệt![/]")
    except KeyboardInterrupt:
        _clear_screen()
        console.print("[bold yellow]⚠️ Đã dừng ứng dụng.[/]")