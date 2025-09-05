import os
import random
import string
import csv
import datetime
import getpass
import uuid
from config import *

LOG_DIR = "logs"
EXPORT_DIR = "exports"
CLEAR_SCREEN = True  # Cho phép tắt/mở clearsrc

# Tạo thư mục cần thiết
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(QUESTIONS_DIR, exist_ok=True)

def timestamp_now():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def current_user():
    try:
        return getpass.getuser()
    except Exception:
        return "unknown_user"

def log_action(action: str, detail: str = ""):
    ts = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    fn = os.path.join(LOG_DIR, f"{datetime.datetime.now().strftime("%Y%m%d")}.log")    
    user = current_user()
    line = f"{ts} | {user} | {action} | {detail}\n"
    with open(fn, "a", encoding="utf-8") as f:
        f.write(line)

class QuizGame:
    def __init__(self, qdir=QUESTIONS_DIR):
        self.qdir = qdir
        os.makedirs(self.qdir, exist_ok=True)

    @staticmethod
    def clearsrc():
        if CLEAR_SCREEN:
            os.system("cls" if os.name == "nt" else "clear")

    def _files(self):
        return [f for f in os.listdir(self.qdir) if f.endswith(".csv")]

    def _list_files(self, show=True):
        files = self._files()
        if not files:
            print("⚠️ Không có file câu hỏi.")
            return []
        if show:
            print(f"{BRIGHT_GREEN}\n📂 Danh sách file:{RESET}")
            for i, f in enumerate(files, 1):
                path = os.path.join(self.qdir, f)
                try:
                    with open(path, encoding="utf-8-sig") as csvfile:
                        count = sum(1 for _ in csv.reader(csvfile)) - 1
                except Exception:
                    count = 0
                print(f" {i:>2}) {f:<25} | {count} câu hỏi")
        return files

    def _choose_file(self, action="chọn"):
        files = self._list_files()
        if not files:
            return None
        idx = input(f"\n👉 Nhập số file để {action}: ").strip()
        if idx.isdigit() and 1 <= int(idx) <= len(files):
            return os.path.join(self.qdir, files[int(idx) - 1])
        print("⚠️ Chọn không hợp lệ.")
        return None

    def _load(self, path):
        if not os.path.exists(path):
            return []
        data = []
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append((row["id"], row["answer"], row["question"], row["desc"], row["ref"]))
        return data

    def _save(self, path, data):
        # Sort theo cột id (cột 0)
        # data_sorted = sorted(data, key=lambda x: uuid.UUID(x[0]))
        data_sorted = sorted(data, key=lambda x: x[1].lower()) 

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "answer", "question", "desc", "ref"])
            for row in data_sorted:
                writer.writerow(row)

    def _show(self, path):
        data = self._load(path)
        if not data:
            print("❌ File trống.")
            return []
        print("\n📋 DANH SÁCH CÂU HỎI:")
        for i, (qid, a, q, d, r) in enumerate(data, 1):
            print(f"{BRIGHT_CYAN}{i:>2}) {q}{RESET}")
            print(f"   {GREEN}➤ Đáp án: {a}{RESET}")
            if d:
                print(f"   {YELLOW}💡 Mô tả: {d}{RESET}")
            if r:
                print(f"   {CYAN}🔗 Reference: {r}{RESET}")
        return data

    # CRUD
    def _crud(self, mode):
        path = self._choose_file(mode)
        if not path:
            return
        data = self._show(path)

        if mode == "thêm":
            while True:
                self.clearsrc()
                self._show(path)
                q = input("\n❓ Nhập câu hỏi (exit() để thoát): ").strip()
                if q.lower() == "exit()":
                    break
                a = input("✅ Đáp án: ").strip()
                if not q or not a:
                    print("⚠️ Câu hỏi và đáp án không được để trống.")
                    continue
                d = input("💡 Mô tả (có thể bỏ trống): ").strip()
                r = input("🔗 Reference (có thể bỏ trống): ").strip()
                data.append((str(uuid.uuid4()), a, q, d, r))
                self._save(path, data)
                log_action("ADD_Q", f"{os.path.basename(path)} | Q: {q}")
                print("➕ Đã thêm câu hỏi mới.")

        elif mode == "xoá":
            while True:
                idx = input("\n🗑️ Nhập số thứ tự cần xoá (exit() để thoát): ").strip()
                if idx.lower() == "exit()":
                    break
                if idx.isdigit() and 1 <= int(idx) <= len(data):
                    removed = data.pop(int(idx) - 1)
                    self._save(path, data)
                    log_action("DEL_Q", f"{os.path.basename(path)} | Q: {removed[2]}")
                    print(f"🗑️ Đã xoá: {removed[2]}")
                else:
                    print("❌ ID không hợp lệ.")

        elif mode.startswith("sửa"):
            field_map = {"sửaQ": 2, "sửaA": 1, "sửaD": 3, "sửaR": 4}
            idx = input("🔢 Nhập số thứ tự cần sửa: ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(data):
                entry = list(data[int(idx) - 1])
                if mode == "sửa":
                    entry[2] = input("❓ Câu hỏi mới: ").strip() or entry[2]
                    entry[1] = input("✅ Đáp án mới: ").strip() or entry[1]
                    entry[3] = input("💡 Mô tả mới: ").strip() or entry[3]
                    entry[4] = input("🔗 Reference mới: ").strip() or entry[4]
                else:
                    field_idx = field_map[mode]
                    new_val = input(f"✏️ Nhập giá trị mới (cũ: {entry[field_idx]}): ").strip()
                    if new_val:
                        entry[field_idx] = new_val
                data[int(idx) - 1] = tuple(entry)
                self._save(path, data)
                log_action("EDIT_Q", f"{os.path.basename(path)} | {entry}")
                print("✅ Đã sửa thành công.")

    # Quiz
    def _options(self, correct, pool, n):
        pool = list(set(pool) - {correct, "Đúng", "Sai"})
        return random.sample(pool, min(n - 1, len(pool))) + [correct]

    @staticmethod
    def _progress_bar(percent, width=30):
        filled = int(width * percent // 100)
        bar = "[" + "=" * filled + " " * (width - filled) + "]"
        return f"{bar} {percent:.1f}%"

    def _normalize(self, text):
        return text.replace("\\n", "\n").replace("\\t", "\t") if text else text

    def _quiz(self, data, n_opts=None, max_qs=None):
        if not data:
            print("❌ Không có câu hỏi.")
            return

        # 🔀 Random nếu cần
        pool = data if max_qs is None else (data * ((max_qs // len(data)) + 1))[:max_qs]
        if max_qs is not None:
            random.shuffle(pool)
            pool = pool[:max_qs]

        all_ans = [a for _, a, _, _, _ in data]
        results, score = [], 0

        for i, (_, a, q, d, r) in enumerate(pool, 1):
            print("\n" + "-" * 60)

            # 🔥 Chuẩn hóa xuống dòng
            q_disp, a_disp, d_disp, r_disp = (self._normalize(x) for x in (q, a, d, r))
            
            # q_disp = q.replace("\\n", "\n").replace("\\t", "\t") 
            # a_disp = a.replace("\\n", "\n").replace("\\t", "\t") 
            # d_disp = d.replace("\\n", "\n").replace("\\t", "\t") if d else d 
            # r_disp = r.replace("\\n", "\n").replace("\\t", "\t") if r else r
            
            print(f"{i}. ❓ {q_disp}")

            if None:
                pass
            elif "nhận định đúng sai" in q.lower():
                opts = ["Đúng", "Sai"]
            elif "dịch" in q.lower():
                opts = self._options(a_disp, list({a_disp, *[ans for _, ans, ques, _, _ in data if "dịch" in ques.lower()]}), n_opts)
            elif "tên đầy đủ" in q.lower():
                opts = self._options(a_disp, list({a_disp, *[ans for _, ans, ques, _, _ in data if "tên đầy đủ" in ques.lower()]}), n_opts)                                           
            else:
                opts = self._options(a_disp, all_ans, n_opts) 
                        
            # opts = ["Đúng", "Sai"] if "nhận định đúng sai" in q.lower() else self._options(a_disp, all_ans, n_opts)
            
            random.shuffle(opts)
            letters = string.ascii_lowercase[:len(opts)]
            mapping = dict(zip(letters, opts))

            for k, v in mapping.items():
                print(f"  {k}) {v}")

            while True:
                pick = input("👉 Nhập đáp án: ").lower().strip()
                if pick in mapping:
                    chosen = mapping[pick]
                    break
                print("⚠️ Lựa chọn không hợp lệ, nhập lại đi!")
                log_action("CHOSEN", f"Nhập thất bại")

            # Lấy tất cả đáp án đúng cho câu hỏi hiện tại
            correct_answers = [ans for _, ans, ques, _, _ in data if ques.strip().lower() == q.strip().lower()]
            ok = chosen.lower() in (ca.lower() for ca in correct_answers)
            
            # ok = chosen.lower() == a_disp.lower()
            
            # pick = input("👉 Nhập đáp án: ").lower().strip()
            # ok = pick.lower() == a_disp.lower()
            
            # 🚫 Không cho Enter trống skip
            # while True:
            #     pick = input("👉 Nhập đáp án: ").lower().strip()
            #     if pick in mapping:
            #         chosen = mapping[pick]
            #         break
            #     print("⚠️ Lựa chọn không hợp lệ, nhập lại đi!")

            # ok = chosen.lower() == a_disp.lower()
            if ok:
                score += 1

            results.append({
                "index": i,
                "question": q_disp,
                "correct": a_disp,
                # "chosen": chosen,
                "desc": d_disp,
                "ref": r_disp,
                "ok": ok
            })

            if ok:
                print(f"{GREEN}✅ Chính xác!{RESET}")
                log_action(f"CHOSEN:{_}", f"{chosen} - {q} Đúng + 1 điểm")
                if d_disp:
                    print(f"Mô tả: {d_disp}")
                if r_disp:
                    print(f"Tham chiếu:\n{r_disp}")
            else:
                print(f"{RED}❌ Sai!{RESET} ➤ Đáp án đúng: {a_disp}")
                log_action(f"CHOSEN:{_}", f"{chosen} - {q} Sai")
                if d_disp:
                    print(f"{BRIGHT_YELLOW}Mô tả: {d_disp}{RESET}")
                if r_disp:
                    print(f"{BRIGHT_CYAN}Tham chiếu:\n{r_disp}{RESET}")

        # 📊 Thống kê
        total = len(results)
        wrong = total - score
        percent = (score / total * 100) if total else 0.0

        print("\n" + "=" * 60)
        print(f"{BLUE}🎯 BẢNG ĐIỂM CHI TIẾT{RESET}")
        header = f"{'#':>3}  {'RESULT':^8}  {'CHOSEN':^20}  {'CORRECT':^20}"
        print(header)
        print("-" * 60)
        for r in results:
            res_sym = f"{GREEN}✅{RESET}" if r["ok"] else f"{RED}❌{RESET}"
            print(f"{r['index']:>3})  {res_sym:^8}   {r['correct']:<20}")
            # print(f"{r['index']:>3})  {res_sym:^8}  {r['chosen']:<20}  {r['correct']:<20}")

        print("-" * 60)
        print(f"{GREEN}✅ Đúng : {score}{RESET}    {RED}❌ Sai : {wrong}{RESET}    {CYAN}📊 Tỉ lệ: {percent:.1f}%{RESET}")
        print(self._progress_bar(percent))

        # 💾 Export CSV
        csv_name = f"quiz_results_{timestamp_now()}.csv"
        csv_path = os.path.join(EXPORT_DIR, csv_name)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["timestamp", datetime.datetime.now().isoformat()])
            writer.writerow(["user", current_user()])
            writer.writerow(["total_questions", total])
            writer.writerow(["score", score])
            writer.writerow(["wrong", wrong])
            writer.writerow(["percent", f"{percent:.1f}"])
            writer.writerow([])
            writer.writerow(["idx", "question", "correct", "ok", "desc", "reference"])
            # writer.writerow(["idx", "question", "chosen", "correct", "ok", "desc", "reference"])
            for r in results:
                writer.writerow([
                    r["index"], r["question"], r["correct"],
                    # r["index"], r["question"], r["chosen"], r["correct"],
                    r["ok"], r["desc"], r.get("ref", "")
                ])
        print(f"{BRIGHT_GREEN}✅ Đã export kết quả: {csv_path}{RESET}")


    def play_file(self):
        path = self._choose_file("chơi")
        if path:
            self._quiz(
                self._load(path),
                n_opts=MAX_GENERATE_NORMAL_ANSWERS,
                max_qs=MAX_GENERATE_NORMAL_QUESTIONS
            )

    def play_all(self):
        files = self._files()
        data = []
        for f in files:
            path = os.path.join(self.qdir, f)
            data.extend(self._load(path))

        # 🔥 Chơi tất cả câu hỏi một lần, không reset từng câu
        self._quiz(
            data,
            n_opts=MAX_GENERATE_ALL_ANSWERS,
            max_qs=MAX_GENERATE_ALL_QUESTIONS
        )


    # Menu
    def manage_questions(self):
        actions = {
            "1": ("thêm", f"{BRIGHT_GREEN}➕ Thêm nội dung{RESET}"),
            "2": ("xoá", f"{BRIGHT_RED}🗑️ Xoá nội dung{RESET}"),
            "3": ("sửa", f"{BRIGHT_YELLOW}✏️ Sửa toàn bộ{RESET}"),
            "4": ("sửaQ", f"{BRIGHT_YELLOW}✏️ Sửa câu hỏi{RESET}"),
            "5": ("sửaA", f"{BRIGHT_YELLOW}✏️ Sửa đáp án{RESET}"),
            "6": ("sửaD", f"{BRIGHT_YELLOW}✏️ Sửa mô tả{RESET}"),
            "7": ("sửaR", f"{BRIGHT_YELLOW}✏️ Sửa tham khảo{RESET}"),
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
        while True:
            self.clearsrc()
            self._list_files()
            print("\n===== 📂 QUẢN LÝ FILE =====")
            print(" 1) ➕ Tạo file\n 2) 🗑️ Xoá file\n 3) ✏️ Đổi tên file\n exit() 🔙 quay lại")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch == "1":
                name = input("📄 Nhập tên file mới (không cần .csv): ").strip()
                if name:
                    path = os.path.join(self.qdir, f"{name}.csv")
                    if os.path.exists(path):
                        print("⚠️ File đã tồn tại.")
                    else:
                        with open(path, "w", encoding="utf-8-sig", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow(["id", "answer", "question", "desc", "ref"])
                        log_action("CREATE_FILE", path)
                        print(f"✅ Đã tạo {name}.csv")
            elif ch == "2":
                path = self._choose_file("xoá")
                if path and input(f"❓ Xoá {os.path.basename(path)} (y/n): ").lower() == "y":
                    os.remove(path)
                    log_action("DELETE_FILE", path)
                    print("🗑️ Đã xoá file.")
            elif ch == "3":
                path = self._choose_file("đổi tên")
                if path:
                    new = input("✏️ Nhập tên mới (không cần .csv): ").strip()
                    if new:
                        newpath = os.path.join(self.qdir, f"{new}.csv")
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
                t = (f" {k}) {label}")
                print(t)
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch in actions:
                log_action(f"START: ", f"{ch}:{t}")
                if ch == "0":
                    return
                actions[ch][0]()
            else:
                print("⚠️ Sai lựa chọn.")

# Entry point
if __name__ == "__main__":
    QuizGame().menu()
