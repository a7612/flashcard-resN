import os, csv, time
from src.core import _CONFIG, console, log_action, _safe_input
from rich.table import Table
from rich import box

class FileManager:
    def __init__(self):
        self.qdir = _CONFIG.QUESTIONS_DIR
        self._cache = {}

    def get_files(self):
        return [f for f in os.listdir(self.qdir) if f.endswith(".csv")]

    def count_questions(self, fname):
        if fname not in self._cache:
            try: 
                with open(os.path.join(self.qdir, fname), encoding="utf-8-sig") as f:
                    self._cache[fname] = max(0, sum(1 for _ in f) - 1)
            except: self._cache[fname] = 0
        return self._cache[fname]

    def list_files(self, show=True):
        files = self.get_files()
        if show:
            table = Table(title="📂 KHO DỮ LIỆU HỆ THỐNG", box=box.SIMPLE_HEAD)
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Tên Bộ Đề", style="bold white")
            table.add_column("Số câu", justify="right")
            for i, f in enumerate(files, 1):
                c = self.count_questions(f)
                color = "green" if c >= 64 else "cyan" if c >= 32 else "yellow"
                table.add_row(str(i), f"📚 {f}", f"[{color}]{c}[/]")
            console.print(table)
        return files

    def create_file(self):
        name = _safe_input("📝 Tên bộ đề mới (không cần .csv): ")
        if name and not os.path.exists(p := os.path.join(self.qdir, f"{name}.csv")):
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(["id", "answer", "question", "hint", "desc"])
            log_action("CREATE", p); console.print(f"[green]🆕 Đã tạo: {name}.csv[/]"); time.sleep(1)

    def delete_file(self, path):
        if _safe_input(f"❗ Xác nhận xoá vĩnh viễn {os.path.basename(path)}? (y/n) ") == "y":
            os.remove(path)
            self._cache.pop(os.path.basename(path), None)
            log_action("DELETE", path); console.print("[red]🗑️ Đã xoá file.[/]"); time.sleep(1)

    def rename_file(self, path):
        new = _safe_input("🏷️ Tên mới: ")
        if new:
            new_path = os.path.join(self.qdir, f"{new}.csv")
            os.rename(path, new_path)
            self._cache.clear()
            log_action("RENAME", f"{path}->{new_path}")
            console.print("[green]🏷️ Đã đổi tên bộ đề.[/]"); time.sleep(1)