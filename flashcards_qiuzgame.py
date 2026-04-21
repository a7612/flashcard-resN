#!/usr/bin/env python3
from src.process_menu import MenuManager
from src.core import console

if __name__ == "__main__":
    try:
        manager = MenuManager()
        manager.run_menu("🎮 HỆ THỐNG HỌC TẬP FLASHCARD", {
            "/train": (lambda: manager.play_action(), "🚀 Luyện tập"),
            "/play": (lambda: manager.play_action(all_files=True), "🌍 Thử thách"),
            "/manage": (lambda: manager.manage_q_menu(), "📦 Quản lý nội dung"),
            "/file": (lambda: manager.manage_f_menu(), "🗂️ Quản lý kho lưu"),
            "/clear_history": (lambda: manager.clear_history(), "🧹 Xoá lịch sử"),
            "/clear_log": (lambda: manager.clear_logs(), "📝 Dọn sạch nhật ký"),
            "/clear_trash": (lambda: manager.empty_trash(), "🗑️ Dọn sạch thùng rác"),
            "/exit": (lambda: console.print("[bold red]👋 Chào tạm biệt![/]"), "Thoát chương trình")
        })
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Đã dừng ứng dụng.[/]")