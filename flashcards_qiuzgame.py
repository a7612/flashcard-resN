#!/usr/bin/env python3
from src.process_menu import MenuManager
from src.core import console

if __name__ == "__main__":
    try:
        manager = MenuManager()
        manager.run_menu("🎮 HỆ THỐNG HỌC TẬP FLASHCARD", {
            "1": (lambda: manager.play_action(), "🚀 Luyện tập theo bộ"),
            "2": (lambda: manager.play_action(all_files=True), "🌍 Thử thách tổng hợp"),
            "3": (lambda: manager.manage_q_menu(), "📦 Quản lý nội dung"),
            "4": (lambda: manager.manage_f_menu(), "🗂️ Cấu hình kho lưu"),
            "0": (lambda: console.print("[bold red]👋 Chào tạm biệt![/]"), "Exit")
        })
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Đã dừng ứng dụng.[/]")