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
    def f_size(b):
        if b >= 1048576: return f"{b/1048576:.1f} MB"
        return f"{b/1024:.1f} KB" if b >= 1024 else f"{b} B"

    try:
        files = file_mgr.get_files()
        total_q, q_size, clean_size = 0, 0, 0
        for f in files:
            count = file_mgr.count_questions(f)
            total_q += count
            full_path = os.path.join(file_mgr.qdir, f)
            if os.path.exists(full_path): q_size += os.path.getsize(full_path)

        log_fs = [f for f in os.listdir(_CONFIG.LOG_DIR) if os.path.isfile(os.path.join(_CONFIG.LOG_DIR, f))]
        log_count = len(log_fs)
        for f in log_fs: clean_size += os.path.getsize(os.path.join(_CONFIG.LOG_DIR, f))

        hist_fs = [f for f in os.listdir(_CONFIG.EXPORT_DIR) if f.startswith("quiz_results_")]
        hist_count = len(hist_fs)
        for f in hist_fs: clean_size += os.path.getsize(os.path.join(_CONFIG.EXPORT_DIR, f))

        trash_fs = [f for f in os.listdir(_CONFIG.TRASH_DIR) if os.path.isfile(os.path.join(_CONFIG.TRASH_DIR, f))]
        trash_count = len(trash_fs)
        for f in trash_fs: clean_size += os.path.getsize(os.path.join(_CONFIG.TRASH_DIR, f))
    except: 
        total_q, q_size, clean_size, files = 0, 0, 0, []
        log_count, hist_count, trash_count = 0, 0, 0

    table = Table(box=box.ROUNDED, show_header=False, min_width=28, border_style=_CONFIG.COLOR_STATS) 
    table.add_row("📂 Bộ đề", str(len(files)))
    table.add_row("❓ Tổng câu", f"[bold green]{total_q}[/]")
    table.add_row("📁 File tạm", str(log_count + hist_count))
    table.add_row("🗑️ Thùng rác", str(trash_count))
    table.add_row("💾 Lưu trữ bộ đề", f"[bold cyan]{f_size(q_size)}[/]")
    table.add_row("🧹 Lưu trữ nên xóa", f"[bold yellow]{f_size(clean_size)}[/]")
    table.add_row("📊 Lưu trữ thực tế", f"[bold magenta]{f_size(q_size + clean_size)}[/]")

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

def _choose_file_path_util(file_mgr, allow_all=False, show=True, exclude_disabled=False, context_name="", hide_empty=False):
    if context_name:
        console.print(f"\n[bold yellow]📍 ĐANG THỰC HIỆN:[/] [bold cyan]{context_name.upper()}[/]")

    files = file_mgr.list_files(show=show, exclude_disabled=exclude_disabled, hide_empty=hide_empty)
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
        disabled = file_mgr._get_disabled_list()
        if all_files:
            data = []
            for f in file_mgr.get_files():
                if f not in disabled and file_mgr.count_questions(f) > 0:
                    data.extend(card_mgr.load_data(os.path.join(file_mgr.qdir, f)))
            if data: game.run(data, *game.get_difficulty())
        else:
            _clear_screen()
            path = _choose_file_path_util(file_mgr, exclude_disabled=True, context_name="Luyện tập", hide_empty=True)
            if path:
                data = card_mgr.load_data(path)
                if data: game.run(data, n_opts=1) # Chế độ KISS: 1 đáp án, không hỏi mức độ
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
    path = _choose_file_path_util(file_mgr, show=False, context_name="Biên tập nội dung")
    if path:
        card_mgr.show_questions(path)
        menu_mgr._run_question_crud_menu(path)

def _clear_logs_util():
    """Tiện ích gọi lệnh dọn dẹp nhật ký từ LogManager."""
    LogManager.clear_logs()

