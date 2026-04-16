import random, string, datetime, re, csv, os
from rich.table import Table
from rich.text import Text
from rich import box
from config import *
from src.core import _CONFIG, console, log_action, _replace_colors, _clear_screen, _handle_error, _get_now

class QuizGame:
    def __init__(self, app): self.app = app

    def _clean_text(self, text):
        """Loại bỏ Rich Markup [style]...[/style] để so sánh đáp án."""
        clean = re.sub(r'\[/?[a-zA-Z #0-9,._-]+\]', '', str(text))
        return clean.strip().lower().rstrip('.')

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        q_lower = q.lower()
        if any(k in q_lower for k in _CONFIG.KEYWORD_BOOL): return ["Đúng", "Sai"]
        
        # Đảm bảo n_opts tối thiểu là 4 nếu không được chỉ định rõ ràng hoặc bằng 1
        n_target = n_opts if (n_opts and n_opts > 1) else 4
        
        target = {a}
        related = []
        for r in data:
            ans_val = r[1]
            ques_val = r[2].lower()
            if ans_val.strip() != a.strip():
                # Lọc bỏ các đáp án quá dài so với đáp án chuẩn để tránh "rác"
                if len(a) < 20 and len(ans_val) > 100:
                    continue
                
                # Tìm đáp án liên quan dựa trên từ khóa câu hỏi
                for k in _CONFIG.KEYWORD:
                    if k in q_lower and k in ques_val:
                        related.append(ans_val)
                        break
                        
        target.update(related)
        candidates = []
        for x in all_ans:
            ans_candidate = x[1]
            if ans_candidate.strip() != a.strip() and ans_candidate not in target:
                candidates.append(ans_candidate)
                
        if len(target) < n_target:
            target.update(random.sample(candidates, min(len(candidates), n_target - len(target))))
        
        final_pool = list(target - {a, "Đúng", "Sai"})
        opts = random.sample(final_pool, min(len(final_pool), max(0, n_target - 1)))
        opts.append(a)
        
        colored_opts = []
        for o in dict.fromkeys(opts):
            colored_opts.append(_replace_colors(o))
        return colored_opts

    def _feedback(self, ok, chosen, q, a, d, r, qid):
        log_action(f"CHOSEN:{qid}", f"{chosen} - {q} {'Đúng' if ok else 'Sai'}")
        if ok: console.print(f"\n[bold white on green] ✨ CHÍNH XÁC! [/] {chosen}")
        else:
            console.print(f"\n[bold white on red] 🌪️ TIẾC QUÁ... [/] Đáp án đúng: [bold yellow]{a}[/]")
        if r: console.print(f"[cyan]  📖 Mô tả thêm: \n[/]{r}")
        console.print("") 

    def _export_results(self, results, score, total):
        wrong, pct = total - score, (score / total * 100) if total else 0.0
        table = Table(title="🏆 BẢNG VÀNG THÀNH TÍCH", box=box.DOUBLE_EDGE)
        table.add_column("STT", justify="right", style="cyan")
        table.add_column("TRẠNG THÁI", justify="center")
        table.add_column("ĐÁP ÁN CHUẨN", style="green")
        for r in results: table.add_row(str(r['index']), "💎" if r['ok'] else "🧨", r['correct'])
        console.print(table)
        bar = "█"*int(30*pct//100) + "░"*(30-int(30*pct//100))
        console.print(f"\n[green]✅ Đúng: {score:<5}[/] [red]❌ Sai: {wrong:<5}[/] [cyan]📊 {pct:.1f}% [{bar}][/]\n")
        ts = _get_now().strftime("%Y%m%d_%H%M%S")
        csv_p = os.path.join(_CONFIG.EXPORT_DIR, f"quiz_results_{ts}.csv")
        try:
            with open(csv_p, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerows([["timestamp", _get_now().isoformat()], ["user", os.getlogin()], ["total", total], ["score", score], ["percent", f"{pct:.1f}"], [], ["idx", "question", "correct", "ok", "hint", "desc"]] + [[r["index"], r["question"], r["correct"], r["ok"], r["hint"], r.get("desc", "")] for r in results])
            console.print(f"[bold green]💾 Đã xuất báo cáo: {csv_p}[/]")
        except Exception as e:
            console.print(f"[red]❌ Lỗi I/O khi xuất file CSV báo cáo: {e}[/]")

    def get_difficulty(self):
        table = Table(title="⚡ CHỌN MỨC ĐỘ THỬ THÁCH", box=box.SIMPLE)
        table.add_column("Key", style="bold cyan", justify="right"); table.add_column("Chế độ", style="white")
        for k, v in [("0", "⚙️ Mặc định"), ("1", "🍃 Dễ (10 câu)"), ("2", "🔥 Vừa (20 câu)"), ("3", "💀 Khó (50 câu)"), ("4", "👑 Hardcore (100 câu)")]: table.add_row(k, v)
        console.print(table)
        try: ch = int(console.input(f"\n👉 Lựa chọn của bạn: "))
        except (ValueError, EOFError, KeyboardInterrupt): ch = 0
        return {1: (1, 10), 2: (4, 20), 3: (6, 50), 4: (random.randint(8, 24), 100)}.get(ch, (_CONFIG.MAX_GENERATE_NORMAL_ANSWERS, _CONFIG.MAX_GENERATE_NORMAL_QUESTIONS))

    def run(self, data, n_opts=None, max_qs=None, source=None):
        if not data:
            console.print("[yellow]⚠️ Không có dữ liệu câu hỏi để bắt đầu.[/]")
            return

        try:
            # Clean duplicates
            data = self._deduplicate_data(data)
            pool = random.sample(data, min(max_qs, len(data))) if max_qs else data[:]
            results, score = [], 0

            for i, (qid, a, q, d, r) in enumerate(pool, 1):
                ok, chosen, info = self._ask_question(i, len(pool), qid, a, q, d, r, data, n_opts, score)
                if chosen == "EXIT_SIGNAL": break
                
                if ok: score += 1
                results.append({"index": i, "question": info[0], "correct": info[1], "hint": info[2], "desc": info[3], "ok": ok})
                self._feedback(ok, chosen, *info, qid)
                
                if i < len(pool) and not self._wait_next(): break

            self._export_results(results, score, len(results))
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
        console.rule(f"[bold white on blue] 📝 QUIZ [/] [cyan]{i}/{total}[/] │ [green]Score: {current_score}[/] │ [dim]{qid[-6:]}[/]")
        q_d, a_d, d_d, r_d = map(_replace_colors, (q, a, d or "", r or ""))
        # Sử dụng style làm gốc để lệnh [/] bên trong q_d reset về đúng màu này
        console.print(f"\n{q_d}\n", style="bold white")
        
        opts = self._get_options(qid, q, a, data, data, n_opts); random.shuffle(opts)
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

    def _wait_next(self):
        try: 
            console.input("[grey50] [Enter] Tiếp tục...[/]")
            return True
        except: return False