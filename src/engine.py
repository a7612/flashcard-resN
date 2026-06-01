import random, string, re, csv, os, getpass, difflib
from rich.table import Table
from rich.text import Text
from rich import box
from src.core import _CONFIG, console
from src.utils import _replace_colors, _clear_screen, _handle_error, _get_now, _safe_input
from src.process_log import log_action, log_difficulty
import src.process_input as inp

class QuizGame:
    def __init__(self): pass

    def _get_kws(self):
        """Đọc và cache danh sách từ khóa từ filter_categories.txt."""
        if hasattr(self, '_cached_kws'): return self._cached_kws
        f_path = os.path.join("data", "filter_categories.txt")
        self._cached_kws = []
        if os.path.exists(f_path):
            try:
                with open(f_path, "r", encoding="utf-8") as f:
                    self._cached_kws = [l.strip().lower() for l in f if l.strip() and not l.startswith("#")]
            except: pass
        return self._cached_kws

    def _clean_text(self, text):
        """Loại bỏ Rich Markup [style]...[/style] để so sánh đáp án."""
        # Thay đổi dấu + thành * để nhận diện và loại bỏ cả thẻ đóng [/] của Rich
        clean = re.sub(r'\[/?[a-zA-Z #0-9,._-]*\]', '', str(text))
        return clean.strip().lower().rstrip('.')

    def _check_correctness(self, user_input, correct_answer):
        """So sánh đáp án có hỗ trợ Fuzzy Matching."""
        u = self._clean_text(user_input)
        c = self._clean_text(correct_answer)
        if u == c: return True, 1.0
        
        ratio = 0.0
        if getattr(_CONFIG, 'FUZZY_MATCHING_ENABLED', False):
            ratio = difflib.SequenceMatcher(None, u, c).ratio()
            return ratio >= getattr(_CONFIG, 'FUZZY_MATCHING_THRESHOLD', 0.9), ratio
        return False, ratio

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        tf_kws = getattr(_CONFIG, 'KEYWORD_BOOL', [])
        if any(kw.lower() in q.lower() for kw in tf_kws): return ["Đúng", "Sai"]
        
        # Thiết lập mục tiêu
        n_target, a_clean = n_opts if (n_opts and n_opts > 1) else 4, a.strip().lower()
        pool, match_k = [], None

        # 2. Tìm keyword
        kws = self._get_kws()
        match_k = next((k for k in kws if k in q.lower()), None)

        # 3. Gom pool distractors: Ưu tiên lọc theo keyword, không được thì lấy ngẫu nhiên
        if match_k:
            pool = list(set(str(x[1]).strip() for x in data 
                            if match_k in str(x[2]).lower() and str(x[1]).strip().lower() != a_clean))
        
        if not pool: # Fallback nếu không có keyword hoặc keyword không tìm thấy kết quả nào
            pool = list(set(str(x[1]).strip() for x in all_ans if str(x[1]).strip().lower() != a_clean))

        # 4. Lọc bỏ các giá trị Boolean và thực hiện "có nhiêu trả nhiêu" trong giới hạn n_target
        pool = [o for o in pool if o not in ["Đúng", "Sai"]]

        # 5. Thuật toán lọc theo độ dài (Length Similarity)
        # Sắp xếp pool theo trị tuyệt đối độ chênh lệch chiều dài so với đáp án đúng 'a'
        target_len = len(str(a))
        pool.sort(key=lambda x: abs(len(str(x)) - target_len))

        # Lấy một nhóm các câu có độ dài gần nhất (ví dụ top 20 câu hoặc gấp 3 số lượng cần lấy)
        # để vẫn đảm bảo tính ngẫu nhiên khi sample, tránh việc 10 lần chơi đều ra 3 phương án y hệt nhau.
        candidate_pool = pool[:max(20, (n_target - 1) * 3)]
        
        opts = random.sample(candidate_pool, min(len(candidate_pool), n_target - 1)) + [a]
        random.shuffle(opts)
        return [_replace_colors(o) for o in dict.fromkeys(opts)]

    def _feedback(self, ok, chosen, q, a, d, r, ratio, qid):
        log_action(f"CHOSEN:{qid}", f"{chosen} - {q} {'Đúng' if ok else 'Sai'}")
        if ok: 
            p = Text.from_markup("\n[bold white on green] ✨ CHÍNH XÁC! [/] ")
            p.append(Text.from_markup(chosen))
            console.print(p)
        else:
            p = Text.from_markup("\n[bold white on red] 🌪️ TIẾC QUÁ... [/] Đáp án đúng: ")
            p.append(Text.from_markup(a, style="bold yellow"))
            if not ok and getattr(_CONFIG, 'FUZZY_MATCHING_ENABLED', False) and ratio > 0:
                p.append(Text.from_markup(f" [dim](Gần đúng: {ratio*100:.1f}%)[/]"))
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
            
            # Thuật toán giới hạn tần suất keyword: Ưu tiên đa dạng hóa bộ đề
            random.shuffle(data)
            kws = self._get_kws()
            limit = getattr(_CONFIG, 'MAX_SAME_KEYWORD_PER_QUIZ', 5)
            
            pool, overflow, kw_counts = [], [], {}
            for row in data:
                match_k = next((k for k in kws if k in str(row[2]).lower()), None)
                if match_k:
                    count = kw_counts.get(match_k, 0)
                    if count < limit:
                        pool.append(row)
                        kw_counts[match_k] = count + 1
                    else:
                        overflow.append(row)
                else:
                    pool.append(row)
            
            # Nếu chưa đủ số lượng yêu cầu, lấy thêm từ phần dư (overflow)
            if max_qs:
                if len(pool) < max_qs:
                    pool.extend(overflow[:max_qs - len(pool)])
                pool = pool[:max_qs]
            
            random.shuffle(pool)
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
            # Sử dụng cấu hình để xác định trường nào dùng để loại bỏ trùng lặp.
            # Mặc định là ID (index 0) để đảm bảo tính duy nhất cho các câu hỏi có cùng nội dung nhưng khác đáp án.
            # Có thể cấu hình thành 2 trong config.py để loại bỏ các câu hỏi có nội dung giống nhau.
            key_value = str(row[_CONFIG.DEDUPLICATE_COLUMN_INDEX]).strip().lower()
            if key_value not in seen:
                unique.append(row)
                seen.add(key_value)
        return unique

    def _ask_question(self, i, total, qid, a, q, d, r, data, n_opts, current_score):
        _clear_screen()
        console.rule(f"[bold white on blue] 📝 QUIZ [/] [cyan]{i}/{total}[/] │ [green]Score: {current_score}[/]")
        
        q_d, a_d, d_d, r_d = map(_replace_colors, (q, a, d or "", r or ""))
        # Sử dụng Text.from_markup để style bold white bao phủ toàn bộ question kể cả khi có tag reset
        console.print("\n", Text.from_markup(q_d, style="bold white"), "\n")
        
        # Kiểm tra chế độ nhập liệu trực tiếp (Fill-in-the-blank)
        is_input_mode = any(kw.lower() in q.lower() for kw in getattr(_CONFIG, 'KEYWORD_Q_INPUT', []))

        if is_input_mode:
            while True:
                prompt = "👉 Nhập đáp án (? để nhận gợi ý): " if bool(d) else "👉 Nhập đáp án: "
                u = _safe_input(f"\n{prompt}")
                if u is None: return False, "EXIT_SIGNAL", None
                if u == "?":
                    console.print(f"[yellow]💡 Gợi ý: {d_d}[/]")
                    continue
                # So sánh đáp án nhập vào với đáp án chuẩn (đã làm sạch)
                ok, ratio = self._check_correctness(u, a)
                return ok, u, (q_d, a_d, d_d, r_d, ratio)
        else:
            # Chế độ trắc nghiệm (Multiple Choice) truyền thống
            opts = self._get_options(qid, q, a, data, data, n_opts)
            mapping = {k: v for k, v in zip(string.ascii_uppercase[:len(opts)], opts)}
            for k, v in mapping.items():
                # Cô lập phần (A), (B) để không bị ảnh hưởng bởi reset màu trong v
                console.print(Text.from_markup(f"  [bold cyan]({k})[/] ").append(Text.from_markup(v)))

            while True:
                u = inp.input_quiz_choice(mapping, has_hint=bool(d))
                if u == "EXIT_SIGNAL": return False, "EXIT_SIGNAL", None
                if u == "HINT_SIGNAL":
                    console.print(f"[yellow]💡 Gợi ý: {d_d}[/]")
                    continue
                
                chosen = mapping[u]
                ok, ratio = self._check_correctness(chosen, a)
                return ok, chosen, (q_d, a_d, d_d, r_d, ratio)

    def _wait_next(self, qid=None):
        val = inp.input_difficulty_rating()
        if qid and val:
            log_action(f"RATING:{qid}", f"Difficulty: {val}")
            log_difficulty(qid, val)
        return True