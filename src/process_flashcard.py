import os, csv, uuid, time
from src.core import _CONFIG, console
from src.utils import _replace_colors, _safe_input, _clear_screen, _handle_error, _move_to_trash
from src.process_log import log_action
from rich.table import Table
from rich.text import Text
from rich import box
import src.process_input as inp

class FlashcardManager:
    def __init__(self):
        self._data_cache = {}

    def clear_cache(self, path=None):
        if path:
            self._data_cache.pop(path, None)
        else:
            self._data_cache.clear()

    def _sort_data(self, data):
        """Sắp xếp danh sách câu hỏi dựa trên cấu hình QUESTION_SORT_BY."""
        mode = getattr(_CONFIG, 'QUESTION_SORT_BY', 'answer_asc')
        col_map = {'id': 0, 'answer': 1, 'question': 2, 'hint': 3, 'desc': 4}
        parts = mode.split('_')
        idx = col_map.get(parts[0], 1)
        rev = parts[1] == 'desc' if len(parts) > 1 else False
        # Sắp xếp chính theo cột chọn, phụ theo Answer và Question để đảm bảo thứ tự ổn định
        data.sort(key=lambda x: (str(x[idx]).lower(), str(x[1]).lower(), str(x[2]).lower()), reverse=rev)
        return data

    def load_data(self, path, force=False):
        # Trả về từ cache nếu có và không yêu cầu load lại
        if not force and path in self._data_cache:
            return self._data_cache[path]

        if not os.path.exists(path):
            return []

        try:
            rows = []
            with open(path, encoding="utf-8-sig") as f:
                # Tự động nhận diện delimiter (;) hoặc (,)
                head = f.read(2048); f.seek(0)
                delim = ';' if ';' in head and ',' not in head else ','
                reader = csv.DictReader(f, delimiter=delim)
                for r in reader:
                    rows.append(list(r.values()))
            
            # Sắp xếp dữ liệu sau khi load để hiển thị đúng chuẩn
            self._sort_data(rows)
            self._data_cache[path] = rows
            return rows
        except (FileNotFoundError, csv.Error, PermissionError) as e:
            _handle_error(f"❌ Lỗi nghiêm trọng khi nạp file '{os.path.basename(path)}': {type(e).__name__} - {e}")
            return []

    def save_data(self, path, data):
        try:
            # Sắp xếp dữ liệu trước khi ghi xuống file
            self._sort_data(data)
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "answer", "question", "hint", "desc"])
                writer.writerows(data)
            # Cập nhật cache ngay sau khi lưu để đồng bộ dữ liệu
            self._data_cache[path] = data
        except Exception as e:
            _handle_error(f"❌ Không thể ghi dữ liệu xuống file '{os.path.basename(path)}': {e}")

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
            
            # Tách biệt icon và nội dung để lệnh reset [/] không làm hỏng style icon
            qa = Text.from_markup("[bold blue]❓ [/]")
            qa.append(Text.from_markup(_replace_colors(q)))
            qa.append(Text.from_markup("\n[bold green]✅ [/]"))
            qa.append(Text.from_markup(_replace_colors(a)))
            
            extra = Text()
            if d: extra.append(Text.from_markup("[yellow]💡 [/]")).append(Text.from_markup(_replace_colors(d) + "\n"))
            if r: extra.append(Text.from_markup("[cyan]📖 [/]")).append(Text.from_markup(_replace_colors(r)))
            table.add_row(Text(str(i), style=stt_style), qa, extra)
        console.print(table)
        return data

    def add_question(self, path):
        last_id = None
        while True:
            _clear_screen()
            self.show_questions(path, highlight_id=last_id, highlight_type='add')
            try:
                q, a, d, r = inp.input_question_details()
                if q is None: break  # Thoát khi nhập /exit
                if a is None: break

                data = self.load_data(path)
                
                last_id = str(uuid.uuid4())
                data.append([last_id, a, q, d or "", r or ""])
                self.save_data(path, data)
                log_action("QUES_ADD", f"File: {os.path.basename(path)} | Q: {q[:50]}...")
                console.print("[green]✨ Đã thêm thành công! Nhập tiếp hoặc '/exit' để dừng.[/]"); time.sleep(0.5)
            except Exception as e:
                _handle_error(f"💥 Lỗi xử lý khi thêm câu hỏi: {e}")
                break

    def delete_question(self, path):
        while True:
            _clear_screen()
            data = self.show_questions(path)
            if not data: break
            try:
                val = inp.input_selection("🔢 Nhập STT để xoá hoặc '/all' (hoặc '/exit'): ", len(data), allow_all=True)
                if val is None: break
                
                if val == "/all":
                    confirm = inp.confirm_delete("câu hỏi trong file này")
                    if confirm == "y":
                        _move_to_trash(path) # Backup bản cũ vào trash trước khi làm trống
                        data = []
                        self.save_data(path, data)
                        console.print("[bold yellow]♻️ Đã dọn sạch câu hỏi (Bản cũ đã được lưu vào trash/).[/]")
                        log_action("DELETE_ALL_QUESTIONS", path)
                        time.sleep(1)
                        break
                    continue

                removed = data.pop(val)
                self.save_data(path, data)
                log_action("QUES_DELETE", f"File: {os.path.basename(path)} | Q: {removed[2][:50]}...")
                console.print(f"[red]🗑️ Đã xoá câu hỏi: {_replace_colors(removed[2])}[/]"); time.sleep(0.5)
            except Exception as e:
                _handle_error(f"❌ Lỗi khi thực hiện xoá: {e}")
                break

    def edit_question(self, path, field_idx=None):
        last_id = None
        while True:
            _clear_screen()
            data = self.show_questions(path, highlight_id=last_id, highlight_type='edit')
            if not data: break
            
            idx = inp.input_selection("🔢 Nhập STT để sửa (hoặc '/exit'): ", len(data))
            if idx is None: break
            
            try:
                row = list(data[idx])
                last_id = row[0]
                if field_idx is None: # Sửa toàn bộ
                    q, a, d, r = inp.input_question_details(row[2], row[1], row[3], row[4], is_edit=True)
                    if q is None: return
                    row[2], row[1], row[3], row[4] = q, a or row[1], d or row[3], r or row[4]
                else:
                    # Logic sửa nhanh từng trường có thể giữ lại hoặc chuyển vào inp
                    new_v = _safe_input(f"✏️ Giá trị mới ({row[field_idx]}): ")
                    if new_v is None: break
                    if new_v: row[field_idx] = new_v
                    
                data[idx] = row
                self.save_data(path, data)
                log_action("QUES_EDIT", f"File: {os.path.basename(path)} | ID: {last_id}")
                console.print("[green]🛠️ Đã cập nhật.[/]"); time.sleep(0.5)
            except Exception as e:
                _handle_error(f"❌ Lỗi khi cập nhật câu hỏi tại dòng {idx+1}: {e}")
                break

    def validate_file(self, path):
        """Kiểm tra tính toàn vẹn và lỗi Markup Rich trong file."""
        errors = []
        data = self.load_data(path, force=True)
        if not data: return []

        for i, row in enumerate(data, 1):
            if len(row) < 3: continue
            q_text = str(row[2])
            
            if q_text.count('[') != q_text.count(']'):
                errors.append(f"Dòng {i}: [magenta]Cú pháp Markup [[ ]] không cân xứng[/]")
            
        return errors