def _manage_filter_categories_util(file_mgr, card_mgr):
    import src.process_input as inp
    f_path = os.path.join("data", "filter_categories.txt")
    os.makedirs("data", exist_ok=True)

    while True:
        _clear_screen()
        kws = []
        if os.path.exists(f_path):
            with open(f_path, "r", encoding="utf-8") as f:
                kws = [l.strip().lower() for l in f if l.strip() and not l.startswith("#")]
        
        # Gom toàn bộ dữ liệu từ các file CSV để đếm số lượng sử dụng
        all_data = []
        for f_name in file_mgr.get_files():
            all_data.extend(card_mgr.load_data(os.path.join(file_mgr.qdir, f_name)))
        
        # Tính toán thống kê
        stats = []
        for k in set(kws):
            count = sum(1 for row in all_data if len(row) > 2 and k in str(row[2]).lower())
            stats.append({"kw": k, "count": count})
        
        # Sắp xếp bảng thống kê theo số lượng câu hỏi sử dụng (giảm dần)
        stats.sort(key=lambda x: x['count'], reverse=True)
        
        table = Table(title="🏷️ QUẢN LÝ TỪ KHÓA BỘ LỌC", box=box.ROUNDED)
        table.add_column("STT", justify="right", style="cyan")
        table.add_column("Từ khóa đang sử dụng", style="bold white")
        table.add_column("Số câu liên quan", justify="right", style="green")
        
        for i, s in enumerate(stats, 1):
            table.add_row(str(i), s['kw'], str(s['count']))
        console.print(table)
        
        console.print("\n[bold cyan][A][/] Thêm  [bold yellow][E][/] Sửa  [bold red][D][/] Xoá  [bold white][Q][/] Thoát")
        cmd = _safe_input("👉 Lựa chọn: ")
        if not cmd or cmd.lower() == 'q': break
        
        action = cmd.lower()
        if action == 'a':
            new_k = inp.input_keyword()
            if new_k: kws.append(new_k.strip().lower())
        elif action in ['e', 'd'] and stats:
            idx = inp.input_selection("🔢 Nhập STT: ", len(stats))
            if idx is not None:
                target_kw = stats[idx]['kw']
                if action == 'e':
                    upd_k = inp.input_keyword(target_kw)
                    if upd_k: kws = [upd_k.strip().lower() if k == target_kw else k for k in kws]
                else:
                    if inp.input_confirm_generic(f"Xác nhận xoá '{target_kw}'? (y/n): ") == 'y':
                        kws = [k for k in kws if k != target_kw]
        
        # Lưu file: Sắp xếp lại theo bảng chữ cái (Sort theo file)
        kws = sorted(list(set(k.strip().lower() for k in kws if k.strip())))
        with open(f_path, "w", encoding="utf-8") as f:
            f.write("\n".join(kws))

