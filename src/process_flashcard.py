import os, csv, uuid, time, re
from src.core import _CONFIG, console, log_action, _replace_colors, _safe_input, _clear_screen, _handle_error, _move_to_trash
from rich.table import Table
from rich.text import Text
from rich import box

class FlashcardManager:
    def __init__(self):
        self._data_cache = {}

    def load_data(self, path, force=False):
        # Trả về từ cache nếu có và không yêu cầu load lại
        if not force and path in self._data_cache:
            return self._data_cache[path]

        if not os.path.exists(path):
            return []

        try:
            rows = []
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(list(r.values()))
            
            self._data_cache[path] = rows
            return rows
        except (FileNotFoundError, csv.Error, PermissionError) as e:
            _handle_error(f"❌ Lỗi nghiêm trọng khi nạp file '{os.path.basename(path)}': {type(e).__name__} - {e}")
            return []

    def save_data(self, path, data):
        try:
            data.sort(key=lambda x: (str(x[1]).lower(), str(x[2]).lower()))
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
                data = self.load_data(path)
                q = _safe_input(f"❓ Câu hỏi mới: ")
                if q is None: break  # Thoát khi nhập /exit
                if not q: continue   # Bỏ qua nếu để trống
                
                a = _safe_input(f"✅ Đáp án chuẩn: ")
                if a is None: break
                if not a: continue
                
                d = _safe_input("💡 Gợi ý (Enter để bỏ qua): ")
                if d is None: break
                
                r = _safe_input("📖 Mô tả thêm (Enter để bỏ qua): ")
                if r is None: break
                
                last_id = str(uuid.uuid4())
                data.append([last_id, a, q, d or "", r or ""])
                self.save_data(path, data)
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
                idx_info = lambda x: (
                    x.isdigit() and 1 <= int(x) <= len(data) or x.lower() == "/all",
                    int(x)-1 if x.isdigit() else x.lower()
                )
                val = _safe_input("🔢 Nhập STT để xoá hoặc '/all' để xoá hết (hoặc '/exit'): ", idx_info)
                if val is None: break
                
                if val == "/all":
                    confirm = _safe_input("❗ Xác nhận xoá TOÀN BỘ câu hỏi trong file này? (y/n) ")
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
            
            idx_info = lambda x: (x.isdigit() and 1 <= int(x) <= len(data), int(x)-1 if x.isdigit() else 0)
            idx = _safe_input("🔢 Nhập STT để sửa (hoặc '/exit'): ", idx_info)
            if idx is None: break
            
            try:
                row = list(data[idx])
                last_id = row[0]
                if field_idx is None: # Sửa toàn bộ
                    for i, label in [(2, "Câu hỏi"), (1, "Đáp án"), (3, "Gợi ý"), (4, "Mô tả")]:
                        val = _safe_input(f"✏️ {label} ({row[i]}): ")
                        if val is None: return # Thoát hẳn method nếu đang sửa dở mà muốn exit
                        if val: row[i] = val
                else:
                    new_val = _safe_input(f"✏️ Nhập giá trị mới ({row[field_idx]}): ")
                    if new_val is None: break
                    if new_val: row[field_idx] = new_val
                    
                data[idx] = row
                self.save_data(path, data)
                console.print("[green]🛠️ Đã cập nhật.[/]"); time.sleep(0.5)
            except Exception as e:
                _handle_error(f"❌ Lỗi khi cập nhật câu hỏi tại dòng {idx+1}: {e}")
                break

    def validate_file(self, path):
        """Kiểm tra mã ANSI cũ và lỗi Markup trong file."""
        errors = []
        data = self.load_data(path, force=True)
        if not data: return []

        # Regex tìm mã ANSI thực (\x1b...) hoặc literal ANSI ([94m...)
        ansi_rx = re.compile(r'\x1b\[[0-9;]*[mK]|\[\d+m')
        
        for i, row in enumerate(data, 1):
            if len(row) < 3: continue
            # Kiểm tra cả mã ANSI cũ và các thẻ Markup chưa đóng hết
            q_text = str(row[2])
            a_text = str(row[1])
            if ansi_rx.search(q_text) or ansi_rx.search(a_text):
                errors.append(f"Dòng {i}: [bold red]Phát hiện mã ANSI cũ[/]")
            
            if q_text.count('[') != q_text.count(']'):
                errors.append(f"Dòng {i}: [magenta]Cú pháp Markup [[ ]] không cân xứng[/]")
            
            # Cảnh báo nếu mở nhiều thẻ mà đóng quá ít (dễ gây lem màu)
            if q_text.count('[') > q_text.count('/]'):
                 if "[/" not in q_text and "[" in q_text: # Trường hợp chỉ mở ko đóng
                     pass # validate_file đã bắt ở trên, nhưng có thể bổ sung cảnh báo logic ở đây
        return errors

    def fix_ansi_in_file(self, path):
        """Tự động chuyển đổi mã ANSI sang Rich Markup và lưu lại file."""
        data = self.load_data(path, force=True)
        if not data: return False

        # Ánh xạ mã màu ANSI sang Rich Markup
        ansi_map = {
            '31': 'red', '91': 'bright_red',
            '32': 'green', '92': 'bright_green',
            '33': 'yellow', '93': 'bright_yellow',
            '34': 'blue', '94': 'bright_blue',
            '35': 'magenta', '95': 'bright_magenta',
            '36': 'cyan', '96': 'bright_cyan',
            '37': 'white', '97': 'bright_white',
            '90': 'grey50'
        }
        ansi_rx = re.compile(r'(?:\x1b\[|\[)(\d+)m')
        
        changed = False
        for row in data:
            for i in range(1, min(len(row), 5)): # Xử lý các cột nội dung
                val = str(row[i])
                if ansi_rx.search(val):
                    # Thay vì dùng [/], dùng cơ chế tự đóng của Rich nếu có thể, 
                    # nhưng đơn giản nhất là đảm bảo reset style về mặc định.
                    row[i] = ansi_rx.sub(lambda m: f"[{ansi_map.get(m.group(1), 'white')}]" if m.group(1) != '0' else "[/]", val)
                    changed = True
        
        if changed:
            self.save_data(path, data)
            return True
        return False