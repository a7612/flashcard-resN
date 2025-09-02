import os
import random
import string
import csv
import datetime
import getpass
from config import *

LOG_DIR = "logs"
EXPORT_DIR = "exports"

# Tạo thư mục logs/ và exports/ nếu chưa tồn tại
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(QUESTIONS_DIR, exist_ok=True)


def timestamp_now():
    """Chuỗi timestamp để đặt tên file/log."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def current_user():
    """Ai đang chạy chương trình (dùng để log)."""
    try:
        return getpass.getuser()
    except Exception:
        return "unknown_user"


def log_action(action: str, detail: str = ""):
    """Ghi log đơn giản: timestamp | user | action | detail."""
    fn = os.path.join(LOG_DIR, "actions.log")
    ts = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    user = current_user()
    line = f"{ts} | {user} | {action} | {detail}\n"
    with open(fn, "a", encoding="utf-8") as f:
        f.write(line)


class QuizGame:
    """Class quản lý toàn bộ game + CRUD + logging + export."""

    def __init__(self, qdir=QUESTIONS_DIR):
        self.qdir = qdir
        os.makedirs(self.qdir, exist_ok=True)

    # ====== UTILS ======
    @staticmethod
    def clearsrc():
        """Xoá màn hình console (tương thích Windows/Linux)."""
        os.system("cls" if os.name == "nt" else "clear")

    def _files(self):
        """Trả về danh sách file .txt trong thư mục câu hỏi."""
        return [f for f in os.listdir(self.qdir) if f.endswith(".txt")]

    def _list_files(self, show=True):
        """Liệt kê file + số lượng câu hỏi trong mỗi file."""
        files = self._files()
        if not files:
            print("⚠️ Không có file câu hỏi.")
            return []
        if show:
            print(f"{BRIGHT_GREEN}\n📂 Danh sách file:{RESET}")
            for i, f in enumerate(files, 1):
                path = os.path.join(self.qdir, f)
                try:
                    count = sum(1 for _ in open(path, encoding="utf-8"))
                except Exception:
                    count = 0
                print(f" {i:>2}) {f:<25} | {count} câu hỏi")
        return files

    def _choose_file(self, action="chọn"):
        """Cho người dùng chọn file dựa trên danh sách hiện có."""
        files = self._list_files()
        if not files:
            return None
        idx = input(f"\n👉 Nhập số file để {action}: ").strip()
        if idx.isdigit() and 1 <= int(idx) <= len(files):
            return os.path.join(self.qdir, files[int(idx) - 1])
        print("⚠️ Chọn không hợp lệ.")
        return None

    def _load(self, path):
        """Đọc file -> list các tuple (id, answer, question, desc)."""
        if not os.path.exists(path):
            return []
        data = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(";", 3)
                if len(parts) == 3:
                    parts.append("")  # rỗng desc nếu file cũ
                data.append(parts)
        return data

    def _save(self, path, data):
        """
        Lưu data vào file với format: id;answer;question;desc
        Sắp xếp theo đáp án + câu hỏi để ổn định.
        """
        with open(path, "w", encoding="utf-8") as f:
            for i, (_, a, q, d) in enumerate(sorted(data, key=lambda x: (x[1].lower(), x[2].lower())), 1):
                f.write(f"{i};{a};{q};{d}\n")

    def _show(self, path):
        """Hiển thị danh sách câu hỏi trong file, trả về data list."""
        data = self._load(path)
        if not data:
            print("❌ File trống.")
            return []
        print("\n📋 DANH SÁCH CÂU HỎI:")
        for i, (qid, a, q, d) in enumerate(data, 1):
            print(f"{BRIGHT_CYAN}{i:>2}) {q}{RESET}")
            print(f"   {GREEN}➤ Đáp án: {a}{RESET}")
            if d:
                print(f"   {YELLOW}💡 Mô tả: {d}{RESET}")
        return data

    # ====== CRUD ======
    def _crud(self, mode):
        """
        Thêm / Xoá / Sửa  ... Ghi log những hành động này vào logs/actions.log
        mode: "thêm", "xoá", "sửa", "sửaQ", "sửaA", "sửaD"
        """
        path = self._choose_file(mode)
        if not path:
            return
        data = self._show(path)

        if mode == "thêm":
            while True:
                q = input("\n❓ Nhập câu hỏi (exit() để thoát): ").strip()
                if q.lower() == "exit()":
                    break
                a = input("✅ Đáp án: ").strip()
                d = input("💡 Mô tả (có thể bỏ trống): ").strip()
                if q and a:
                    data.append((str(len(data) + 1), a, q, d))
                    self._save(path, data)
                    log_action("ADD_Q", f"{os.path.basename(path)} | Q: {q} | A: {a}")
                    self.clearsrc()
                    print("➕ Đã thêm câu hỏi mới.")
                    self._show(path)

        elif mode == "xoá":
            while True:
                idx = input("\n🗑️ Nhập ID cần xoá (exit() để thoát): ").strip()
                if idx.lower() == "exit()":
                    break
                if idx.isdigit() and 1 <= int(idx) <= len(data):
                    qid, ans, ques, desc = data[int(idx) - 1]
                    if input(f"❓ Xác nhận xoá \"{ques}\" (y/n): ").lower() == "y":
                        removed = data.pop(int(idx) - 1)
                        self._save(path, data)
                        log_action("DEL_Q", f"{os.path.basename(path)} | Q: {removed[2]} | A: {removed[1]}")
                        self.clearsrc()
                        print(f"🗑️ Đã xoá: \"{ques}\" [Đáp án: {ans}]")
                        self._show(path)

        elif mode.startswith("sửa"):
            field_map = {"sửaQ": 2, "sửaA": 1, "sửaD": 3}
            if mode == "sửa":
                idx = input("\n✏️ Nhập ID cần sửa toàn bộ (exit() để thoát): ").strip()
                if idx.isdigit() and 1 <= int(idx) <= len(data):
                    old = data[int(idx) - 1]
                    new_q = input("❓ Câu hỏi mới: ").strip()
                    new_a = input("✅ Đáp án mới: ").strip()
                    new_d = input("💡 Mô tả mới: ").strip()
                    if new_q and new_a:
                        data[int(idx) - 1] = (str(idx), new_a, new_q, new_d)
                        self._save(path, data)
                        log_action("EDIT_Q_FULL", f"{os.path.basename(path)} | ID:{idx} | OLD:{old} | NEW:{data[int(idx)-1]}")
                        self.clearsrc()
                        print("✏️ Đã cập nhật câu hỏi.")
                        self._show(path)
            else:
                self._edit_field(data, path, field_map[mode])

    def _edit_field(self, data, path, field_idx):
        """Sửa một trường (question/answer/desc) và log hành động."""
        idx = input("🔢 Nhập ID cần sửa: ").strip()
        if idx.isdigit() and 1 <= int(idx) <= len(data):
            entry = list(data[int(idx) - 1])
            old_val = entry[field_idx]
            new_val = input(f"✏️ Nhập giá trị mới (cũ: {old_val}) (enter = giữ nguyên): ").strip()
            if new_val == "":
                print("⚠️ Không có thay đổi.")
                return
            entry[field_idx] = new_val
            data[int(idx) - 1] = tuple(entry)
            self._save(path, data)
            log_action("EDIT_FIELD", f"{os.path.basename(path)} | ID:{idx} | field_idx:{field_idx} | OLD:{old_val} | NEW:{new_val}")
            print("✅ Đã sửa thành công.")

    # ====== QUIZ & EXPORT ======
    def _options(self, correct, pool, n):
        """Sinh lựa chọn (loại trừ đáp án đúng + 'Đúng'/'Sai')."""
        pool = list(set(pool) - {correct, "Đúng", "Sai"})
        return random.sample(pool, min(n - 1, len(pool))) + [correct]

    @staticmethod
    def _progress_bar(percent, width=30):
        """Trả về string progress bar (ASCII)."""
        filled = int(width * percent // 100)
        bar = "[" + "=" * filled + " " * (width - filled) + "]"
        return f"{bar} {percent:.1f}%"

    def _quiz(self, data, n_opts=None, max_qs=None):
        """
        Chạy quiz:
        - Ghi lại từng câu hỏi + đáp án chọn vào results (dùng để in bảng điểm và export)
        - Sau quiz: in bảng điểm có highlight màu và progress bar, export CSV, log hành động.
        """
        if not data:
            print("❌ Không có câu hỏi.")
            return

        pool = data if max_qs is None else (data * ((max_qs // len(data)) + 1))[:max_qs]
        all_ans = [a for _, a, _, _ in data]

        results = []  # list of dict: {idx, q, correct, chosen, desc, ok}
        score = 0

        for i, (_, a, q, d) in enumerate(pool, 1):
            print("\n" + "-" * 60)
            print(f"{i}. ❓ {q}")

            # Sinh lựa chọn
            if "nhận định đúng sai" in q.lower():
                opts = ["Đúng", "Sai"]
            else:
                opts = self._options(a, all_ans, n_opts)
            random.shuffle(opts)

            letters = string.ascii_lowercase[:len(opts)]
            mapping = dict(zip(letters, opts))

            # In lựa chọn
            for k, v in mapping.items():
                print(f"  {k}) {v}")

            pick = input("👉 Nhập đáp án: ").lower().strip()
            chosen = mapping.get(pick, "") if pick in mapping else ""
            ok = chosen.lower() == a.lower()
            if ok:
                score += 1

            # Lưu kết quả cho bảng điểm + export
            results.append({
                "index": i,
                "question": q,
                "correct": a,
                "chosen": chosen or "(không hợp lệ)",
                "desc": d,
                "ok": ok
            })

            # Phản hồi ngắn cho từng câu
            if ok:
                print(f"{GREEN}✅ Chính xác!{RESET}")
            else:
                print(f"{RED}❌ Sai!{RESET} ➤ Đáp án đúng: {a}")
            if d:
                print(f"   {YELLOW}💡 Mô tả: {d}{RESET}")

        total = len(results)
        wrong = total - score
        percent = (score / total * 100) if total else 0.0

        # In BẢNG ĐIỂM (tóm tắt)
        print("\n" + "=" * 60)
        print(f"{BLUE}🎯 BẢNG ĐIỂM CHI TIẾT{RESET}")
        header = f"{'#':>3}  {'RESULT':^8}  {'CHOSEN':^20}  {'CORRECT':^20}"
        print(header)
        print("-" * 60)
        for r in results:
            idx = r["index"]
            res_sym = f"{GREEN}✅{RESET}" if r["ok"] else f"{RED}❌{RESET}"
            chosen = (r["chosen"][:18] + "...") if len(r["chosen"]) > 18 else r["chosen"]
            correct = (r["correct"][:18] + "...") if len(r["correct"]) > 18 else r["correct"]
            # Highlight dòng đúng/sai màu sắc
            print(f"{idx:>3})  {res_sym:^8}  {chosen:<20}  {correct:<20}")

        print("-" * 60)
        print(f"{GREEN}✅ Đúng : {score}{RESET}    {RED}❌ Sai : {wrong}{RESET}    {CYAN}📊 Tỉ lệ: {percent:.1f}%{RESET}")
        # Progress bar
        print(self._progress_bar(percent))

        # Export CSV
        csv_name = f"quiz_results_{timestamp_now()}.csv"
        csv_path = os.path.join(EXPORT_DIR, csv_name)
        try:
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as csvfile:
                writer = csv.writer(csvfile)
                # Header meta
                writer.writerow(["timestamp", datetime.datetime.now().isoformat()])
                writer.writerow(["user", current_user()])
                writer.writerow(["total_questions", total])
                writer.writerow(["score", score])
                writer.writerow(["wrong", wrong])
                writer.writerow(["percent", f"{percent:.1f}"])
                writer.writerow([])  # blank
                # detail header
                writer.writerow(["idx", "question", "chosen", "correct", "ok", "desc"])
                for r in results:
                    writer.writerow([r["index"], r["question"], r["chosen"], r["correct"], r["ok"], r["desc"]])
            print(f"{BRIGHT_GREEN}✅ Đã export kết quả: {csv_path}{RESET}")
            log_action("EXPORT_CSV", f"{csv_path} | score={score}/{total} ({percent:.1f}%)")
        except Exception as e:
            print(f"{RED}⚠️ Lỗi khi export CSV: {e}{RESET}")
            log_action("EXPORT_ERROR", str(e))

    def play_file(self):
        """Chơi quiz theo 1 file cụ thể."""
        path = self._choose_file("chơi")
        if path:
            self._quiz(self._load(path),
                       n_opts=MAX_GENERATE_NORMAL_ANSWERS,
                       max_qs=MAX_GENERATE_NORMAL_QUESTIONS)

    def play_all(self):
        """Chơi quiz với tất cả file trong thư mục."""
        files = self._files()
        data = []
        for f in files:
            data.extend(self._load(os.path.join(self.qdir, f)))
        random.shuffle(data)
        self._quiz(data, n_opts=MAX_GENERATE_ALL_ANSWERS, max_qs=MAX_GENERATE_ALL_QUESTIONS)

    # ====== MENU ======
    def manage_questions(self):
        """Menu CRUD nội dung."""
        actions = {
            "1": ("thêm", f"{BRIGHT_GREEN}➕ Thêm nội dung{RESET}"),
            "2": ("xoá", f"{BRIGHT_RED}🗑️ Xoá nội dung{RESET}"),
            "3": ("sửa", f"{BRIGHT_YELLOW}✏️ Sửa toàn bộ{RESET}"),
            "4": ("sửaQ", f"{BRIGHT_YELLOW}✏️ Sửa câu hỏi{RESET}"),
            "5": ("sửaA", f"{BRIGHT_YELLOW}✏️ Sửa đáp án{RESET}"),
            "6": ("sửaD", f"{BRIGHT_YELLOW}✏️ Sửa mô tả{RESET}"),
        }
        while True:
            self.clearsrc()
            print("\n===== 📋 QUẢN LÝ NỘI DUNG =====")
            for k, (_, label) in actions.items():
                print(f" {k}) {label}")
            print(" exit() 🔙 quay lại")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch.lower() == "exit()":
                return
            if ch in actions:
                self._crud(actions[ch][0])
            else:
                print("⚠️ Lựa chọn không hợp lệ.")

    def manage_files(self):
        """Menu quản lý tệp tin (tạo/xoá/đổi tên)."""
        while True:
            self.clearsrc()
            self._list_files()
            print("\n===== 📂 QUẢN LÝ FILE =====")
            print(" 1) ➕ Tạo file\n 2) 🗑️ Xoá file\n 3) ✏️ Đổi tên file\n exit() 🔙 quay lại")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch == "1":
                name = input("📄 Nhập tên file mới (không cần .txt): ").strip()
                if name:
                    path = os.path.join(self.qdir, f"{name}.txt")
                    if os.path.exists(path):
                        print("⚠️ File đã tồn tại.")
                    else:
                        open(path, "w", encoding="utf-8").close()
                        log_action("CREATE_FILE", path)
                        print(f"✅ Đã tạo {name}.txt")
            elif ch == "2":
                path = self._choose_file("xoá")
                if path and input(f"❓ Xoá {os.path.basename(path)} (y/n): ").lower() == "y":
                    os.remove(path)
                    log_action("DELETE_FILE", path)
                    print("🗑️ Đã xoá file.")
            elif ch == "3":
                path = self._choose_file("đổi tên")
                if path:
                    new = input("✏️ Nhập tên mới (không cần .txt): ").strip()
                    if new:
                        newpath = os.path.join(self.qdir, f"{new}.txt")
                        os.rename(path, newpath)
                        log_action("RENAME_FILE", f"{path} -> {newpath}")
                        print("✅ Đã đổi tên file.")
            elif ch.lower() == "exit()":
                return
            else:
                print("⚠️ Lựa chọn không hợp lệ.")

    def menu(self):
        """Menu chính chương trình."""
        actions = {
            "1": (self.play_file, f"{BRIGHT_GREEN}🎯 Chơi theo bộ{RESET}"),
            "2": (self.play_all, f"{BRIGHT_GREEN}🌍 Chơi tất cả{RESET}"),
            "3": (self.manage_questions, f"{BRIGHT_YELLOW}📋 Quản lý câu hỏi{RESET}"),
            "4": (self.manage_files, f"{BRIGHT_YELLOW}📂 Quản lý file{RESET}"),
            "0": (lambda: print(f"{BRIGHT_RED}👋 Tạm biệt!"), f"{BRIGHT_RED}🚪 Thoát{RESET}"),
        }
        while True:
            print(f"{BLUE}\n===== 📚 FLASHCARD QUIZ GAME ====={RESET}")
            for k, (_, label) in actions.items():
                print(f" {k}) {label}")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch in actions:
                if ch == "0":
                    return
                actions[ch][0]()
            else:
                print("⚠️ Sai lựa chọn.")

# Entry point
if __name__ == "__main__":
    QuizGame().menu()
