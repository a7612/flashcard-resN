import random, string, re, csv, os, getpass
from rich.table import Table
from rich.text import Text
from rich import box
from src.core import _CONFIG, console
from src.utils import _replace_colors, _clear_screen, _handle_error, _get_now, _safe_input
from src.process_log import log_action, log_difficulty

class QuizGame:
    def __init__(self): pass

    def _clean_text(self, text):
        """Loại bỏ Rich Markup [style]...[/style] để so sánh đáp án."""
        clean = re.sub(r'\[/?[a-zA-Z #0-9,._-]+\]', '', str(text))
        return clean.strip().lower().rstrip('.')

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        q_lower = q.lower()
        
        # 1. Check type_question: Nếu chứa từ khóa Bool -> trả về Đúng/Sai ngay
        if any(kw.lower() in q_lower for _, kw in _CONFIG.KEYWORD_BOOL): 
            return ["Đúng", "Sai"]
        
        n_target = n_opts if (n_opts and n_opts > 1) else 4

        # 2. Nhận diện Domain (Chủ đề): Kết hợp từ khóa CSV và Tiền tố "Subject:"
        current_domains = {kw.lower() for _, kw in _CONFIG.KEYWORD if kw.lower() in q_lower}
        # Tự động trích xuất Subject từ prefix (vd: "Cyber Security: ..." -> "cyber security")
        prefix_match = re.match(r'^([^:]{2,30}):', q)
        if prefix_match:
            current_domains.add(prefix_match.group(1).lower().strip())

        # Phân loại ứng viên vào 3 tầng ưu tiên
        same_domain, neutral, different_domain = [], [], []
        
        for x in all_ans:
            cand_a, cand_q = x[1], str(x[2]).lower()
            if cand_a.strip() == a.strip(): continue

            # Lọc bỏ đáp án quá dài/ngắn không tương đồng để giữ thẩm mỹ
            if len(a) < 25 and len(cand_a) > 120: continue

            # Nhận diện Domain của ứng viên
            cand_domains = {kw.lower() for _, kw in _CONFIG.KEYWORD if kw.lower() in cand_q}
            # Trích xuất prefix của ứng viên (nếu có)
            c_prefix = re.match(r'^([^:]{2,30}):', x[2])
            if c_prefix:
                cand_domains.add(c_prefix.group(1).lower().strip())
            
            if current_domains:
                if current_domains.intersection(cand_domains):
                    same_domain.append(cand_a)
                elif not cand_domains:
                    neutral.append(cand_a)
                else:
                    different_domain.append(cand_a)
            else:
                if not cand_domains:
                    same_domain.append(cand_a) # Nếu Q gốc ko domain, ưu tiên candidate ko domain
                else:
                    different_domain.append(cand_a)

        # Sắp xếp mỗi tầng theo độ dài tương đồng để tăng tính đánh lừa
        for pool in [same_domain, neutral, different_domain]:
            pool.sort(key=lambda x: abs(len(x) - len(a)))

        target = {a}
        def fill_from_pool(source_pool):
            if len(target) >= n_target: return
            # Lấy top 15 ứng viên tương đồng nhất về độ dài, sau đó bốc ngẫu nhiên
            candidates = source_pool[:15]
            random.shuffle(candidates)
            for item in candidates:
                if len(target) >= n_target: break
                target.add(item)

        # Đổ dữ liệu theo thứ tự ưu tiên
        fill_from_pool(same_domain)
        fill_from_pool(neutral)
        fill_from_pool(different_domain)

        final_pool = list(target - {"Đúng", "Sai"})
        if a in final_pool: final_pool.remove(a)

        opts = random.sample(final_pool, min(len(final_pool), max(0, n_target - 1)))
        opts.append(a)

        return [_replace_colors(o) for o in opts]

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
        try: ch = int(console.input(f"\n👉 Lựa chọn của bạn: "))
        except (ValueError, EOFError, KeyboardInterrupt): ch = 1
        
        if ch == 5: return (4, 999, True) # Chế độ sinh tồn
        if ch == 6:
            qs = int(_safe_input("📝 Số lượng câu hỏi: ") or 10)
            opts = int(_safe_input("🔢 Số lượng đáp án hiển thị: ") or 4)
            return (opts, qs, False)
            
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
            try:
                u = console.input(f"\n👉 Đáp án: ").strip().upper()
                if u in ['/EXIT', 'EXIT']: return False, "EXIT_SIGNAL", None
                if u == '?': console.print(f"[yellow]💡 Gợi ý: {d_d}[/]"); continue
                if u in mapping:
                    chosen = mapping[u]
                    return self._clean_text(chosen) == self._clean_text(a_d), chosen, (q_d, a_d, d_d, r_d)
                console.print("[red]❌ Sai cú pháp![/]")
            except (EOFError, KeyboardInterrupt): return False, "EXIT_SIGNAL", None

    def _wait_next(self, qid=None):
        try: 
            prompt = "[bold yellow]⭐ Hãy đánh giá độ khó của câu hỏi này (1-5, hoặc Enter để bỏ qua): [/]"
            val = console.input(prompt).strip()
            if qid and val.isdigit() and 1 <= int(val) <= 5:
                log_action(f"RATING:{qid}", f"Difficulty: {val}")
                log_difficulty(qid, val)
            return True
        except (EOFError, KeyboardInterrupt): return False