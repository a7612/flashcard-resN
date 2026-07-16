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

    def _get_word_bank(self, all_ans):
        """Tạo ngân hàng từ vựng phân loại theo chữ cái đầu từ toàn bộ bộ đề."""
        if hasattr(self, '_cached_bank'): return self._cached_bank
        bank = {}
        for row in all_ans:
            # Lấy text từ cả Answer, Question, Hint và Desc để làm phong phú từ vựng
            text = self._clean_text(f"{row[1]} {row[2]} {row[3] or ''} {row[4] or ''}")
            # Tìm các từ có độ dài >= 2 (bỏ qua các từ đơn lẻ không nghĩa)
            words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
            for w in words:
                first = w[0].upper()
                if first not in bank: bank[first] = set()
                bank[first].add(w.capitalize())
        self._cached_bank = {k: list(v) for k, v in bank.items()}
        return self._cached_bank

    def _get_history_word_bank(self):
        """Quét lịch sử các lần làm sai để lấy từ vựng ưu tiên làm phương án nhiễu."""
        if hasattr(self, '_cached_history_bank'): return self._cached_history_bank
        bank = {}
        export_dir = _CONFIG.EXPORT_DIR
        if not os.path.exists(export_dir): return {}

        try:
            h_files = [f for f in os.listdir(export_dir) if f.startswith("quiz_results_")]
            for f_name in h_files:
                path = os.path.join(export_dir, f_name)
                with open(path, encoding="utf-8-sig") as f:
                    reader = list(csv.reader(f))
                    # Dữ liệu bắt đầu từ dòng index 7 (sau metadata và header)
                    if len(reader) < 8: continue
                    for row in reader[7:]:
                        if len(row) >= 4 and row[3].strip().lower() == "false":
                            text = self._clean_text(row[2]) # Cột 'correct'
                            words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
                            for w in words:
                                first = w[0].upper()
                                if first not in bank: bank[first] = set()
                                bank[first].add(w.capitalize())
        except: pass
        self._cached_history_bank = {k: list(v) for k, v in bank.items()}
        return self._cached_history_bank

    def _generate_fake_phrase(self, original_a, bank, h_bank=None):
        """Sinh cụm từ giả thông minh hơn bằng cách khớp độ dài từ gốc."""
        # Làm sạch và tách các từ gốc
        clean_a = re.sub(r'\(.*?\)', '', self._clean_text(original_a)).strip()
        words = [w for w in re.split(r'[\s\-_]+', clean_a) if w]
        if not words: return None
        
        # Nếu answer chỉ là 1 từ duy nhất và dài hơn 1 ký tự (VD: 'IMAP')
        # ta coi đó là acronym và sinh phrase dựa trên từng chữ cái của nó.
        if len(words) == 1 and len(words[0]) > 1:
            processing_targets = list(words[0].upper())
            is_acronym_mode = True
        else:
            processing_targets = words
            is_acronym_mode = False
        
        fake_phrase = []
        used_in_phrase = set()
        
        for target in processing_targets:
            first = target[0].upper()
            # Ưu tiên lấy từ ngân hàng lịch sử sai (h_bank), nếu không có mới lấy từ bank hiện tại
            candidates = h_bank.get(first, []) if h_bank and h_bank.get(first) else bank.get(first, [])
            if not candidates:
                fake_phrase.append(first)
                continue
            
            if is_acronym_mode:
                # Nếu sinh từ chữ cái đơn lẻ, ưu tiên từ có độ dài trung bình (4-9 ký tự) để phrase cân đối
                smart_candidates = [c for c in candidates if 4 <= len(c) <= 9 and c not in used_in_phrase]
            else:
                # Nếu sinh từ từ gốc, ưu tiên độ dài cực sát (chênh lệch <= 2 ký tự)
                smart_candidates = [c for c in candidates if abs(len(c) - len(target)) <= 2 and c not in used_in_phrase]
            
            # Fallback nếu không tìm được từ tương đương độ dài
            final_pool = smart_candidates if smart_candidates else [c for c in candidates if c not in used_in_phrase]
            chosen = random.choice(final_pool) if final_pool else random.choice(candidates)
            
            fake_phrase.append(chosen)
            used_in_phrase.add(chosen)
            
        return " ".join(fake_phrase)

    def _get_initials(self, text):
        """Lấy các chữ cái đầu. VD: 'Access Control List' -> 'ACL', 'ACL' -> 'ACL'."""
        # Loại bỏ nội dung trong ngoặc đơn nếu có: "Access Control List (ACL)" -> "Access Control List"
        clean = re.sub(r'\(.*?\)', '', self._clean_text(text)).strip()
        words = [w for w in re.split(r'[\s\-_]+', clean) if w]
        if not words: return ""
        
        # Nếu có nhiều từ, lấy các chữ cái đầu
        if len(words) > 1:
            return "".join(w[0] for w in words).upper()
        # Nếu chỉ có 1 từ, coi đó chính là chuỗi initials (ví dụ: 'ACL')
        return "".join(w[0] for w in words).upper()

    def _clean_text(self, text):
        """Loại bỏ Rich Markup [style]...[/style] để so sánh đáp án."""
        # Thay đổi dấu + thành * để nhận diện và loại bỏ cả thẻ đóng [/] của Rich
        clean = re.sub(r'\[/?[a-zA-Z #0-9,._-]*\]', '', str(text))
        return clean.strip().lower().rstrip('.')

    def _check_correctness(self, user_input, correct_answer):
        """So sánh đáp án có hỗ trợ Fuzzy Matching."""
        u_clean = self._clean_text(user_input)
        c_clean = self._clean_text(correct_answer)

        # 1. Kiểm tra khớp chính xác sau khi làm sạch
        if u_clean == c_clean:
            return True, 1.0
        
        if getattr(_CONFIG, 'FUZZY_MATCHING_ENABLED', False):
            u_words = u_clean.split()
            c_words = c_clean.split()
            
            if not c_words: return False, 0.0
            
            total_score = 0.0
            # Duyệt qua từng vị trí từ trong đáp án chuẩn
            for i in range(len(c_words)):
                c_word = c_words[i]
                
                # Nếu người dùng nhập thiếu từ ở vị trí này
                if i >= len(u_words):
                    continue
                
                u_word = u_words[i]
                if u_word == c_word:
                    # Từ đúng hoàn toàn ở vị trí này -> +1 điểm
                    total_score += 1.0
                else:
                    # So sánh ký tự nghiêm ngặt theo vị trí (Strict Index Matching)
                    char_matches = sum(1 for j in range(min(len(u_word), len(c_word))) if u_word[j] == c_word[j])
                    total_score += char_matches / max(len(u_word), len(c_word))

            # Tỉ lệ = (tổng điểm đạt được) / (tổng số từ tối đa giữa 2 chuỗi)
            # Việc chia cho max giúp phạt trường hợp người dùng nhập dư quá nhiều từ "rác"
            ratio = total_score / max(len(c_words), len(u_words))
            return ratio >= getattr(_CONFIG, 'FUZZY_MATCHING_THRESHOLD', 0.9), ratio
        return False, 0.0

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        tf_kws = getattr(_CONFIG, 'KEYWORD_BOOL', [])
        if any(kw.lower() in q.lower() for kw in tf_kws): return ["Đúng", "Sai"]
        
        # Thiết lập mục tiêu
        n_target, a_clean = n_opts if (n_opts is not None and n_opts >= 1) else 4, a.strip().lower()
        pool, match_k = [], None

        # 2. Kiểm tra xem có phải dạng câu hỏi viết tắt/giải nghĩa (acronym) không
        is_acronym_q = any(kw.lower() in q.lower() for kw in getattr(_CONFIG, 'KEYWORD_Q_INPUT', []))
        target_initials = self._get_initials(a)

        # 3. Gom pool distractors
        # Ưu tiên 1: Nếu là câu hỏi acronym (stand for, viết tắt), sinh phương án NGHIÊM NGẶT theo chữ cái đầu
        if is_acronym_q and len(target_initials) > 1:
            # Tìm các đáp án THỰC TẾ có cùng initials trong data trước
            pool = list(set(str(x[1]).strip() for x in all_ans 
                            if self._get_initials(str(x[1])) == target_initials and str(x[1]).strip().lower() != a_clean))
            
            # Luôn cố gắng sinh thêm phương án giả để đạt độ đa dạng, sử dụng bank từ vựng và lịch sử
            bank = self._get_word_bank(all_ans)
            h_bank = self._get_history_word_bank()
            
            for _ in range(100): # Tăng số lần thử
                fake = self._generate_fake_phrase(a, bank, h_bank)
                if fake and fake.lower() != a_clean and fake not in pool:
                    # Kiểm tra lại một lần nữa để chắc chắn initials khớp hoàn toàn
                    if self._get_initials(fake) == target_initials:
                        pool.append(fake)
                if len(pool) >= 20: break
            
            # QUAN TRỌNG: Với câu hỏi viết tắt, nếu không tìm/sinh đủ initials, 
            # chúng ta CHỈ lấy những gì đã có, không fallback sang các đáp án ngẫu nhiên khác.
        
        # Ưu tiên 2: Nếu KHÔNG PHẢI acronym, hoặc pool vẫn trống (không tìm thấy initials nào)
        if not pool:
            kws = self._get_kws()
            match_k = next((k for k in kws if k in q.lower()), None)
            
            if match_k:
                keyword_matches = [str(x[1]).strip() for x in data 
                                  if match_k in str(x[2]).lower() and str(x[1]).strip().lower() != a_clean]
                pool = list(set(pool + keyword_matches))

        # Ưu tiên 3: Fallback lấy ngẫu nhiên cho các dạng câu hỏi thông thường
        if not is_acronym_q and len(pool) < (n_target - 1):
            all_remaining = [str(x[1]).strip() for x in all_ans if str(x[1]).strip().lower() != a_clean]
            pool = list(set(pool + all_remaining))

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

    def _get_diff_visual(self, u_input, c_answer):
        """Tạo chuỗi màu sắc so sánh chi tiết giữa đáp án nhập và đáp án chuẩn."""
        u_words = self._clean_text(u_input).split()
        c_words = self._clean_text(c_answer).split()
        
        kq_sai = Text("\n➜ KQ sai : ")
        so_khop = Text("➜ So khớp: ")
        max_len = max(len(u_words), len(c_words))

        for i in range(max_len):
            if i > 0:
                kq_sai.append(" "); so_khop.append(" ")

            uw = u_words[i] if i < len(u_words) else ""
            cw = c_words[i] if i < len(c_words) else ""

            if uw == cw and uw != "":
                kq_sai.append(uw, style="bold green")
                so_khop.append(cw, style="bold green")
            else:
                # So sánh từng ký tự theo vị trí (Strict Character Alignment)
                word_max_len = max(len(uw), len(cw))
                for j in range(word_max_len):
                    uc = uw[j] if j < len(uw) else None
                    cc = cw[j] if j < len(cw) else None
                    
                    if uc == cc and uc is not None:
                        kq_sai.append(uc, style="bold green")
                        so_khop.append(cc, style="bold green")
                    else:
                        if uc is not None:
                            kq_sai.append(uc, style="bold red")
                        if cc is not None:
                            so_khop.append(cc, style="bold yellow")
            
        return kq_sai, so_khop

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
                p.append(Text.from_markup(f" [bold cyan]({ratio*100:.1f}%)[/]"))
            console.print(p)
            
            # Hiển thị so khớp chi tiết khi sai (không áp dụng cho Đúng/Sai đơn giản)
            if chosen and str(chosen).lower() not in ["đúng", "sai"]:
                kq_sai, so_khop = self._get_diff_visual(chosen, a)
                console.print(kq_sai)
                console.print(so_khop)

        if r: console.print(f"[cyan]  📖 Mô tả thêm: \n[/]{r}")
        console.print("") 

    def _export_results(self, results, score, total):
        if total <= 0:
            console.print("[yellow]⚠️ Lượt chơi kết thúc mà không có câu hỏi nào được thực hiện.[/]")
            return

        wrong, pct = total - score, (score / total * 100) if total else 0.0
        table = Table(title="BẢNG VÀNG THÀNH TÍCH", box=box.DOUBLE_EDGE)
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
            ("1", "[green]Dễ (10 câu, 3 đáp án)[/]"),
            ("2", "[yellow]Vừa (20 câu, 4 đáp án)[/]"),
            ("3", "[red]Khó (50 câu, 6 đáp án)[/]"),
            ("4", "[magenta]Hardcore (100 câu, 10 đáp án)[/]"),
            ("5", "Sinh tồn (Sai là dừng, 4 đáp án)"),
            ("6", "Tùy chỉnh (Tự thiết lập)")
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
            console.print("[yellow]Không có dữ liệu câu hỏi để bắt đầu.[/]")
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
                        console.print(f"\n[bold red]GAME OVER![/] Bạn đã dừng bước tại câu {i} trong chế độ Sinh tồn.")
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
        console.rule(f"[bold white on blue]QUIZ [/] [cyan]{i}/{total}[/] │ [green]Score: {current_score}[/]")
        
        q_d, a_d, d_d, r_d = map(_replace_colors, (q, a, d or "", r or ""))
        # Sử dụng Text.from_markup để style bold white bao phủ toàn bộ question kể cả khi có tag reset
        console.print("\n", Text.from_markup(q_d, style="bold white"), "\n")
        
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