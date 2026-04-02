import os, csv, uuid, time
from src.core import _CONFIG, console, log_action, _replace_colors, _safe_input, _clear_screen
from rich.table import Table
from rich.text import Text
from rich import box

class FlashcardManager:
    def load_data(self, path):
        if not os.path.exists(path): return []
        with open(path, encoding="utf-8-sig") as f:
            return [list(r.values()) for r in csv.DictReader(f)]

    def save_data(self, path, data):
        data.sort(key=lambda x: (str(x[1]).lower(), str(x[2]).lower()))
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "answer", "question", "hint", "desc"])
            writer.writerows(data)

    def show_questions(self, path, highlight_id=None, highlight_type=None):
        data = self.load_data(path)
        if not data:
            console.print(f"\n[yellow]⚠️ Bộ đề '{os.path.basename(path)}' hiện đang trống. Hãy thêm câu hỏi mới![/]")
            return []
        table = Table(title=f"📋 CHI TIẾT: {os.path.basename(path)}", box=box.ROUNDED, show_lines=True)
        table.add_column("STT", justify="right", width=4)
        table.add_column("NỘI DUNG CÂU HỎI", style="white")
        table.add_column("THÔNG TIN BỔ TRỢ", style="dim")
        for i, row in enumerate(data, 1):
            qid, a, q, d, r = row[:5]
            
            # Logic làm nổi bật dòng dựa trên ID và loại thao tác
            stt_style = "cyan"
            if qid == highlight_id:
                if highlight_type == 'add': stt_style = "bold green"
                elif highlight_type == 'edit': stt_style = "bold yellow"
            
            qa = Text().append("❓ ", style="bold blue").append(Text.from_ansi(_replace_colors(q)))
            qa.append("\n✅ ", style="bold green").append(Text.from_ansi(_replace_colors(a)))
            extra = Text()
            if d: extra.append("💡 ", style="yellow").append(Text.from_ansi(_replace_colors(d))).append("\n")
            if r: extra.append("📖 ", style="cyan").append(Text.from_ansi(_replace_colors(r)))
            table.add_row(Text(str(i), style=stt_style), qa, extra)
        console.print(table)
        return data

    def add_question(self, path):
        self.show_questions(path) # Hiển thị danh sách trước khi thêm
        data = self.load_data(path)
        q = _safe_input(f"❓ Câu hỏi mới: ")
        if not q: return
        a = _safe_input(f"✅ Đáp án chuẩn: ")
        if not a: return
        d = _safe_input("💡 Gợi ý: ")
        r = _safe_input("📖 Mô tả thêm: ")
        new_id = str(uuid.uuid4())
        data.append([new_id, a, q, d or "", r or ""])
        self.save_data(path, data)
        self.show_questions(path, highlight_id=new_id, highlight_type='add')
        console.print("[green]✨ Đã thêm thành công![/]"); time.sleep(0.5)

    def delete_question(self, path):
        data = self.show_questions(path)
        if not data: return
        val = _safe_input("🔢 Nhập STT để xoá: ", lambda x: (x.isdigit() and 1 <= int(x) <= len(data), int(x)-1 if x.isdigit() else 0))
        if val is not None:
            removed = data.pop(val)
            self.save_data(path, data)
            console.print(f"[red]🗑️ Đã xoá câu hỏi: {_replace_colors(removed[2])}[/]"); time.sleep(0.5)

    def edit_question(self, path, field_idx=None):
        data = self.show_questions(path)
        if not data: return
        idx = _safe_input("🔢 Nhập STT để sửa: ", lambda x: (x.isdigit() and 1 <= int(x) <= len(data), int(x)-1 if x.isdigit() else 0))
        if idx is None: return
        
        row = list(data[idx])
        target_id = row[0]
        if field_idx is None: # Sửa toàn bộ
            row[2] = _safe_input(f"❓ Câu hỏi ({row[2]}): ") or row[2]
            row[1] = _safe_input(f"✅ Đáp án ({row[1]}): ") or row[1]
            row[3] = _safe_input(f"💡 Gợi ý ({row[3]}): ") or row[3]
            row[4] = _safe_input(f"📖 Mô tả ({row[4]}): ") or row[4]
        else:
            new_val = _safe_input("✏️ Nhập giá trị mới: ")
            if new_val: row[field_idx] = new_val
            
        data[idx] = row
        self.save_data(path, data)
        self.show_questions(path, highlight_id=target_id, highlight_type='edit')
        console.print("[green]🛠️ Đã cập nhật.[/]"); time.sleep(0.5)