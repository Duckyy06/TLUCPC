import os
import re
import difflib

# Cấu hình
INPUT_FOLDER = 'assignments'
OUTPUT_FOLDER = 'output'
THRESHOLD = 0.8  # Chỉ báo cáo nếu giống nhau > 80%

# Danh sách từ khóa C++ để tránh đổi tên nhầm (Simplified list)
KEYWORDS = {
    'int', 'float', 'double', 'char', 'void', 'return', 'if', 'else', 
    'for', 'while', 'do', 'switch', 'case', 'break', 'continue', 
    'include', 'using', 'namespace', 'std', 'cout', 'cin', 'main'
}

class PlagiarismChecker:
    def __init__(self):
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
        self.files = {}

    def load_files(self):
        """Đọc tất cả file .cpp/.py trong thư mục assignments"""
        print("--- Đang tải file ---")
        for filename in os.listdir(INPUT_FOLDER):
            if filename.endswith((".cpp", ".py", ".c")):
                path = os.path.join(INPUT_FOLDER, filename)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.files[filename] = f.read()
        print(f"Đã tải {len(self.files)} file.")

    def normalize_code(self, source_code):
        """
        Bước 1 & 2: Preprocessing + Tokenization (giả lập)
        - Xóa comment
        - Đổi tên biến thành token chung (VAR)
        """
        # 1. Xóa comment (C++ style: // và /* ... */)
        text = re.sub(r'//.*', '', source_code)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

        # 2. Tách từ (Tokenize) đơn giản bằng Regex
        tokens = re.findall(r'\b\w+\b', text)
        
        # 3. Chuẩn hóa: Nếu không phải keyword thì đổi thành "TOKEN"
        # Điều này giúp phát hiện đạo văn dù sinh viên đổi tên biến (vd: count -> dem)
        normalized_tokens = []
        for token in tokens:
            if token in KEYWORDS or token.isdigit():
                normalized_tokens.append(token)
            else:
                normalized_tokens.append("VAR") # Đưa mọi tên biến về dạng VAR
        
        # Trả về chuỗi đã chuẩn hóa để so sánh logic
        return " ".join(normalized_tokens)

    def generate_html_report(self, file1, file2, content1, content2, score):
        """Tạo file HTML so sánh chi tiết giữa 2 bài"""
        
        # Sử dụng HtmlDiff của Python để tạo bảng so sánh side-by-side
        differ = difflib.HtmlDiff()
        html_content = differ.make_file(
            content1.splitlines(), 
            content2.splitlines(), 
            fromdesc=file1, 
            todesc=file2,
            context=True,  # Chỉ hiện các đoạn code xung quanh phần giống nhau
            numlines=5
        )

        # Thêm CSS tùy chỉnh để báo cáo đẹp hơn
        custom_css = """
        <style>
            body { font-family: sans-serif; padding: 20px; }
            h1 { color: #d9534f; }
            .diff_header { background-color: #e8e8e8; }
            td.diff_header { text-align: right; }
            .diff_next { background-color: #c0c0c0; }
            .diff_add { background-color: #dff0d8; }
            .diff_chg { background-color: #fcf8e3; }
            .diff_sub { background-color: #f2dede; }
        </style>
        """
        html_content = html_content.replace('</head>', f'{custom_css}</head>')
        
        # Thêm tiêu đề báo cáo
        header = f"<h1>CẢNH BÁO ĐẠO VĂN: {score}%</h1><hr>"
        html_content = html_content.replace('<body>', f'<body>{header}')

        report_name = f"{file1}_VS_{file2}.html"
        with open(os.path.join(OUTPUT_FOLDER, report_name), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return report_name

    def run(self):
        self.load_files()
        filenames = list(self.files.keys())
        n = len(filenames)
        
        summary_report = [] # Lưu danh sách tổng hợp
        
        print("\n--- Bắt đầu quét (O(N^2)) ---")
        for i in range(n):
            for j in range(i + 1, n):
                f1_name, f2_name = filenames[i], filenames[j]
                
                # Lấy nội dung gốc để hiển thị
                original_content1 = self.files[f1_name]
                original_content2 = self.files[f2_name]

                # Lấy nội dung đã chuẩn hóa để tính toán độ giống nhau
                norm1 = self.normalize_code(original_content1)
                norm2 = self.normalize_code(original_content2)

                # Thuật toán so sánh
                matcher = difflib.SequenceMatcher(None, norm1, norm2)
                similarity = matcher.ratio() * 100

                if similarity > (THRESHOLD * 100):
                    print(f"⚠ PHÁT HIỆN: {f1_name} - {f2_name} | Độ giống: {similarity:.2f}%")
                    
                    # Tạo file báo cáo chi tiết HTML
                    report_link = self.generate_html_report(f1_name, f2_name, original_content1, original_content2, round(similarity, 2))
                    
                    summary_report.append({
                        "pair": f"{f1_name} & {f2_name}",
                        "score": similarity,
                        "link": report_link
                    })
        
        # Tạo trang Index tổng hợp (Dashboard)
        self.create_dashboard(summary_report)

    def create_dashboard(self, data):
        """Tạo file index.html tổng hợp tất cả các trường hợp nghi vấn"""
        html = """
        <html><head><title>Báo cáo Đạo văn</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css">
        </head><body class="container mt-5">
        <h2 class="text-center mb-4">Kết quả Quét Đạo Văn Code</h2>
        <table class="table table-striped table-bordered">
            <thead class="thead-dark"><tr><th>Cặp sinh viên</th><th>Độ giống nhau</th><th>Chi tiết</th></tr></thead>
            <tbody>
        """
        # Sắp xếp danh sách từ cao xuống thấp
        data.sort(key=lambda x: x['score'], reverse=True)
        
        for item in data:
            color = "text-danger" if item['score'] > 90 else "text-warning"
            html += f"""
            <tr>
                <td>{item['pair']}</td>
                <td class="{color} font-weight-bold">{item['score']:.2f}%</td>
                <td><a href="{item['link']}" target="_blank" class="btn btn-primary btn-sm">Xem so sánh</a></td>
            </tr>
            """
        
        html += "</tbody></table></body></html>"
        
        with open(os.path.join(OUTPUT_FOLDER, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n✅ Đã hoàn tất! Mở file '{OUTPUT_FOLDER}/index.html' để xem báo cáo.")

if __name__ == "__main__":
    checker = PlagiarismChecker()
    checker.run()