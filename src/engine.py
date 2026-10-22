import random, string, re, csv, os, getpass, difflib, time
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False
from rich.table import Table
from rich.text import Text
from rich import box
from src.core import _CONFIG, console
from src.utils import _replace_colors, _clear_screen, _handle_error, _get_now, _safe_input, _get_mistake_history_data
from src.process_log import log_action, log_difficulty
import src.process_input as inp

class QuizGame:
    def __init__(self): pass

    def _get_all_dataset_answers(self):
        """Tải toàn bộ dữ liệu từ tất cả các file câu hỏi trong QUESTIONS_DIR để làm kho đáp án chung."""
        if hasattr(self, '_cached_all_data'): return self._cached_all_data
        all_data = []
        qdir = _CONFIG.QUESTIONS_DIR
        if os.path.exists(qdir):
            try:
                for f_name in os.listdir(qdir):
                    if f_name.endswith(".csv"):
                        path = os.path.join(qdir, f_name)
                        with open(path, "r", encoding="utf-8-sig") as f:
                            reader = csv.reader(f)
                            for row in reader:
                                if len(row) >= 3 and row[0].strip() and row[0].strip().lower() != "id":
                                    # Chuẩn hóa row có đủ 5 cột (id, answer, question, hint, desc)
                                    row_ext = [row[0], row[1], row[2], row[3] if len(row) > 3 else "", row[4] if len(row) > 4 else ""]
                                    all_data.append(row_ext)
            except: pass
        self._cached_all_data = all_data
        return self._cached_all_data

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

    def _get_filter_wordbank(self):
        """Đọc danh sách từ bị cấm/lọc từ data/filter_wordbank.txt."""
        f_path = os.path.join("data", "filter_wordbank.txt")
        if not os.path.exists(f_path): return set()
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                return set(l.strip().lower() for l in f if l.strip() and not l.startswith("#"))
        except:
            return set()

    def _get_word_bank(self, all_ans):
        """Tạo ngân hàng từ vựng chuyên ngành cho câu hỏi viết tắt dựa trên KEYWORD_Q_INPUT.
        Chỉ bóc tách các từ tiếng Anh chuẩn trong đáp án của các câu hỏi viết tắt để tránh lẫn lộn tên riêng hay nội dung file khác.
        """
        if hasattr(self, '_cached_bank'): return self._cached_bank
        blacklist = self._get_filter_wordbank()
        acronym_kws = getattr(_CONFIG, 'KEYWORD_Q_INPUT', [])
        bank = {}
        for row in all_ans:
            # Kiểm tra câu hỏi có chứa từ khóa quy định trong KEYWORD_Q_INPUT (VD: 'viết tắt của', 'stand for', 'tên đầy đủ')
            q_text = str(row[2]).lower() if len(row) > 2 else ""
            if not any(kw.lower() in q_text for kw in acronym_kws):
                continue
            
            # Chỉ lấy các từ vựng từ Answer (loại bỏ chú thích trong ngoặc đơn nếu có)
            clean_ans = re.sub(r'\(.*?\)', '', self._clean_text(str(row[1]))).strip()
            words = re.findall(r'\b[a-zA-Z]{2,}\b', clean_ans)
            for w in words:
                if w.lower() in blacklist: continue
                first = w[0].upper()
                if first not in bank: bank[first] = set()
                bank[first].add(w.capitalize())
        self._cached_bank = {k: list(v) for k, v in bank.items()}
        return self._cached_bank

    def _get_history_word_bank(self):
        """Quét lịch sử các lần làm sai của các câu hỏi viết tắt (KEYWORD_Q_INPUT) để lấy từ vựng ưu tiên làm phương án nhiễu."""
        if hasattr(self, '_cached_history_bank'): return self._cached_history_bank
        blacklist = self._get_filter_wordbank()
        acronym_kws = getattr(_CONFIG, 'KEYWORD_Q_INPUT', [])
        bank = {}
        export_dir = _CONFIG.EXPORT_DIR
        if not os.path.exists(export_dir): return {}

        try:
            h_files = [f for f in os.listdir(export_dir) if f.startswith("quiz_results_")]
            for f_name in h_files:
                path = os.path.join(export_dir, f_name)
                with open(path, encoding="utf-8-sig") as f:
                    reader = list(csv.reader(f))
                    # Dữ liệu bắt đầu từ dòng index 7 (sau metadata và header: idx, question, correct, ok, hint, desc)
                    if len(reader) < 8: continue
                    for row in reader[7:]:
                        if len(row) >= 4 and row[3].strip().lower() == "false":
                            q_text = row[1].lower() if len(row) > 1 else ""
                            # Chỉ lấy từ lịch sử nếu câu hỏi thuộc dạng viết tắt (KEYWORD_Q_INPUT)
                            if not any(kw.lower() in q_text for kw in acronym_kws):
                                continue
                            clean_ans = re.sub(r'\(.*?\)', '', self._clean_text(row[2])).strip()
                            words = re.findall(r'\b[a-zA-Z]{2,}\b', clean_ans)
                            for w in words:
                                if w.lower() in blacklist: continue
                                first = w[0].upper()
                                if first not in bank: bank[first] = set()
                                bank[first].add(w.capitalize())
        except: pass
        self._cached_history_bank = {k: list(v) for k, v in bank.items()}
        return self._cached_history_bank

    def _generate_fake_phrase(self, original_a, bank, h_bank=None, forbidden_words=None):
        """Sinh cụm từ giả thông minh hơn bằng cách khớp độ dài từ gốc và loại trừ từ cấm/từ trong câu hỏi."""
        blacklist = self._get_filter_wordbank()
        forbidden = set(w.lower() for w in forbidden_words) if forbidden_words else set()
        forbidden.update(blacklist)

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
            # Gom candidates từ cả bank và h_bank để đảm bảo độ phong phú của kho từ
            raw_set = set(bank.get(first, []))
            if h_bank and h_bank.get(first):
                raw_set.update(h_bank.get(first, []))
            
            # Lọc bỏ các từ nằm trong forbidden (từ cấm hoặc từ trong câu hỏi)
            candidates = [c for c in raw_set if c.lower() not in forbidden]
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
        t = str(text)
        for kw in ["{bs}", "{backslash}", "{BACKSLASH}"]:
            t = t.replace(kw, "\\")
        for kw in ["{tab}", "{TAB}"]:
            t = t.replace(kw, "\t")
        for kw in ["{br}", "{break}", "{BREAK}", "{Break}", "{ BREAK }", "{ break }", "{BRAKE}", "{brake}"]:
            t = t.replace(kw, "\n")
        t = t.replace("\\n", "\n").replace("\r\n", "\n").replace("\\t", "\t")
        clean = re.sub(r'\[/?[a-zA-Z #0-9,._-]*\]', '', t)
        return clean.strip().lower().rstrip('.')

    def _check_correctness(self, user_input, correct_answer):
        """So sánh đáp án có hỗ trợ Fuzzy Matching."""
        # 1. Trực tiếp kiểm tra nếu phương án chọn trùng với đáp án chuẩn (hoặc bản đã format màu/ký tự của nó)
        if user_input == correct_answer or user_input == _replace_colors(correct_answer):
            return True, 1.0

        u_clean = self._clean_text(user_input)
        c_clean = self._clean_text(correct_answer)

        # 2. Kiểm tra khớp chính xác sau khi làm sạch
        if u_clean == c_clean:
            return True, 1.0

        # 3. So khớp với cả bản đã qua _replace_colors của đáp án chuẩn
        c_fmt_clean = self._clean_text(_replace_colors(correct_answer))
        if u_clean == c_fmt_clean:
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

    def _multi_shuffle(self, lst, times=25):
        """Trộn danh sách 20-30 lần để triệt tiêu tính định hình ban đầu."""
        if not lst: return lst
        for _ in range(times):
            random.shuffle(lst)
        return lst

    def _get_options(self, qid, q, a, data, all_ans, n_opts):
        tf_kws = getattr(_CONFIG, 'KEYWORD_BOOL', [])
        if any(kw.lower() in q.lower() for kw in tf_kws): return ["Đúng", "Sai"]
        
        # Thiết lập mục tiêu
        n_target = n_opts if (n_opts is not None and n_opts >= 1) else 4
        a_clean = self._clean_text(a)
        q_clean = self._clean_text(q)
        n_needed = n_target - 1
        
        pool = []

        # 2. Kiểm tra xem có phải dạng câu hỏi viết tắt/giải nghĩa (acronym) không
        is_acronym_q = any(kw.lower() in q.lower() for kw in getattr(_CONFIG, 'KEYWORD_Q_INPUT', []))
        target_initials = self._get_initials(a)

        # 3. Gom pool distractors cho câu hỏi acronym
        if is_acronym_q and len(target_initials) > 1:
            # Thu thập các từ xuất hiện trong câu hỏi q và target initials để cấm xuất hiện trong fake options
            q_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', q.lower()))
            q_tokens.add(target_initials.lower())
            blacklist = self._get_filter_wordbank()
            forbidden = q_tokens | blacklist

            # Tìm các đáp án THỰC TẾ có cùng initials trong data trước (loại trừ nếu chứa từ cấm hoặc từ trong câu hỏi)
            raw_pool = set(str(x[1]).strip() for x in all_ans 
                           if self._get_initials(str(x[1])) == target_initials and self._clean_text(str(x[1])) != a_clean)
            pool = []
            for item in raw_pool:
                words_in_item = set(re.findall(r'\b[a-zA-Z0-9]+\b', item.lower()))
                if not (words_in_item & forbidden):
                    pool.append(item)
            
            # Luôn cố gắng sinh thêm phương án giả để đạt độ đa dạng, sử dụng bank từ vựng và lịch sử
            acronym_data_source = self._get_all_dataset_answers() if (all_ans is data or len(all_ans) <= 1) else all_ans
            bank = self._get_word_bank(acronym_data_source)
            h_bank = self._get_history_word_bank()
            
            for _ in range(100):
                fake = self._generate_fake_phrase(a, bank, h_bank, forbidden_words=forbidden)
                if fake and self._clean_text(fake) != a_clean and fake not in pool:
                    fake_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', fake.lower()))
                    if not (fake_words & forbidden) and self._get_initials(fake) == target_initials:
                        pool.append(fake)
                if len(pool) >= 20: break
            
            pool = [o for o in pool if o not in ["Đúng", "Sai"]]
            if pool:
                self._multi_shuffle(pool, 25)
                chosen_distractors = random.sample(pool, min(len(pool), n_needed))
                opts = chosen_distractors + [a]
                self._multi_shuffle(opts, 25)
                return [_replace_colors(o) for o in dict.fromkeys(opts)]

        # 4. Loại bỏ đáp án a VÀ tất cả các đáp án khác của CÙNG CÂU HỎI q
        # (Để đảm bảo câu hỏi trắc nghiệm chỉ có 1 ĐÁP ÁN ĐÚNG và 3 ĐÁP ÁN SAI cùng dạng từ khóa)
        global_ans = self._get_all_dataset_answers() if (all_ans is data or len(all_ans) <= 1) else all_ans
        seen_answers = set()
        seen_answers.add(a_clean)
        pool_for_seen = global_ans if global_ans else all_ans
        for x in pool_for_seen:
            if self._clean_text(x[2]) == q_clean:
                seen_answers.add(self._clean_text(x[1]))

        chosen_distractors = []
        still_needed = n_needed
        target_len = len(str(a))

        # 5. Tầng 1 - Ưu tiên rút 3 ĐÁP ÁN SAI từ các câu hỏi KHÁC có CÙNG KEYWORD (filter_categories.txt)
        kws = self._get_kws()
        match_k = next((k for k in kws if k in q.lower()), None)
        if match_k and still_needed > 0:
            kw_answers = []
            # 5.1 Ưu tiên tìm trong bộ đề hiện tại (data)
            for x in data:
                ans_str = str(x[1]).strip()
                ans_clean = self._clean_text(ans_str)
                if match_k in str(x[2]).lower() and self._clean_text(x[2]) != q_clean and ans_clean not in seen_answers:
                    kw_answers.append(ans_str)
                    seen_answers.add(ans_clean)
            
            # 5.2 Nếu chưa đủ, tìm tiếp các câu hỏi có cùng KEYWORD trên toàn bộ hệ thống (global_ans)
            if len(kw_answers) < still_needed and global_ans:
                for x in global_ans:
                    ans_str = str(x[1]).strip()
                    ans_clean = self._clean_text(ans_str)
                    if match_k in str(x[2]).lower() and self._clean_text(x[2]) != q_clean and ans_clean not in seen_answers:
                        kw_answers.append(ans_str)
                        seen_answers.add(ans_clean)
            
            kw_answers = [o for o in kw_answers if o not in ["Đúng", "Sai"]]
            if kw_answers:
                self._multi_shuffle(kw_answers, 25)
                kw_answers.sort(key=lambda x: abs(len(str(x)) - target_len))
                candidate_kw = kw_answers[:max(100, still_needed * 3)]
                self._multi_shuffle(candidate_kw, 25)
                kw_sample = random.sample(candidate_kw, min(len(candidate_kw), still_needed))
                chosen_distractors.extend(kw_sample)
                still_needed = n_needed - len(chosen_distractors)

        # 6. Tầng 2 - Global Fallback: Lấy đáp án sai từ các câu hỏi KHÁC còn lại nếu chưa đủ phương án nhiễu
        if still_needed > 0:
            fallback_pool = []
            pool_source = global_ans if global_ans else all_ans
            for x in pool_source:
                ans_str = str(x[1]).strip()
                ans_clean = self._clean_text(ans_str)
                if self._clean_text(x[2]) != q_clean and ans_clean not in seen_answers:
                    fallback_pool.append(ans_str)
                    seen_answers.add(ans_clean)

            fallback_pool = [o for o in fallback_pool if o not in ["Đúng", "Sai"]]

            if fallback_pool:
                self._multi_shuffle(fallback_pool, 25)
                fallback_pool.sort(key=lambda x: abs(len(str(x)) - target_len))
                candidate_pool = fallback_pool[:max(100, still_needed * 3)]
                self._multi_shuffle(candidate_pool, 25)
                extra_sample = random.sample(candidate_pool, min(len(candidate_pool), still_needed))
                chosen_distractors.extend(extra_sample)

        # 7. Tổng hợp 1 ĐÁP ÁN ĐÚNG + 3 ĐÁP ÁN SAI, xáo trộn 25 lần và trả về
        opts = chosen_distractors + [a]
        self._multi_shuffle(opts, 25)
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
        elif chosen == "[HẾT GIỜ]":
            p = Text.from_markup("\n[bold white on red] ⏰ HẾT THỜI GIAN LÀM BÀI! [/] Đáp án đúng: ")
            p.append(Text.from_markup(a, style="bold yellow"))
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

    def _persist_config_value(self, key, val):
        """Lưu giá trị cấu hình vào file settings.json và config.py (nếu có)."""
        import json
        setattr(_CONFIG, key, val)
        try:
            settings_path = "settings.json"
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings_data = json.load(f)
            else:
                settings_data = {}
            settings_data[key] = val
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=4)
        except: pass

        path = "config.py"
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(path, "w", encoding="utf-8") as f:
                for line in lines:
                    if re.match(rf"^\s*{key}\s*=", line):
                        comment = line[line.find("#"):].strip() if "#" in line else ""
                        f.write(f"{key} = {repr(val)} {'# ' + comment if comment else ''}\n".replace(" # #", " #"))
                    else:
                        f.write(line)
        except: pass

    def get_difficulty(self):
        while True:
            cur_limit = getattr(_CONFIG, 'QUIZ_TIME_LIMIT', 15)
            time_str = f"{cur_limit}s" if cur_limit > 0 else "Vô tận (0s)"
            rating_enabled = getattr(_CONFIG, 'ENABLE_DIFFICULTY_RATING', False)
            rating_str = "[bold green]Bật (1)[/]" if rating_enabled else "[bold red]Tắt (0)[/]"
            edit_enabled = getattr(_CONFIG, 'EDIT_AFTER_ANSWER', False)
            edit_str = "[bold green]Bật (1)[/]" if edit_enabled else "[bold red]Tắt (0)[/]"

            table = Table(title="⚡ CHỌN MỨC ĐỘ THỬ THÁCH", box=box.SIMPLE)
            table.add_column("Key", style="bold cyan", justify="right")
            table.add_column("Chế độ", style="white")
            modes = [
                ("1", "[green]Dễ (10 câu, 3 đáp án)[/]"),
                ("2", "[yellow]Vừa (20 câu, 4 đáp án)[/]"),
                ("3", "[red]Khó (50 câu, 6 đáp án)[/]"),
                ("4", "[magenta]Hardcore (100 câu, 10 đáp án)[/]"),
                ("5", "Sinh tồn (Sai là dừng, 4 đáp án)"),
                ("6", "Tùy chỉnh (Tự thiết lập)"),
                ("7", f"[cyan]Thời gian trả lời: [bold yellow]{time_str}[/] [dim](0 vô tận, default = 15s)[/]"),
                ("8", f"[cyan]Đánh giá độ khó: {rating_str} [dim](0 = tắt, 1 = bật)[/]"),
                ("9", f"[cyan]Chỉnh sửa sau khi trả lời: {edit_str} [dim](0 = tắt, 1 = bật)[/]")
            ]
            for k, v in modes: table.add_row(k, v)
            console.print(table)
            ch = inp.input_difficulty_mode()
            
            if ch == 7:
                val = _safe_input(f"⏱️ Nhập thời gian trả lời mỗi câu (0 vô tận, Enter = 15s, hiện tại: {cur_limit}s): ")
                if val is not None:
                    val_str = str(val).strip()
                    if val_str == "":
                        _CONFIG.QUIZ_TIME_LIMIT = 15
                    elif val_str.isdigit():
                        _CONFIG.QUIZ_TIME_LIMIT = int(val_str)
                    
                    self._persist_config_value("QUIZ_TIME_LIMIT", _CONFIG.QUIZ_TIME_LIMIT)
                    console.print(f"[bold green]✅ Đã đặt thời gian: {f'{_CONFIG.QUIZ_TIME_LIMIT}s' if _CONFIG.QUIZ_TIME_LIMIT > 0 else 'Vô tận'}[/]\n")
                continue

            if ch == 8:
                curr_status = "1" if rating_enabled else "0"
                val = _safe_input(f"⭐ Đánh giá độ khó (0 = tắt, 1 = bật, Enter đổi trạng thái, hiện tại: {curr_status}): ")
                if val is not None:
                    val_str = str(val).strip()
                    if val_str == "0":
                        _CONFIG.ENABLE_DIFFICULTY_RATING = False
                    elif val_str == "1":
                        _CONFIG.ENABLE_DIFFICULTY_RATING = True
                    elif val_str == "":
                        _CONFIG.ENABLE_DIFFICULTY_RATING = not rating_enabled
                    
                    self._persist_config_value("ENABLE_DIFFICULTY_RATING", _CONFIG.ENABLE_DIFFICULTY_RATING)
                    console.print(f"[bold green]✅ Đã {'bật' if _CONFIG.ENABLE_DIFFICULTY_RATING else 'tắt'} đánh giá độ khó.[/]\n")
                continue

            if ch == 9:
                curr_status = "1" if edit_enabled else "0"
                val = _safe_input(f"✏️ Chỉnh sửa sau khi trả lời (0 = tắt, 1 = bật, Enter đổi trạng thái, hiện tại: {curr_status}): ")
                if val is not None:
                    val_str = str(val).strip()
                    if val_str == "0":
                        _CONFIG.EDIT_AFTER_ANSWER = False
                    elif val_str == "1":
                        _CONFIG.EDIT_AFTER_ANSWER = True
                    elif val_str == "":
                        _CONFIG.EDIT_AFTER_ANSWER = not edit_enabled

                    self._persist_config_value("EDIT_AFTER_ANSWER", _CONFIG.EDIT_AFTER_ANSWER)
                    console.print(f"[bold green]✅ Đã {'bật' if _CONFIG.EDIT_AFTER_ANSWER else 'tắt'} chỉnh sửa sau khi trả lời.[/]\n")
                continue

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
            
            # Thuật toán Ưu tiên Câu hỏi Sai:
            # Các câu đã từng làm sai (w > 0) và chưa đạt Hiệu số +10 (diff < 10)
            # sẽ được tự động đưa vào thử thách, hiệu số càng âm càng được ưu tiên lên đầu
            mistakes = _get_mistake_history_data()
            mistake_items, normal_items = [], []

            for row in data:
                q_text = _replace_colors(row[2])
                m_info = mistakes.get(q_text)
                if not m_info:
                    clean_q = re.sub(r'\[/?[a-zA-Z #0-9,._-]*\]', '', str(row[2])).strip().lower()
                    for mk, mv in mistakes.items():
                        clean_mk = re.sub(r'\[/?[a-zA-Z #0-9,._-]*\]', '', str(mk)).strip().lower()
                        if clean_q == clean_mk:
                            m_info = mv
                            break

                if m_info and m_info[0] > 0:
                    w, c = m_info[0], m_info[1]
                    diff = c - w
                    if diff < 10:
                        mistake_items.append((diff, row))
                        continue
                normal_items.append(row)

            # Sắp xếp nhóm câu sai: hiệu số càng âm càng ưu tiên lên đầu
            random.shuffle(mistake_items)
            mistake_items.sort(key=lambda x: x[0])
            sorted_mistake_rows = [x[1] for x in mistake_items]

            # Xáo trộn nhóm câu bình thường và áp dụng đa dạng hóa keyword
            self._multi_shuffle(normal_items, 25)
            kws = self._get_kws()
            limit = getattr(_CONFIG, 'MAX_SAME_KEYWORD_PER_QUIZ', 5)
            filtered_normal, overflow, kw_counts = [], [], {}
            for row in normal_items:
                match_k = next((k for k in kws if k in str(row[2]).lower()), None)
                if match_k:
                    count = kw_counts.get(match_k, 0)
                    if count < limit:
                        filtered_normal.append(row)
                        kw_counts[match_k] = count + 1
                    else:
                        overflow.append(row)
                else:
                    filtered_normal.append(row)

            available_normal = filtered_normal + overflow

            # Ghép pool: ưu tiên tối đa nhóm câu sai chưa đạt +10, phần còn lại lấy từ câu bình thường
            if max_qs:
                if len(sorted_mistake_rows) >= max_qs:
                    pool = sorted_mistake_rows[:max_qs]
                else:
                    needed = max_qs - len(sorted_mistake_rows)
                    pool = sorted_mistake_rows + available_normal[:needed]
            else:
                pool = sorted_mistake_rows + available_normal

            self._multi_shuffle(pool, 25)
            results, score = [], 0

            try:
                for i, (qid, a, q, d, r) in enumerate(pool, 1):
                    ok, chosen, info = self._ask_question(i, len(pool), qid, a, q, d, r, data, n_opts, score)
                    if chosen == "EXIT_SIGNAL": break
                    
                    if ok: score += 1
                    results.append({"index": i, "question": info[0], "correct": info[1], "hint": info[2], "desc": info[3], "ok": ok})
                    self._feedback(ok, chosen, *info, qid)

                    if not self._wait_next(qid, ok=ok, current_item=(qid, a, q, d, r)): break

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
        time_limit = getattr(_CONFIG, 'QUIZ_TIME_LIMIT', 0)
        console.rule(f"[bold white on blue]QUIZ [/] [cyan]{i}/{total}[/] │ [green]Score: {current_score}[/]")
        
        q_d, a_d, d_d, r_d = map(_replace_colors, (q, a, d or "", r or ""))
        # Sử dụng Text.from_markup để style bold white bao phủ toàn bộ question kể cả khi có tag reset
        console.print("\n", Text.from_markup(q_d, style="bold white"), "\n")
        
        # Chế độ trắc nghiệm (Multiple Choice) truyền thống
        opts = self._get_options(qid, q, a, data, data, n_opts)
        mapping = {k: v for k, v in zip(string.ascii_uppercase[:len(opts)], opts)}
        for k, v in mapping.items():
            # Căn lề các dòng tiếp theo trong phương án nếu có xuống dòng (\n từ {BREAK} hoặc \n)
            v_indented = v.replace("\n", "\n      ")
            console.print(Text.from_markup(f"  [bold cyan]({k})[/] ").append(Text.from_markup(v_indented)))

        while True:
            u = inp.input_quiz_choice(mapping, has_hint=bool(d))
            if u == "EXIT_SIGNAL": return False, "EXIT_SIGNAL", None
            if u == "TIMEOUT_SIGNAL":
                console.print(f"\n[bold red]⏰ Bạn không kịp đưa ra đáp án trong {time_limit} giây quy định![/]")
                return False, "[HẾT GIỜ]", (q_d, a_d, d_d, r_d, 0.0)
            if u == "HINT_SIGNAL":
                console.print(f"[yellow]💡 Gợi ý: {d_d}[/]")
                continue
            
            chosen = mapping[u]
            ok, ratio = self._check_correctness(chosen, a)
            return ok, chosen, (q_d, a_d, d_d, r_d, ratio)

    def _wait_next(self, qid=None, ok=True, current_item=None):
        if getattr(_CONFIG, 'EDIT_AFTER_ANSWER', False) and qid and current_item:
            try:
                from src.process_flashcard import FlashcardManager
                fm = FlashcardManager()
                # current_item = (qid, a, q, d, r)
                _, a_curr, q_curr, d_curr, r_curr = current_item
                console.print("\n[bold cyan]✏️ Chỉnh sửa câu hỏi vừa làm (Nhấn Enter để giữ nguyên):[/]")
                new_q = _safe_input(f"❓ Câu hỏi ({q_curr}): ")
                if new_q == "": new_q = None
                new_a = _safe_input(f"✅ Đáp án chuẩn ({a_curr}): ")
                if new_a == "": new_a = None
                new_d = _safe_input(f"💡 Gợi ý ({d_curr}): ")
                if new_d == "": new_d = None
                new_r = _safe_input(f"📖 Mô tả ({r_curr}): ")
                if new_r == "": new_r = None

                if any(x is not None for x in [new_q, new_a, new_d, new_r]):
                    updated, updated_row = fm.update_question_by_id(qid, new_q=new_q, new_a=new_a, new_d=new_d, new_r=new_r)
                    if updated:
                        console.print("[bold green]✨ Đã cập nhật thành công câu hỏi![/]\n")
                    else:
                        console.print("[yellow]⚠️ Không tìm thấy file chứa ID câu hỏi để cập nhật.[/]\n")
                else:
                    console.print("[dim]⏩ Giữ nguyên, không có thay đổi.[/]\n")
            except Exception as e:
                console.print(f"[red]❌ Lỗi khi chỉnh sửa câu hỏi: {e}[/]\n")

        if getattr(_CONFIG, 'ENABLE_DIFFICULTY_RATING', False):
            val = inp.input_difficulty_rating()
            if qid and val:
                log_action(f"RATING:{qid}", f"Difficulty: {val}")
                log_difficulty(qid, val)
            return True

        # Nếu vừa trả lời sai, dừng 1s cho người chơi kịp nhìn đáp án đúng
        if not ok:
            time.sleep(1.0)

        # Hiệu ứng chuyển câu 3... 2... 1... 💥 BÙM!
        steps = [("3...", 0.45), ("2...", 0.45), ("1...", 0.45), ("💥 BÙM!", 0.25)]
        for s_text, dur in steps:
            console.print(f"\r[dim]⏳ Chuyển câu trong:[/] [bold yellow]{s_text}[/] ", end="")
            end_t = time.time() + dur
            skipped = False
            while time.time() < end_t:
                if HAS_MSVCRT and msvcrt.kbhit():
                    msvcrt.getwch()
                    skipped = True
                    break
                time.sleep(0.03)
            if skipped:
                console.print("\r[bold magenta]🚀 💥 BÙM![/]                   ")
                time.sleep(0.15)
                break
        console.print("")
        return True