def _show_mistake_stats_util():
    """Thống kê các câu hỏi thường xuyên bị trả lời sai từ lịch sử."""
    _clear_screen()
    console.print(Panel(Align.center("[bold red]❌ THỐNG KÊ LỖI SAI PHỔ BIẾN[/]"), border_style="red"))
    
    mistakes = {} # {question_text: [wrong_count, correct_count, correct_answer]}
    export_dir = _CONFIG.EXPORT_DIR
    if not os.path.exists(export_dir):
        console.print("[yellow]⚠️ Chưa có dữ liệu lịch sử để phân tích.[/]")
        console.input(f"\n[cyan]Nhấn Enter để quay lại...[/]")
        return

    h_files = [f for f in os.listdir(export_dir) if f.startswith("quiz_results_")]
    if not h_files:
        console.print("[yellow]⚠️ Chưa có kết quả lượt chơi nào được lưu lại.[/]")
        console.input(f"\n[cyan]Nhấn Enter để quay lại...[/]")
        return

    # 1. Tải dữ liệu độ khó trung bình từ difficult.csv
    avg_difficulty = {} # {qid: avg_score}
    diff_path = os.path.join("data", "difficult.csv")
    if os.path.exists(diff_path):
        try:
            diff_raw = {} # {qid: [scores]}
            with open(diff_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    qid, score = row.get("id"), row.get("độ khó")
                    if qid and score:
                        if qid not in diff_raw: diff_raw[qid] = []
                        diff_raw[qid].append(int(score))
            avg_difficulty = {k: sum(v)/len(v) for k, v in diff_raw.items()}
        except: pass

    # 2. Ánh xạ Nội dung (đã style) -> ID để tra cứu độ khó
    text_to_id = {}
    q_dir = _CONFIG.QUESTIONS_DIR
    if os.path.exists(q_dir):
        for f_name in os.listdir(q_dir):
            if f_name.endswith(".csv"):
                try:
                    with open(os.path.join(q_dir, f_name), encoding="utf-8-sig") as f:
                        # Tự động nhận diện delimiter
                        head = f.read(1024); f.seek(0)
                        delim = ';' if ';' in head and ',' not in head else ','
                        reader = csv.reader(f, delimiter=delim)
                        next(reader, None) # Bỏ qua header
                        for row in reader:
                            if len(row) >= 3:
                                # Engine lưu log question đã qua xử lý màu, nên ta map theo key đó
                                text_to_id[_replace_colors(row[2])] = row[0]
                except: pass

    with console.status("[bold red]Đang tổng hợp dữ liệu lỗi...[/]"):
        for f_name in h_files:
            try:
                with open(os.path.join(export_dir, f_name), encoding="utf-8-sig") as f:
                    reader = list(csv.reader(f))
                    # Dữ liệu kết quả bắt đầu từ dòng index 7
                    if len(reader) < 8 or len(reader[0]) < 2: continue
                    file_ts = reader[0][1]
                    for row in reader[7:]:
                        if len(row) >= 4:
                            q_text, ans_text, is_ok = row[1], row[2], row[3].strip().lower() == "true"
                            if q_text not in mistakes:
                                mistakes[q_text] = [0, 0, ans_text, None, None] # [w, c, ans, last_w, last_c]
                            
                            if is_ok:
                                mistakes[q_text][1] += 1
                                if not mistakes[q_text][4] or file_ts > mistakes[q_text][4]:
                                    mistakes[q_text][4] = file_ts
                            else:
                                mistakes[q_text][0] += 1
                                if not mistakes[q_text][3] or file_ts > mistakes[q_text][3]:
                                    mistakes[q_text][3] = file_ts
            except: pass

    # Chỉ hiển thị những câu đã từng sai ít nhất 1 lần
    stats = {q: v for q, v in mistakes.items() if v[0] > 0}

    if not stats:
        console.print("\n[bold green]✨ Tuyệt vời! Bạn chưa làm sai câu nào trong các lượt chơi gần đây.[/]")
    else:
        # Sắp xếp dựa trên cấu hình MISTAKE_SORT_BY
        sort_mode = getattr(_CONFIG, 'MISTAKE_SORT_BY', 'wrong_desc')
        if sort_mode == "correct_asc":
            sorted_mistakes = sorted(stats.items(), key=lambda x: (x[1][1], -x[1][0]))
        elif sort_mode == "diff_asc":
            sorted_mistakes = sorted(stats.items(), key=lambda x: (x[1][1] - x[1][0], -x[1][0]))
        else: # Mặc định: wrong_desc
            sorted_mistakes = sorted(stats.items(), key=lambda x: x[1][0], reverse=True)

        table = Table(box=box.ROUNDED, expand=True, show_lines=True)
        table.add_column("Số lần sai", justify="center", style="bold red")
        table.add_column("Ngày sai gần nhất", justify="center", style="red")
        table.add_column("Số lần đúng", justify="center", style="bold green")
        table.add_column("Ngày đúng gần nhất", justify="center", style="green")
        table.add_column("Hiệu số", justify="center")
        table.add_column("Độ khó", justify="center")
        table.add_column("Nội dung câu hỏi", style="white")
        table.add_column("Đáp án đúng", style="green")

        for q, (w, c, ans, lw, lc) in sorted_mistakes:
            diff = c - w
            diff_style = "bold green" if diff > 0 else "bold red" if diff < 0 else "white"
            diff_str = f"[{diff_style}]{'+' if diff > 0 else ''}{diff}[/]"

            def fmt_ts(ts):
                if not ts: return "[dim]-[/]"
                try:
                    dt = datetime.datetime.fromisoformat(ts)
                    return dt.strftime("%d/%m/%y")
                except: return "[dim]-[/]"

            # Lấy thông tin độ khó trung bình
            qid = text_to_id.get(q)
            score = avg_difficulty.get(qid)
            score_str = f"[bold yellow]{score:.1f} ⭐[/]" if score else "[dim]-[/]"
            
            table.add_row(str(w), fmt_ts(lw), str(c), fmt_ts(lc), diff_str, score_str, _replace_colors(q), _replace_colors(ans))
        console.print(table)
        console.print(f"\n[dim]💡 Hệ thống hiển thị toàn bộ danh sách các câu hỏi bạn đã từng trả lời sai.[/]")

    console.input(f"\n[cyan]Nhấn Enter để quay lại...[/]")

def _handle_file_deletion_util(file_mgr, show_list=True):
    p = _choose_file_path_util(file_mgr, allow_all=True, show=show_list, context_name="Xoá bộ đề")
    if p == "/all": file_mgr.delete_all_files()
    elif p: file_mgr.delete_file(p)