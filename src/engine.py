import random, string, datetime, re, csv, os
from rich.table import Table
from rich.text import Text
from rich import box
from config import *
from src.core import _CONFIG, console, log_action, _replace_colors, _clear_screen

class QuizGame:
    def __init__(self, app): self.app = app

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        if any(k in q.lower() for k in _CONFIG.KEYWORD_BOOL): return ["Đúng", "Sai"]
        target = {a}; related = [r[1] for r in data if r[1].strip() != a.strip() and any(k in r[2].lower() for k in _CONFIG.KEYWORD if k in q.lower())]
        target.update(related)
        candidates = [x[1] for x in all_ans if x[1].strip() != a.strip() and x[1] not in target]
        if len(target) < (n_opts or 4): target.update(random.sample(candidates, min(len(candidates), (n_opts or 4) - len(target))))
        final = list(target - {a, "Đúng", "Sai"}); opts = random.sample(final, min(final_len := len(final), max(0, (n_opts or 4) - 1))) + [a]
        return [_replace_colors(o) for o in dict.fromkeys(opts)]

    def _feedback(self, ok, chosen, q, a, d, r, qid):
        log_action(f"CHOSEN:{qid}", f"{chosen} - {q} {'Đúng' if ok else 'Sai'}")
        if ok: console.print(Text().append("\n ✨ CHÍNH XÁC! ", style="bold white on green").append(" ").append(Text.from_ansi(chosen)))
        else:
            ans_txt = Text.from_ansi(a); ans_txt.stylize("bold yellow")
            console.print(Text().append("\n 🌪️ TIẾC QUÁ... ", style="bold white on red").append(" Đáp án đúng: ").append(ans_txt))
        if r: console.print(Text("  📖 Mô tả thêm: \n", style="cyan").append(Text.from_ansi(r)))
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
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_p = os.path.join(_CONFIG.EXPORT_DIR, f"quiz_results_{ts}.csv")
        with open(csv_p, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows([["timestamp", datetime.datetime.now().isoformat()], ["user", os.getlogin()], ["total", total], ["score", score], ["percent", f"{pct:.1f}"], [], ["idx", "question", "correct", "ok", "hint", "desc"]] + [[r["index"], r["question"], r["correct"], r["ok"], r["hint"], r.get("desc", "")] for r in results])
        print(f"{BRIGHT_GREEN}💾 Đã xuất báo cáo: {csv_p}{RESET}")

    def get_difficulty(self):
        table = Table(title="⚡ CHỌN MỨC ĐỘ THỬ THÁCH", box=box.SIMPLE)
        table.add_column("Key", style="bold cyan", justify="right"); table.add_column("Chế độ", style="white")
        for k, v in [("0", "⚙️ Mặc định"), ("1", "🍃 Dễ (10 câu)"), ("2", "🔥 Vừa (20 câu)"), ("3", "💀 Khó (50 câu)"), ("4", "👑 Hardcore (100 câu)")]: table.add_row(k, v)
        console.print(table)
        try: ch = int(console.input(f"\n👉 Lựa chọn của bạn: "))
        except: ch = 0
        return {1: (1, 10), 2: (4, 20), 3: (6, 50), 4: (random.randint(8, 24), 100)}.get(ch, (_CONFIG.MAX_GENERATE_NORMAL_ANSWERS, _CONFIG.MAX_GENERATE_NORMAL_QUESTIONS))

    def run(self, data, n_opts=None, max_qs=None, source=None):
        if not data: return print("❗ Không tìm thấy dữ liệu câu hỏi.")
        pool, results, score = (random.sample(data, min(max_qs, len(data))) if max_qs else data[:]), [], 0
        for i, (qid, a, q, d, r) in enumerate(pool, 1):
            _clear_screen()
            console.rule(f"[bold white on blue] 📝 QUIZ TIME [/] [cyan]Câu {i}/{len(pool)}[/] │ [green]Score: {score}[/] │ [dim]ID: {qid[-6:]}[/]")
            q_d, a_d, d_d, r_d = map(_replace_colors, (q, a, d or "", r or ""))
            console.print(Text("\n").append(Text.from_ansi(q_d)).append("\n"), style="bold white")
            opts = self._get_options(qid, q, a, data, data, n_opts); random.shuffle(opts)
            mapping = {k: v for k, v in zip(string.ascii_uppercase[:len(opts)], opts)}
            for k, v in mapping.items(): console.print(Text().append(f"  ({k}) ", style="bold cyan").append(Text.from_ansi(v)))
            while True:
                u = console.input(f"\n👉 Chọn ([bold cyan]A-{list(mapping)[-1]}[/]) / '?' Gợi ý / '/exit': ").strip().upper()
                if u == 'EXIT': return self._export_results(results, score, len(results))
                if u == '?': print(f"{YELLOW}💡 Gợi ý:{RESET}\n{d_d}"); continue
                if u in mapping: chosen = mapping[u]; break
                print(f"{BRIGHT_RED}❌ Lựa chọn không hợp lệ.{RESET}")
            clean = lambda t: re.sub(r'\{[A-Z0-9_]+\}|\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', str(t)).strip().lower().rstrip('.')
            ok = clean(chosen) == clean(a)
            if ok: score += 1
            results.append({"index": i, "question": q_d, "correct": a_d, "hint": d_d, "desc": r_d, "ok": ok})
            self._feedback(ok, chosen, q_d, a_d, d_d, r_d, qid)
            if i < len(pool): input(f"{BRIGHT_BLACK}[Phím bất kỳ] để tiếp tục...{RESET}")
        self._export_results(results, score, len(pool))