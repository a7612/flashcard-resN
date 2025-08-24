# gui_quiz_with_theme.py
import json, random, shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

# ========== CONFIG ==========
BASE_DIR = Path.cwd()
QUESTIONS_DIR = BASE_DIR / "questions"
CONFIG_FILE = BASE_DIR / "config.json"
WIDTH, HEIGHT = 640, 960
MAX_QUESTIONS = 20
FONT = ("Arial", 11)

# ========== UTILS ==========
def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_config(cfg):
    try:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def center_window(win, width=640, height=480):
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x = (sw // 2) - (width // 2)
    y = (sh // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

# ========== Quiz Manager ==========
class QuizManager:
    def __init__(self, qdir: Path = QUESTIONS_DIR):
        self.qdir = Path(qdir)
        self.qdir.mkdir(exist_ok=True)

    def list_files(self):
        return sorted([p.name for p in self.qdir.glob("*.txt")])

    def load_questions(self, filename):
        path = self.qdir / filename
        if not path.exists():
            return []
        qs = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split(",", 2)
                if len(parts) == 3:
                    qid, ans, q = parts
                    qs.append((qid, ans.strip(), q.strip()))
        return qs

    def save_questions(self, filename, questions):
        # sort theo đáp án (case-insensitive) rồi reindex ID
        questions.sort(key=lambda x: x[1].lower())
        path = self.qdir / filename
        with path.open("w", encoding="utf-8") as f:
            for i, (_, ans, q) in enumerate(questions, 1):
                f.write(f"{i},{ans},{q}\n")

    def add_question(self, filename, question, answer):
        qs = self.load_questions(filename)
        qs.append((str(len(qs)+1), answer.strip(), question.strip()))
        self.save_questions(filename, qs)

    def delete_question(self, filename, qid):
        qs = self.load_questions(filename)
        qs = [q for q in qs if q[0] != str(qid)]
        self.save_questions(filename, qs)

    def import_file(self, src_path: str):
        src = Path(src_path)
        if src.exists() and src.suffix == ".txt":
            dest = self.qdir / src.name
            shutil.copy(src, dest)
            return dest.name
        return None

    def export_file(self, filename, dest_path: str):
        shutil.copy(self.qdir / filename, Path(dest_path))

# ========== Main GUI ==========
class QuizGUI:
    def __init__(self, root):
        self.root = root
        self.mgr = QuizManager()
        cfg = load_config()
        self.theme = cfg.get("theme", "light")

        self.root.title("📚 Flashcard Quiz")
        center_window(self.root, WIDTH, HEIGHT)
        self.root.minsize(560, 700)

        self._build_ui()
        self._apply_theme(self.theme)
        self._refresh_files()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill="both", expand=True)

        # File list
        top = ttk.LabelFrame(frm, text="📂 File câu hỏi", padding=8)
        top.pack(fill="x")
        self.file_listbox = tk.Listbox(top, height=6, font=FONT, activestyle="none")
        self.file_listbox.pack(side="left", fill="both", expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", lambda e: self._show_questions())

        fbtns = ttk.Frame(top); fbtns.pack(side="right", fill="y")
        ttk.Button(fbtns, text="🔄 Refresh", command=self._refresh_files).pack(fill="x", pady=3)
        ttk.Button(fbtns, text="📥 Import", command=self._import_file).pack(fill="x", pady=3)
        ttk.Button(fbtns, text="📤 Export", command=self._export_file).pack(fill="x", pady=3)
        self.theme_btn = ttk.Button(fbtns, text="🌙 Dark Mode", command=self._toggle_theme)
        self.theme_btn.pack(fill="x", pady=3)

        # Question list
        mid = ttk.LabelFrame(frm, text="📋 Danh sách câu hỏi", padding=8)
        mid.pack(fill="both", expand=True, pady=8)

        self.tree = ttk.Treeview(mid, columns=("id","answer","question"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("answer", text="Đáp án")
        self.tree.heading("question", text="Câu hỏi")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("answer", width=120)
        self.tree.column("question", width=420)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        # Actions
        bottom = ttk.Frame(frm); bottom.pack(fill="x", pady=5)
        ttk.Button(bottom, text="🎯 Chơi theo bộ", command=self._play_selected).pack(side="left", padx=5)
        ttk.Button(bottom, text="🌍 Chơi toàn bộ", command=self._play_all).pack(side="left", padx=5)
        ttk.Button(bottom, text="➕ Thêm câu hỏi", command=self._add_question).pack(side="left", padx=5)
        ttk.Button(bottom, text="🗑️ Xoá câu hỏi", command=self._delete_question).pack(side="left", padx=5)

        self.status_lbl = ttk.Label(frm, text="Ready", font=FONT)
        self.status_lbl.pack(anchor="e")

    # ===== file ops =====
    def _refresh_files(self):
        self.file_listbox.delete(0, tk.END)
        files = self.mgr.list_files()
        for f in files:
            count = len(self.mgr.load_questions(f))
            self.file_listbox.insert(tk.END, f"{f} ({count} câu)")
        if files:
            self.file_listbox.selection_set(0)
            self._show_questions()
        else:
            self.tree.delete(*self.tree.get_children())

    def _get_selected_filename(self):
        sel = self.file_listbox.curselection()
        if not sel: return None
        return self.file_listbox.get(sel[0]).split(" (")[0]

    def _show_questions(self):
        fname = self._get_selected_filename()
        if not fname: return
        self.tree.delete(*self.tree.get_children())
        qs = self.mgr.load_questions(fname)
        for q in qs:
            self.tree.insert("", "end", values=q)
        self.status_lbl.config(text=f"{fname} — {len(qs)} câu")

    def _add_question(self):
        fname = self._get_selected_filename()
        if not fname: return
        q = simpledialog.askstring("❓", "Nhập câu hỏi:")
        if q is None: return
        a = simpledialog.askstring("✅", "Nhập đáp án đúng:")
        if a is None: return
        if not q.strip() or not a.strip():
            messagebox.showwarning("⚠️", "Không được để trống.")
            return
        self.mgr.add_question(fname, q, a)
        self._show_questions()
        messagebox.showinfo("➕", "Đã thêm câu hỏi.")

    def _delete_question(self):
        fname = self._get_selected_filename()
        if not fname: return
        sel = self.tree.selection()
        if not sel: return
        qid = self.tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Xác nhận", f"Xoá câu ID {qid}?"):
            self.mgr.delete_question(fname, qid)
            self._show_questions()

    def _import_file(self):
        p = filedialog.askopenfilename(filetypes=[("Text files","*.txt")])
        if not p: return
        res = self.mgr.import_file(p)
        self._refresh_files()
        messagebox.showinfo("📥", f"Đã import: {res}")

    def _export_file(self):
        fname = self._get_selected_filename()
        if not fname: return
        dest = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=fname)
        if dest:
            self.mgr.export_file(fname, dest)
            messagebox.showinfo("📤", f"Đã export → {dest}")

    # ===== quiz logic =====
    def _play_selected(self):
        fname = self._get_selected_filename()
        if not fname: return
        qs = self.mgr.load_questions(fname)
        if not qs: return
        QuizWindow(self.root, qs, theme=self.theme)

    def _play_all(self):
        all_qs = []
        for f in self.mgr.list_files():
            all_qs += self.mgr.load_questions(f)
        if not all_qs: return
        QuizWindow(self.root, all_qs, theme=self.theme, num_choices=8)

    # ===== theme =====
    def _toggle_theme(self):
        self.theme = "dark" if self.theme=="light" else "light"
        self._apply_theme(self.theme)
        cfg = load_config(); cfg["theme"] = self.theme; save_config(cfg)

    def _apply_theme(self, theme):
        style = ttk.Style()
        try: style.theme_use("clam")
        except: pass
        if theme=="light":
            bg, fg = "#fff", "#111"; self.theme_btn.config(text="🌙 Dark Mode")
        else:
            bg, fg = "#2b2b2b", "#eee"; self.theme_btn.config(text="☀️ Light Mode")
        self.root.configure(bg=bg)
        style.configure("Treeview", background=bg, fieldbackground=bg, foreground=fg, font=FONT)
        style.configure("Treeview.Heading", font=(FONT[0], 10, "bold"), background="#666", foreground=fg)

# ========== Quiz Window ==========
class QuizWindow(tk.Toplevel):
    def __init__(self, root, questions, theme="light", num_choices=4):
        super().__init__(root)
        self.questions = self._prepare_pool(questions)
        self.num_choices = num_choices
        self.idx = 0; self.score=0
        self.all_answers = list(dict.fromkeys([ans for _,ans,_ in questions]))
        self.correct = None

        self.title("🎯 Quiz")
        center_window(self, 600, 420)

        self.q_var = tk.StringVar()
        ttk.Label(self, textvariable=self.q_var, wraplength=560, font=("Arial",13)).pack(pady=8)
        self.ans_var = tk.StringVar()
        self.radio_frame = ttk.Frame(self); self.radio_frame.pack()
        self.radios = [ttk.Radiobutton(self.radio_frame, text="", variable=self.ans_var) for _ in range(num_choices)]
        for rb in self.radios: rb.pack(anchor="w", pady=2)

        btns = ttk.Frame(self); btns.pack(pady=5)
        ttk.Button(btns, text="Trả lời", command=self._submit).pack(side="left", padx=5)
        ttk.Button(btns, text="Bỏ qua", command=self._skip).pack(side="left", padx=5)
        self.progress = ttk.Label(self, text=""); self.progress.pack()

        self._show_question()

    def _prepare_pool(self, qs):
        if len(qs) >= MAX_QUESTIONS: return random.sample(qs, MAX_QUESTIONS)
        pool=[]; 
        while len(pool)<MAX_QUESTIONS: pool+=qs
        random.shuffle(pool); return pool[:MAX_QUESTIONS]

    def _build_options(self, correct):
        pool = [p for p in self.all_answers if p.lower()!=correct.lower()]
        wrongs = random.sample(pool, min(self.num_choices-1,len(pool)))
        opts = wrongs+[correct]; random.shuffle(opts); return opts

    def _show_question(self):
        if self.idx>=len(self.questions): return self._finish()
        _, correct, q = self.questions[self.idx]; self.correct=correct
        opts = self._build_options(correct)
        self.q_var.set(f"Câu {self.idx+1}/{len(self.questions)}: {q}")
        self.ans_var.set("")
        for rb,opt in zip(self.radios, opts): rb.config(text=opt, value=opt)
        self.progress.config(text=f"Điểm: {self.score}")

    def _submit(self):
        choice=self.ans_var.get().strip()
        if not choice: return
        if choice.lower()==self.correct.lower():
            self.score+=1; messagebox.showinfo("✅","Đúng!")
        else:
            messagebox.showerror("❌",f"Sai. Đáp án: {self.correct}")
        self.idx+=1; self._show_question()

    def _skip(self):
        self.idx+=1; self._show_question()

    def _finish(self):
        pct=(self.score/len(self.questions))*100
        messagebox.showinfo("🌟", f"Điểm: {self.score}/{len(self.questions)}\nTỉ lệ: {pct:.1f}%")
        self.destroy()

# ========== RUN ==========
if __name__=="__main__":
    root=tk.Tk()
    app=QuizGUI(root)
    root.mainloop()
