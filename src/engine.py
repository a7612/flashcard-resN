import random, string, re, csv, os, getpass
from rich.table import Table
from rich.text import Text
from rich import box
from src.core import _CONFIG, console
from src.utils import _replace_colors, _clear_screen, _handle_error, _get_now, _safe_input
from src.process_log import log_action, log_difficulty
import src.process_input as inp

class QuizGame:
    def __init__(self): pass

    def _clean_text(self, text):
        """Loại bỏ Rich Markup [style]...[/style] để so sánh đáp án."""
        clean = re.sub(r'\[/?[a-zA-Z #0-9,._-]+\]', '', str(text))
        return clean.strip().lower().rstrip('.')

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        # 1. Nhận diện câu hỏi Đúng/Sai đơn giản
        if "đúng hay sai" in q.lower(): return ["Đúng", "Sai"]
        
        # Thiết lập mục tiêu
        n_target = n_opts if (n_opts and n_opts > 1) else 4
        a_clean = a.strip().lower()
        pool, match_k, f_path = [], None, os.path.join("data", "filter_categories.txt")

        # 2. Tìm keyword (Đảm bảo 100% lowercase check)
        if os.path.exists(f_path):
            try:
                with open(f_path, "r", encoding="utf-8") as f:
                    # Đọc và lowercase toàn bộ keyword từ file
                    kws = [l.strip().lower() for l in f if l.strip() and not l.startswith("#")]
                match_k = next((k for k in kws if k in q.lower()), None)
            except: pass

        # 3. Gom pool distractors: Ưu tiên lọc theo keyword, không được thì lấy ngẫu nhiên
        if match_k:
            pool = list(set(str(x[1]).strip() for x in data 
                            if match_k in str(x[2]).lower() and str(x[1]).strip().lower() != a_clean))
        
        if not pool: # Fallback nếu không có keyword hoặc keyword không tìm thấy kết quả nào
            pool = list(set(str(x[1]).strip() for x in all_ans if str(x[1]).strip().lower() != a_clean))

        # 4. Lọc bỏ các giá trị Boolean và thực hiện "có nhiêu trả nhiêu" trong giới hạn n_target
        pool = [o for o in pool if o not in ["Đúng", "Sai"]]
        opts = random.sample(pool, min(len(pool), n_target - 1)) + [a]
        random.shuffle(opts)
        return [_replace_colors(o) for o in dict.fromkeys(opts)]

    def _feedback(self, ok, chosen, q, a, d, r, qid):
        log_action(f"CHOSEN:{qid}", f"{chosen} - {q} {'Đúng' if ok else 'Sai'}")
        if ok: 
            p = Text.from_markup("\n[bold white on green] ✨ CHÍNH XÁC! [/] ")
            p.append(Text.from_markup(chosen))
            console.print(p)
        else:
            p = Text.from_markup("\n[bold white on red] 🌪️ TIẾC QUÁ... [/] Đáp án đúng: ")
            p.append(Text.from_markup(a, style="bold yellow"))
            console.print(p)
        if r: console.print(f"[cyan]  📖 Mô tả thêm: \n[/]{r}")
        console.print("") 

    def _export_results(self, results, score, total):
        if total <= 0:
            console.print("[yellow]⚠️ Lượt chơi kết thúc mà không có câu hỏi nào được thực hiện.[/]")
            return

        wrong, pct = total - score, (score / total * 100) if total else 0.0
        table = Table(title="🏆 BẢNG VÀNG THÀNH TÍCH", box=box.DOUBLE_EDGE)
        table.add_column("STT", justify="right", style="cyan")
        table.add_column("TRẠNG THÁI", justify="center")
        table.add_column("ĐÁP ÁN CHUẨN", style="green")
        for r in results:
            table.add_row(str(r['index']), "💎" if r['ok'] else "🧨", r['correct'])
        if len(results) < total:
            table.add_row("...", "⏩", "[dim]Các câu còn lại đã bị bỏ qua...[/]")
            
        console.print(table)
        bar = "█"*int(30*pct//100) + "░"*(30-int(30*pct//100))
        console.print(f"\n[green]✅ Đúng: {score:<5}[/] [red]❌ Sai: {wrong:<5}[/] [cyan]📊 {pct:.1f}% [{bar}][/]\n")
        ts = _get_now().strftime("%Y%m%d_%H%M%S")
        csv_p = os.path.join(_CONFIG.EXPORT_DIR, f"quiz_results_{ts}.csv")
        try:
            with open(csv_p, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerows([["timestamp", _get_now().isoformat()], ["user", getpass.getuser()], ["total", total], ["score", score], ["percent", f"{pct:.1f}"], [], ["idx", "question", "correct", "ok", "hint", "desc"]] + [[r["index"], r["question"], r["correct"], r["ok"], r["hint"], r.get("desc", "")] for r in results])
            log_action("EXPORT_QUIZ", f"Score: {score}/{total} ({pct:.1f}%) -> {csv_p}")
            console.print(f"[bold green]💾 Đã xuất báo cáo: {csv_p}[/]")
        except Exception as e:
            console.print(f"[red]❌ Lỗi I/O khi xuất file CSV báo cáo: {e}[/]")

    def get_difficulty(self):
        table = Table(title="⚡ CHỌN MỨC ĐỘ THỬ THÁCH", box=box.SIMPLE)
        table.add_column("Key", style="bold cyan", justify="right"); table.add_column("Chế độ", style="white")
        modes = [
            ("1", "🍃 Dễ (10 câu, 3 đáp án)"),
            ("2", "🔥 Vừa (20 câu, 4 đáp án)"),
            ("3", "💀 Khó (50 câu, 6 đáp án)"),
            ("4", "👑 Hardcore (100 câu, 10 đáp án)"),
            ("5", "⚡ Sinh tồn (Sai là dừng, 4 đáp án)"),
            ("6", "🛠️ Tùy chỉnh (Tự thiết lập)")
        ]
        for k, v in modes: table.add_row(k, v)
        console.print(table)
        ch = inp.input_difficulty_mode()
        
        if ch == 5: return (4, 999, True) # Chế độ sinh tồn
        if ch == 6:
            opts, qs = inp.input_difficulty_custom()
            return opts, qs, False
            
        return {
            1: (3, 10, False), 
            2: (4, 20, False), 
            3: (6, 50, False), 
            4: (10, 100, False)
        }.get(ch, (4, 20, False))

    def run(self, data, n_opts=None, max_qs=None, survival=False):
        if not data:
            console.print("[yellow]⚠️ Không có dữ liệu câu hỏi để bắt đầu.[/]")
            return

        try:
            # Clean duplicates
            data = self._deduplicate_data(data)
            pool = random.sample(data, min(max_qs, len(data))) if max_qs else data[:]
            results, score = [], 0

            try:
                for i, (qid, a, q, d, r) in enumerate(pool, 1):
                    ok, chosen, info = self._ask_question(i, len(pool), qid, a, q, d, r, data, n_opts, score)
                    if chosen == "EXIT_SIGNAL": break
                    
                    if ok: score += 1
                    results.append({"index": i, "question": info[0], "correct": info[1], "hint": info[2], "desc": info[3], "ok": ok})
                    self._feedback(ok, chosen, *info, qid)

                    if not self._wait_next(qid): break

                    if survival and not ok:
                        console.print(f"\n[bold red]💀 GAME OVER![/] Bạn đã dừng bước tại câu {i} trong chế độ Sinh tồn.")
                        break
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold yellow]⏹️ Đã dừng lượt chơi giữa chừng.[/]")

            self._export_results(results, score, len(pool) if not survival else len(results))
        except Exception as e:
            log_action("ERROR_RUN", str(e))
            _handle_error(f"💥 Lỗi hệ thống trong quá trình Quiz: {e}")

    def _deduplicate_data(self, data):
        unique, seen = [], set()
        for row in data:
            if (q := str(row[2]).strip().lower()) not in seen:
                unique.append(row); seen.add(q)
        return unique

    def _ask_question(self, i, total, qid, a, q, d, r, data, n_opts, current_score):
        _clear_screen()
        console.rule(f"[bold white on blue] 📝 QUIZ [/] [cyan]{i}/{total}[/] │ [green]Score: {current_score}[/]")
        
        q_d, a_d, d_d, r_d = map(_replace_colors, (q, a, d or "", r or ""))
        # Sử dụng Text.from_markup để style bold white bao phủ toàn bộ question kể cả khi có tag reset
        console.print("\n", Text.from_markup(q_d, style="bold white"), "\n")
        
        opts = self._get_options(qid, q, a, data, data, n_opts) # Options đã được shuffle bên trong _get_options
        mapping = {k: v for k, v in zip(string.ascii_uppercase[:len(opts)], opts)}
        for k, v in mapping.items():
            # Cô lập phần (A), (B) để không bị ảnh hưởng bởi reset màu trong v
            console.print(Text.from_markup(f"  [bold cyan]({k})[/] ").append(Text.from_markup(v)))

        while True:
            u = inp.input_quiz_choice(mapping)
            if u == "EXIT_SIGNAL": return False, "EXIT_SIGNAL", None
            if u == "HINT_SIGNAL":
                console.print(f"[yellow]💡 Gợi ý: {d_d}[/]")
                continue
            
            chosen = mapping[u]
            return self._clean_text(chosen) == self._clean_text(a_d), chosen, (q_d, a_d, d_d, r_d)

    def _wait_next(self, qid=None):
        val = inp.input_difficulty_rating()
        if qid and val:
            log_action(f"RATING:{qid}", f"Difficulty: {val}")
            log_difficulty(qid, val)
        return True