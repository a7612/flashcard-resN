import os
import random

QUESTIONS_DIR = "questions"   # 📂 Thư mục chứa file câu hỏi
MAX_QUESTIONS = 20            # 🎯 Số câu hỏi tối đa mỗi lần chơi

def clearsrc():
    # Nếu là Windows thì dùng 'cls', còn Linux/macOS thì dùng 'clear'
    os.system('cls' if os.name == 'nt' else 'clear')

class QuizGame:
    def __init__(self, questions_dir=QUESTIONS_DIR):
        self.questions_dir = questions_dir
        os.makedirs(self.questions_dir, exist_ok=True)

    # ================= FILE HELPERS =================
    def list_files(self, show_count=True):
        """📂 Liệt kê các file câu hỏi (.txt) trong thư mục questions"""
        files = [f for f in os.listdir(self.questions_dir) if f.endswith(".txt")]
        if not files:
            print("⚠️ Không có file câu hỏi nào.")
            return []
        if show_count:
            print("\n📂 Danh sách file:")
            for i, f in enumerate(files, 1):
                path = os.path.join(self.questions_dir, f)
                count = sum(1 for line in open(path, "r", encoding="utf-8") if line.strip())
                print(f" {i}) {f}  –  {count} câu hỏi")
        return files

    def choose_file(self, action="chọn"):
        """👉 Cho phép chọn 1 file theo số thứ tự"""
        files = self.list_files()
        if not files:
            return None
        idx = input(f"\n👉 Nhập số file để {action}: ").strip()
        if not idx.isdigit() or not (1 <= int(idx) <= len(files)):
            print("⚠️ Lựa chọn không hợp lệ.")
            return None
        return os.path.join(self.questions_dir, files[int(idx) - 1])

    def load_questions_from_file(self, filepath):
        """📖 Đọc dữ liệu câu hỏi từ file (định dạng: id;answer;question)"""
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as fh:
            return [
                (qid, ans.strip(), q.strip())
                for line in fh if (parts := line.strip().split(";", 2)) and len(parts) == 3
                for qid, ans, q in [parts]
            ]

    def save_questions(self, filepath, questions):
        """💾 Ghi danh sách câu hỏi ra file (sort theo đáp án, re-index ID)"""
        questions.sort(key=lambda x: x[2].lower())
        questions.sort(key=lambda x: x[1].lower())
        with open(filepath, "w", encoding="utf-8") as fh:
            for i, (_, ans, q) in enumerate(questions, 1):
                fh.write(f"{i};{ans};{q}\n")

    def show_questions(self, filepath):
        """📋 Hiển thị toàn bộ câu hỏi trong file"""
        questions = self.load_questions_from_file(filepath)
        if not questions:
            print("❌ File trống.")
            return []
        print("\n📋 Danh sách câu hỏi:")
        for qid, ans, q in questions:
            print(f" {qid}) {q}   [Đáp án: {ans}]")
        return questions

    # ================= ADD / DELETE =================
    def add_question(self):
        """➕ Thêm câu hỏi mới vào 1 file đã chọn"""
        filepath = self.choose_file("thêm")
        if not filepath:
            return
        questions = self.load_questions_from_file(filepath)
        self.show_questions(filepath)

        q = input("\n❓ Nhập câu hỏi: ").strip()
        a = input("✅ Nhập đáp án đúng: ").strip()
        if not q or not a:
            print("⚠️ Câu hỏi/đáp án không được để trống.")
            return

        questions.append((str(len(questions) + 1), a, q))
        self.save_questions(filepath, questions)
        print(f"\n➕ Đã thêm câu hỏi mới vào file **{os.path.basename(filepath)}**.")

    def delete_question(self):
        """🗑️ Xoá câu hỏi theo ID"""
        filepath = self.choose_file("xoá")
        if not filepath:
            return
        questions = self.show_questions(filepath)
        if not questions:
            return

        del_id = input("\n👉 Nhập ID để xoá: ").strip()
        if not del_id.isdigit() or all(q[0] != del_id for q in questions):
            print("⚠️ ID không hợp lệ.")
            return

        new_questions = [q for q in questions if q[0] != del_id]
        self.save_questions(filepath, new_questions)
        print(f"\n🗑️ Đã xoá câu hỏi ID {del_id} trong file **{os.path.basename(filepath)}**.")

    # ================= QUIZ HELPERS =================
    def _build_options(self, correct, pool_answers, num_choices):
        """🔀 Sinh ngẫu nhiên đáp án (loại bỏ 'Đúng/Sai' cho câu hỏi thường)"""
        # bỏ True/False/Đúng/Sai khỏi pool để không generate nhầm
        pool = list(set(pool_answers) - {correct, "Đúng", "Sai", "dung", "sai"})
        wrongs = random.sample(pool, min(num_choices - 1, len(pool)))
        opts = wrongs + [correct]
        random.shuffle(opts)
        return opts

    def _prepare_quiz_pool(self, questions):
        """📊 Lấy ra danh sách câu hỏi để chơi (tối đa MAX_QUESTIONS)"""
        if not questions:
            return []
        if len(questions) >= MAX_QUESTIONS:
            return random.sample(questions, MAX_QUESTIONS)
        return (questions * ((MAX_QUESTIONS // len(questions)) + 1))[:MAX_QUESTIONS]

    def _check_answer(self, choice, mapping, correct):
        """✔️ Kiểm tra câu trả lời"""
        picked = mapping.get(choice.lower(), choice.strip().lower())
        if picked.lower() == correct.lower():
            clearsrc()
            print("✅ Chính xác!\n")
            return True
        else:
            clearsrc()
            print(f"❌ Sai rồi! Đáp án đúng là: {correct}\n")
            return False

    def _play_quiz(self, questions, num_choices=4):
        """🎮 Chơi quiz theo danh sách câu hỏi"""
        if not questions:
            print("❌ Không có câu hỏi.")
            return

        all_answers = [ans for _, ans, _ in questions]
        quiz_pool = self._prepare_quiz_pool(questions)
        score = 0

        for idx, (_, correct, q) in enumerate(quiz_pool, 1):
            # 👉 Nếu câu hỏi là dạng True/False → chỉ hiện Đúng/Sai
            
            if "nhận định đúng sai" in q.lower():
                opts = ["Đúng", "Sai"]
            else:
                opts = self._build_options(correct, all_answers, num_choices)
            
            letters = [chr(ord("a") + i) for i in range(len(opts))]
            mapping = {letters[i]: opts[i] for i in range(len(opts))}

            # --- Xuất câu hỏi + đáp án ---
            
            print(f"\n{idx}. ❓ {q}\n")
            for l in letters:
                print(f"   {l}) {mapping[l]}")

            # --- Input ---
            if "nhận định đúng sai" in q.lower():
                choice = input("\n👉 Chọn (a/b hoặc gõ Đúng/Sai): ").strip()
            else:
                choice = input("\n👉 Chọn (a/b/c... hoặc gõ đáp án): ").strip()

            if self._check_answer(choice, mapping, correct):
                score += 1

        # --- Kết quả ---
        percent = (score / len(quiz_pool)) * 100
        print("\n🌟 Tổng kết 🌟")
        print(f"   Điểm số: {score}/{len(quiz_pool)}")
        print(f"   Tỉ lệ chính xác: {percent:.1f}%\n")

    # ================= PLAY MODES =================
    def play_file(self):
        """🎯 Chơi quiz theo 1 file"""
        filepath = self.choose_file("chơi")
        if filepath:
            self._play_quiz(self.load_questions_from_file(filepath), num_choices=4)

    def play_all(self):
        """🌍 Chơi quiz toàn bộ file"""
        files = self.list_files(show_count=False)
        all_questions = []
        for f in files:
            all_questions.extend(self.load_questions_from_file(os.path.join(self.questions_dir, f)))
        self._play_quiz(all_questions, num_choices=8)

    # ================= MAIN MENU =================
    def menu(self):
        """📌 Menu chính"""
        while True:
            print("\n===== 📚 QUIZ GAME =====")
            print("1. 🎯 Chơi theo bộ")
            print("2. 🌍 Chơi toàn bộ")
            print("3. ➕ Thêm câu hỏi")
            print("4. 🗑️ Xoá câu hỏi")
            print("0. 🚪 Thoát")
            choice = input("👉 Chọn: ").strip()

            match choice:
                case "1": self.play_file()
                case "2": self.play_all()
                case "3": self.add_question()
                case "4": self.delete_question()
                case "0": print("👋 Tạm biệt!"); break
                case _: print("⚠️ Lựa chọn không hợp lệ.")


# ================= RUN =================
if __name__ == "__main__":
    QuizGame().menu()
