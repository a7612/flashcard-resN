import os
import random
import string

# ====== CONFIG ======
QUESTIONS_DIR = "questions"
MAX_NORMAL_QUESTIONS = 20   # số câu hỏi khi chơi 1 file
MAX_ALL_QUESTIONS = 50      # số câu hỏi khi chơi tất cả

MAX_GENERATE_NORMAL_QUESTIONS = 4   # số đáp án khi chơi 1 file
MAX_GENERATE_ALL_QUESTIONS = 12     # số đáp án khi chơi all


def clearsrc():
    """Xoá màn hình console (tương thích Windows/Linux)."""
    os.system("cls" if os.name == "nt" else "clear")


class QuizGame:
    def __init__(self, qdir=QUESTIONS_DIR):
        """Khởi tạo game, tạo thư mục chứa câu hỏi nếu chưa có."""
        self.qdir = qdir
        os.makedirs(self.qdir, exist_ok=True)

    # ========== UTILS ==========
    def _files(self):
        """Lấy danh sách tất cả file .txt trong thư mục câu hỏi."""
        return [f for f in os.listdir(self.qdir) if f.endswith(".txt")]

    def _list_files(self, show=True):
        """Liệt kê danh sách file + số lượng câu hỏi trong mỗi file."""
        files = self._files()
        if not files:
            print("⚠️ Không có file câu hỏi.")
            return []
        if show:
            print("\n📂 Danh sách file:")
            for i, f in enumerate(files, 1):
                path = os.path.join(self.qdir, f)
                count = sum(1 for _ in open(path, encoding="utf-8"))
                print(f" {i}) {f} – {count} câu hỏi")
        return files

    def _choose_file(self, action="chọn"):
        """Cho người dùng chọn 1 file dựa trên danh sách hiện có."""
        files = self._list_files()
        if not files:
            return None
        idx = input(f"\n👉 Nhập số file để {action}: ").strip()
        return os.path.join(self.qdir, files[int(idx) - 1]) if idx.isdigit() and 1 <= int(idx) <= len(files) else None

    def _load(self, path):
        """Đọc dữ liệu từ file: mỗi dòng dạng 'ID;Đáp án;Câu hỏi'."""
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [line.strip().split(";", 2) for line in f if ";" in line]

    def _save(self, path, data):
        """Ghi lại dữ liệu vào file, sắp xếp theo đáp án + câu hỏi."""
        with open(path, "w", encoding="utf-8") as f:
            for i, (_, a, q) in enumerate(sorted(data, key=lambda x: (x[1].lower(), x[2].lower())), 1):
                f.write(f"{i};{a};{q}\n")

    def _show(self, path):
        """Hiển thị danh sách câu hỏi trong file."""
        data = self._load(path)
        if not data:
            print("❌ File trống.")
            return []
        print("\n📋 Câu hỏi:")
        for i, (qid, a, q) in enumerate(data, 1):
            print(f" {i}) {q}   [Đáp án: {a}]")
        print(" exit() 🔙 Quay lại")
        return data

    # ========== QUESTION CRUD ==========
    def _crud(self, mode):
        """Thêm/Xoá/Sửa câu hỏi trong file."""
        path = self._choose_file(mode)
        if not path:
            return
        data = self._show(path)

        if mode == "thêm":
            while True:
                q = input("\n❓ Nhập câu hỏi (hoặc gõ exit() để quay lại): ").strip()
                if q.lower() == "exit()":
                    break
                a = input("✅ Nhập đáp án: ").strip()
                if q and a:
                    data.append((str(len(data) + 1), a, q))
                    self._save(path, data)
                    clearsrc()
                    print("➕ Đã thêm câu hỏi mới.")
                    self._show(path)

        elif mode == "xoá":
            while True:
                idx = input("\n🗑️ Nhập ID câu hỏi cần xoá (hoặc gõ exit() để quay lại): ").strip()
                if idx.lower() == "exit()":
                    break
                if idx.isdigit() and 1 <= int(idx) <= len(data):
                    qid, ans, ques = data[int(idx) - 1]
                    confirm = input(f"❓ Xác nhận xoá \"{ques}\" (y/n): ").strip().lower()
                    if confirm == "y":
                        data.pop(int(idx) - 1)
                        self._save(path, data)
                        clearsrc()
                        print(f"🗑️ Đã xoá: \"{ques}\" [Đáp án: {ans}]")
                        self._show(path)

        elif mode == "sửa":
            while True:
                idx = input("\n✏️ Nhập ID câu hỏi cần sửa (hoặc gõ exit() để quay lại): ").strip()
                if idx.lower() == "exit()":
                    break
                if idx.isdigit() and 1 <= int(idx) <= len(data):
                    new_q = input("❓ Nhập câu hỏi mới: ").strip()
                    new_a = input("✅ Nhập đáp án mới: ").strip()
                    if new_q and new_a:
                        data[int(idx) - 1] = (str(idx), new_a, new_q)
                        self._save(path, data)
                        clearsrc()
                        print("✏️ Đã cập nhật câu hỏi.")
                        self._show(path)

    def manage_questions(self):
        """Menu quản lý câu hỏi (CRUD)."""
        while True:
            clearsrc()
            print("\n===== 📋 QUẢN LÝ CÂU HỎI =====")
            print(" 1) ➕ Thêm câu hỏi")
            print(" 2) 🗑️ Xoá câu hỏi")
            print(" 3) ✏️ Sửa câu hỏi")
            print(" Hoặc nhập exit() 🔙 quay lại.")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch == "1": self._crud("thêm")
            elif ch == "2": self._crud("xoá")
            elif ch == "3": self._crud("sửa")
            elif ch.lower() == "exit()":
                break
            else:
                print("⚠️ Lựa chọn không hợp lệ, thử lại.")

    # ========== FILE CRUD ==========
    def manage_files(self):
        """Menu quản lý tệp tin: tạo, xoá, đổi tên file."""
        while True:
            clearsrc()
            print("\n===== 📂 QUẢN LÝ TỆP TIN =====")
            print(" 1) ➕ Tạo file")
            print(" 2) 🗑️ Xoá file")
            print(" 3) ✏️ Đổi tên file")
            print(" Hoặc nhập exit() 🔙 quay lại.")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch == "1":
                name = input("📄 Nhập tên file mới: ").strip()
                if name:
                    filepath = os.path.join(self.qdir, f"{name}.txt")
                    if os.path.exists(filepath):
                        print("⚠️ File đã tồn tại.")
                    else:
                        open(filepath, "w", encoding="utf-8").close()
                        print(f"✅ Đã tạo {name}.txt")
            elif ch == "2":
                path = self._choose_file("xoá")
                if path:
                    confirm = input(f"❓ Bạn có chắc muốn xoá file {os.path.basename(path)} (y/n): ").strip().lower()
                    if confirm == "y":
                        os.remove(path)
                        print(f"🗑️ File {path} đã được xoá.")
            elif ch == "3":
                path = self._choose_file("đổi tên")
                if path:
                    new = input("✏️ Nhập tên mới: ").strip()
                    if new:
                        os.rename(path, os.path.join(self.qdir, f"{new}.txt"))
                        print("✅ Đã đổi tên file.")
            elif ch.lower() == "exit()":
                break
            else:
                print("⚠️ Lựa chọn không hợp lệ.")

    # ========== QUIZ ==========
    def _options(self, correct, pool, n):
        """Sinh ra các lựa chọn trắc nghiệm, tránh lặp lại đáp án đúng."""
        pool = list(set(pool) - {correct, "Đúng", "Sai"})
        return random.sample(pool, min(n - 1, len(pool))) + [correct]

    def play_all(self):
        data = []
        for f in self._files():
            data += self._load(os.path.join(self.qdir, f))
        self._quiz(data, n_opts=MAX_GENERATE_ALL_QUESTIONS, max_qs=MAX_ALL_QUESTIONS)

    def _quiz(self, data, n_opts=None, max_qs=None):
        """Chạy quiz với danh sách câu hỏi cho trước."""
        if not data:
            return print("❌ Không có câu hỏi.")

        pool = data if max_qs is None else (data * ((max_qs // len(data)) + 1))[:max_qs]
        all_ans = [a for _, a, _ in data]
        score, wrong = 0, 0

        for i, (_, a, q) in enumerate(pool, 1):
            print("\n" + "="*40)
            print(f"{i}. ❓ {q}")
            opts = ["Đúng", "Sai"] if "nhận định đúng sai" in q.lower() else self._options(a, all_ans, n_opts)
            random.shuffle(opts)
            letters = string.ascii_lowercase[:len(opts)]
            mapping = dict(zip(letters, opts))

            for k, v in mapping.items():
                print(f"  {k}) {v}")

            pick = input("👉 Nhập đáp án: ").lower()
            if mapping.get(pick, "").lower() == a.lower():
                score += 1
                print("✅ Chính xác!")
            else:
                wrong += 1
                print(f"❌ Sai! Đáp án đúng: {a}")

        print("\n" + "="*50+"\n" + "="*50)
        print("🎯 Hoàn thành Quiz!")
        print(f"✅ Đúng: {score}")
        print(f"❌ Sai: {wrong}")
        print(f"📊 Kết quả: {score}/{len(pool)} đúng")
        print(f"🔥 Tỉ lệ chính xác: {score/len(pool)*100:.1f}%")

    def play_file(self):
        """Chơi quiz từ một file cụ thể."""
        path = self._choose_file("chơi")
        if path:
            self._quiz(self._load(path),
                    n_opts=MAX_GENERATE_NORMAL_QUESTIONS,
                    max_qs=MAX_NORMAL_QUESTIONS)

    # ========== MENU ==========
    def menu(self):
        """Menu chính của chương trình."""
        actions = {
            "1": self.play_file,
            "2": self.play_all,
            "3": self.manage_questions,
            "4": self.manage_files,
            "0": lambda: print("👋 Tạm biệt!"),
        }
        while True:
            print("\n===== 📚 QUIZ GAME =====")
            print(" 1) 🎯 Chơi theo bộ")
            print(" 2) 🌍 Chơi toàn bộ")
            print(" 3) 📋 Quản lý câu hỏi")
            print(" 4) 📂 Quản lý tệp tin")
            print(" 0) 🚪 Thoát")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch == "0":
                break
            (actions.get(ch) or (lambda: print("⚠️ Sai lựa chọn.")))()


if __name__ == "__main__":
    QuizGame().menu()
