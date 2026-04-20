import os, datetime, time, csv
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich import box
from src.core import _CONFIG, console, VN_TZ, _get_now, _clear_screen, _handle_error, _move_to_trash, _safe_input
from src.process_log import log_action, LogManager

def _replace_colors(text):
    if not text: return ""
    if isinstance(text, (tuple, list)):
        text = text[1] if len(text) > 1 else text[0]
    
    # Xử lý các ký tự đặc biệt
    t = str(text).replace("\\n", "\n").replace("\\t", "\t").replace("{BACKSLASH}", "\\")
    
    # Nếu chuỗi đã được bọc màu rồi thì không bọc thêm [white] nữa để tránh chồng chéo tag
    if t.startswith("[") and t.endswith("[/]") and "[/][" in t:
        return t
    return f"[white]{t.replace('[/]', '[/][white]')}[/]"

# --- TIỆN ÍCH LOGIC MENU ---

def _show_stats_util(file_mgr):
    try:
        files = file_mgr.get_files()
        total_q, total_bytes = 0, 0
        for f in files:
            total_q += file_mgr.count_questions(f)
            full_path = os.path.join(file_mgr.qdir, f)
            if os.path.exists(full_path): total_bytes += os.path.getsize(full_path)
    except: total_q, total_bytes, files = 0, 0, []
    size_str = f"{total_bytes/1024:.1f} KB" if total_bytes > 1024 else f"{total_bytes} B"
    table = Table(box=box.ROUNDED, show_header=False, min_width=28, border_style=_CONFIG.COLOR_STATS) 
    table.add_row("📂 Bộ đề", str(len(files))); table.add_row("❓ Tổng câu", f"[bold green]{total_q}[/]"); table.add_row("💾 Lưu trữ", f"[bold magenta]{size_str}[/]")
    return Panel(table, title=f"[bold {_CONFIG.COLOR_STATS}]📊 THỐNG KÊ[/]", border_style=_CONFIG.COLOR_STATS, expand=False)

def _get_history_table_util():
    table = Table(box=box.ROUNDED, border_style=_CONFIG.COLOR_HISTORY)
    table.add_column("Thời gian", style="dim", width=11); table.add_column("Điểm", justify="center"); table.add_column("%", justify="right", style="bold yellow")
    history_pcts = []
    h_files = sorted([f for f in os.listdir(_CONFIG.EXPORT_DIR) if f.startswith("quiz_results_")], reverse=True)[:10]
    for f_name in h_files:
        try:
            with open(os.path.join(_CONFIG.EXPORT_DIR, f_name), encoding="utf-8-sig") as f:
                meta = {r[0]: r[1] for r in csv.reader(f) if len(r) >= 2}
                pct = float(meta.get('percent', 0)); history_pcts.append(pct)
                dt = datetime.datetime.fromisoformat(meta["timestamp"]).strftime("%d/%m %H:%M")
                table.add_row(dt, f"{meta.get('score', 0)}/{meta.get('total', 0)}", f"{pct:.0f}%")
        except: pass
    if history_pcts:
        avg = sum(history_pcts)/len(history_pcts)
        color = "bold green" if avg > 80 else "bold red" if avg < 50 else "bold yellow"
        table.caption = f"[bold white]🎯 Độ chính xác TB: [{color}]{avg:.1f}%[/{color}][/]"
    return Panel(table, title=f"[bold {_CONFIG.COLOR_HISTORY}]📜 LỊCH SỬ[/]", border_style=_CONFIG.COLOR_HISTORY, expand=False)

def _choose_file_path_util(file_mgr, allow_all=False):
    files = file_mgr.list_files(show=True)
    if not files:
        console.print("[yellow]⚠️ Thư mục hiện đang trống.[/]"); time.sleep(1); return None
    prompt = f"👉 Nhập ID bộ đề {'hoặc /all ' if allow_all else ''}(hoặc /exit): "
    validator = lambda x: ((x.isdigit() and 1 <= int(x) <= len(files)) or (allow_all and x.lower() == "/all"), 
                          os.path.join(file_mgr.qdir, files[int(x)-1]) if x.isdigit() else x.lower())
    return _safe_input(prompt, validator)

def _play_action_util(file_mgr, card_mgr, menu_mgr, all_files=False):
    from src.engine import QuizGame
    game = QuizGame()
    try:
        data = []
        if all_files:
            for f in file_mgr.get_files(): data.extend(card_mgr.load_data(os.path.join(file_mgr.qdir, f)))
        else:
            path = _choose_file_path_util(file_mgr)
            if path: data = card_mgr.load_data(path)
        if data: game.run(data, *game.get_difficulty())
    except Exception as e: _handle_error(f"❌ Lỗi khi khởi tạo trò chơi: {e}")

def _check_all_integrity_util(file_mgr, card_mgr):
    _clear_screen()
    console.print(Panel(Align.center("[bold cyan]🔍 KIỂM TRA TOÀN DIỆN HỆ THỐNG[/]"), border_style="cyan"))
    files = file_mgr.get_files()
    if not files: return console.print("[yellow]⚠️ Không có file để kiểm tra.[/]")
    table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
    table.add_column("Bộ đề", style="bold white", width=30); table.add_column("Kết quả kiểm tra", justify="left")
    
    with console.status("[bold green]Đang quét dữ liệu...[/]"):
        for f_name in files:
            path = os.path.join(file_mgr.qdir, f_name)
            errors = card_mgr.validate_file(path)
            table.add_row(f_name, "\n".join([f"• {e}" for e in errors]) if errors else "[green]✅ Sạch sẽ[/]")
    console.print(table)
    console.input(f"\n[cyan]Nhấn Enter để quay lại...[/]")

def _clear_history_util():
    files = [f for f in os.listdir(_CONFIG.EXPORT_DIR) if f.startswith("quiz_results_")]
    if not files: return console.print("[yellow]⚠️ Lịch sử hiện đang trống.[/]")
    if console.input(f"\n[bold red]⚠️ Xoá {len(files)} lịch sử? (y/n): [/]").strip().lower() == 'y':
        count = sum(1 for f in files if _move_to_trash(os.path.join(_CONFIG.EXPORT_DIR, f)))
        log_action("CLEAR_HISTORY", f"Removed {count} files"); time.sleep(1.5)

def _empty_trash_util():
    files = [f for f in os.listdir(_CONFIG.TRASH_DIR) if os.path.isfile(os.path.join(_CONFIG.TRASH_DIR, f))]
    if not files: return console.print("[yellow]⚠️ Thùng rác hiện đang trống.[/]")
    if console.input(f"\n[bold red]🔥 Xoá VĨNH VIỄN {len(files)} file? (y/n): [/]").strip().lower() == 'y':
        for f in files: os.remove(os.path.join(_CONFIG.TRASH_DIR, f))
        log_action("EMPTY_TRASH", f"Cleaned {len(files)} files"); time.sleep(1.5)

def _handle_manage_questions_for_path_util(file_mgr, card_mgr, menu_mgr):
    path = _choose_file_path_util(file_mgr)
    if path:
        card_mgr.show_questions(path)
        menu_mgr._run_question_crud_menu(path)

def _clear_logs_util():
    """Tiện ích gọi lệnh dọn dẹp nhật ký từ LogManager."""
    LogManager.clear_logs()

def _handle_file_deletion_util(file_mgr):
    p = _choose_file_path_util(file_mgr, allow_all=True)
    if p == "/all": file_mgr.delete_all_files()
    elif p: file_mgr.delete_file(p)