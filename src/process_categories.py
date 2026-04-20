import os, csv, time
from src.core import console
from src.utils import _safe_input, _clear_screen, _handle_error
from rich.table import Table
from rich import box

class CategoryManager:
    def __init__(self):
        self.path = "data/filter_categories.csv"
        self.headers = ["num", "type_question", "type_keyword", "keyword"]

    def load_data(self):
        """Nạp dữ liệu từ file CSV cấu hình."""
        if not os.path.exists(self.path): return []
        data = []
        try:
            with open(self.path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    data.append(row)
        except Exception as e:
            _handle_error(f"❌ Lỗi đọc file categories: {e}")
        return data

    def save_data(self, data):
        """Xử lý trùng lặp, sắp xếp theo yêu cầu và đánh lại số thứ tự num."""
        # 1. Loại bỏ trùng lặp dựa trên keyword (không phân biệt hoa thường)
        seen = set()
        unique_data = []
        for item in data:
            kw = str(item.get('keyword', '')).strip()
            kw_lower = kw.lower()
            if kw_lower and kw_lower not in seen:
                unique_data.append(item)
                seen.add(kw_lower)
        
        # 2. Sắp xếp: type_keyword trước, sau đó tới keyword (theo yêu cầu)
        unique_data.sort(key=lambda x: (
            str(x.get('type_keyword', '')).lower(), 
            str(x.get('keyword', '')).lower()
        ))
        
        # 3. Đánh lại số thứ tự num từ 1 đến N
        for i, item in enumerate(unique_data, 1):
            item['num'] = str(i)
            
        try:
            with open(self.path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers, delimiter=';')
                writer.writeheader()
                writer.writerows(unique_data)
        except Exception as e:
            _handle_error(f"❌ Lỗi ghi file categories: {e}")

    def show_categories(self):
        """Hiển thị bảng danh sách từ khóa lọc hiện có."""
        data = self.load_data()
        if not data:
            console.print("\n[yellow]⚠️ Danh sách từ khóa lọc hiện đang trống.[/]")
            return []
            
        table = Table(title="🏷️ QUẢN LÝ TỪ KHÓA LỌC", box=box.ROUNDED, show_lines=True)
        table.add_column("Num", justify="right", style="cyan")
        table.add_column("Loại (primary/bool)", style="bold yellow")
        table.add_column("Nhóm nội dung", style="magenta")
        table.add_column("Từ khóa lọc", style="white")
        
        for row in data:
            table.add_row(
                row.get('num', ''), 
                row.get('type_question', ''), 
                row.get('type_keyword', ''), 
                row.get('keyword', '')
            )
        console.print(table)
        return data

    def add_category(self):
        while True:
            _clear_screen()
            self.show_categories()
            kw = _safe_input("🔍 Nhập từ khóa lọc mới (hoặc exit): ")
            if not kw: break
            
            tk = _safe_input("📂 Nhóm (vd: English, IT, General...): ")
            if tk is None: break
            
            tq = "primary"
            data = self.load_data()
            data.append({
                "num": "0", 
                "type_question": tq, 
                "type_keyword": tk or "General", 
                "keyword": kw
            })
            self.save_data(data)
            console.print("[green]✅ Đã thêm và tự động sắp xếp lại danh sách![/]"); time.sleep(0.8)

    def edit_category(self):
        while True:
            _clear_screen()
            data = self.show_categories()
            if not data: break
            
            num_val = lambda x: (x.isdigit() and any(d['num'] == x for d in data), x)
            num = _safe_input("🔢 Nhập STT (num) để sửa (hoặc exit): ", num_val)
            if not num: break
            
            item = next(d for d in data if d['num'] == num)
            new_kw = _safe_input(f"✏️ Từ khóa mới ({item['keyword']}): ")
            if new_kw is None: break
            if new_kw: item['keyword'] = new_kw
            
            tq_val = lambda x: (x.lower() in ['primary', 'bool'], x.lower())
            new_tq = _safe_input(f"🏷️ Loại mới ({item['type_question']}) [primary/bool]: ", tq_val)
            if new_tq is None: break
            if new_tq: item['type_question'] = new_tq
            
            new_tk = _safe_input(f"📂 Nhóm mới ({item['type_keyword']}): ")
            if new_tk is None: break
            if new_tk: item['type_keyword'] = new_tk
            
            self.save_data(data)
            console.print("[green]✅ Đã cập nhật và sắp xếp lại![/]"); time.sleep(0.8)

    def delete_category(self):
        while True:
            _clear_screen()
            data = self.show_categories()
            if not data: break
            
            num_val = lambda x: (x.isdigit() and any(d['num'] == x for d in data), x)
            num = _safe_input("🗑️ Nhập STT (num) để xoá (hoặc exit): ", num_val)
            if not num: break
            
            data = [d for d in data if d['num'] != num]
            self.save_data(data)
            console.print("[red]🗑️ Đã xoá thành công![/]"); time.sleep(0.8)