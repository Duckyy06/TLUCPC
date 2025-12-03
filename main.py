import os
import re
import difflib
import html

# --- CẤU HÌNH ---
INPUT_FOLDER = 'assignments'
OUTPUT_FOLDER = 'output'
THRESHOLD = 0.1  # Ngưỡng cảnh báo 10%

# Từ khóa logic
KEYWORDS = {
    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 
    'break', 'continue', 'import', 'def', 'class', 'public', 'private'
}
DATA_TYPES = {'int', 'string', 'float', 'double', 'char', 'bool', 'void'}

class PlagiarismChecker:
    def __init__(self):
        if not os.path.exists(OUTPUT_FOLDER): os.makedirs(OUTPUT_FOLDER)
        if not os.path.exists(INPUT_FOLDER): os.makedirs(INPUT_FOLDER)
        self.files = {}

    def load_files(self):
        print(f"--- Đang tải file từ '{INPUT_FOLDER}' ---")
        count = 0
        for filename in os.listdir(INPUT_FOLDER):
            if filename.endswith((".cpp", ".py", ".c", ".java")):
                path = os.path.join(INPUT_FOLDER, filename)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        self.files[filename] = f.read()
                    count += 1
                except: pass
        print(f"✅ Đã tải {count} file.")

    def is_boilerplate(self, line):
        line = line.strip()
        if len(line) < 2 or line in ['{', '}', '};', '];', '):', 'else']: return True
        patterns = [
            r'^#include', r'^using\s+namespace', r'^(int|void)\s+main\s*\(', 
            r'^return\s+\d+\s*;', r'^return\s*;',
            r'^(std::)?cout\s*<<', r'^(std::)?cin\s*>>', r'^printf\s*\(', r'^scanf\s*\(',
            r'^print\s*\(', r'.*=\s*input\s*\('
        ]
        for pat in patterns:
            if re.search(pat, line): return True
        return False

    def normalize_line(self, line):
        if self.is_boilerplate(line): return ""
        line = re.sub(r'"[^"]*"', ' __STR__ ', line)
        line = re.sub(r"'[^']*'", ' __CHAR__ ', line)
        line = re.sub(r'\b\d+\b', ' __NUM__ ', line)
        var_map = {}
        type_pattern = r'\b(int|string|float|double|char|bool|void)\s+([a-zA-Z_]\w*)'
        matches = re.findall(type_pattern, line)
        for dtype, var_name in matches:
            if var_name not in KEYWORDS: var_map[var_name] = f"VAR_{dtype.upper()}"
        tokens = re.findall(r'\b\w+\b|[+\-*/=<>!{};(),]', line)
        norm_tokens = []
        for t in tokens:
            if t in KEYWORDS or t in DATA_TYPES: norm_tokens.append(t)
            elif t in ['__STR__', '__CHAR__', '__NUM__']: norm_tokens.append(t)
            elif t in var_map: norm_tokens.append(var_map[t])
            elif re.match(r'[+\-*/=<>!{};(),]', t): norm_tokens.append(t)
            else: norm_tokens.append("VAR") 
        return " ".join(norm_tokens)

    # --- TẠO FILE LIST (Đã cập nhật nút Download) ---
    def create_file_list(self):
        print("Creating list.html...")
        sorted_files = sorted(self.files.keys())
        
        table_rows = ""
        modal_divs = ""
        
        for idx, fname in enumerate(sorted_files, 1):
            content = self.files[fname]
            line_count = len(content.splitlines())
            size_kb = len(content) / 1024
            code_id = f"code_content_{idx}"
            
            # Tạo hàng trong bảng (Thêm nút Tải xuống)
            table_rows += f"""
            <tr>
                <td>{idx}</td>
                <td><b>{fname}</b></td>
                <td>{line_count} dòng</td>
                <td>{size_kb:.2f} KB</td>
                <td>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-info" data-toggle="modal" data-target="#modal_{idx}">
                            👁️ Xem
                        </button>
                        <button type="button" class="btn btn-sm btn-success" onclick="downloadCode('{fname}', '{code_id}')">
                            ⬇ Tải về
                        </button>
                    </div>
                </td>
            </tr>
            """
            
            # Modal chứa code (Thêm ID cho thẻ code để JS lấy nội dung)
            modal_divs += f"""
            <div class="modal fade" id="modal_{idx}" tabindex="-1" role="dialog" aria-hidden="true">
              <div class="modal-dialog modal-lg" role="document">
                <div class="modal-content">
                  <div class="modal-header">
                    <h5 class="modal-title">{fname}</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                      <span aria-hidden="true">&times;</span>
                    </button>
                  </div>
                  <div class="modal-body">
                    <pre style="background:#f8f9fa; padding:10px; border:1px solid #ddd; max-height: 500px; overflow-y: auto;"><code id="{code_id}">{html.escape(content)}</code></pre>
                  </div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Đóng</button>
                    <button type="button" class="btn btn-success" onclick="downloadCode('{fname}', '{code_id}')">Tải file này</button>
                  </div>
                </div>
              </div>
            </div>
            """

        # HTML Structure (Thêm Script Download)
        html_content = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8"><title>Danh sách bài nộp</title>
            <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.16.0/umd/popper.min.js"></script>
            <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
            <script>
                function downloadCode(filename, elementId) {{
                    var text = document.getElementById(elementId).innerText;
                    var element = document.createElement('a');
                    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
                    element.setAttribute('download', filename);
                    element.style.display = 'none';
                    document.body.appendChild(element);
                    element.click();
                    document.body.removeChild(element);
                }}
            </script>
        </head>
        <body class="bg-light">
            <div class="container mt-5 bg-white p-4 shadow rounded">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h2 class="text-primary">📂 Danh sách bài tập ({len(sorted_files)} file)</h2>
                    <a href="index.html" class="btn btn-warning">📊 Xem Báo Cáo Đạo Văn</a>
                </div>
                <table class="table table-hover table-bordered">
                    <thead class="thead-dark">
                        <tr><th style="width: 50px">STT</th><th>Tên File</th><th>Độ dài</th><th>Dung lượng</th><th style="width: 150px">Thao tác</th></tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
            {modal_divs}
        </body>
        </html>
        """
        with open(os.path.join(OUTPUT_FOLDER, 'list.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Đã tạo file danh sách: {OUTPUT_FOLDER}/list.html")

    def generate_side_by_side_html(self, file1, file2, content1, content2, score):
        lines1 = content1.splitlines(); lines2 = content2.splitlines()
        norm_lines1 = [self.normalize_line(line) for line in lines1]
        norm_lines2 = [self.normalize_line(line) for line in lines2]
        matcher = difflib.SequenceMatcher(None, norm_lines1, norm_lines2)
        html_rows = ""
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            segment1 = lines1[i1:i2]; segment2 = lines2[j1:j2]
            max_len = max(len(segment1), len(segment2))
            segment1 += [""] * (max_len - len(segment1)); segment2 += [""] * (max_len - len(segment2))
            css_class_base = ""
            if tag == 'replace': css_class_base = "diff-change"
            elif tag == 'delete': css_class_base = "diff-delete"
            elif tag == 'insert': css_class_base = "diff-insert"
            for k in range(max_len):
                txt1 = segment1[k]; txt2 = segment2[k]; row_class = css_class_base
                if tag == 'equal':
                    if self.is_boilerplate(txt1) or self.is_boilerplate(txt2): row_class = "" 
                    else: row_class = "plagiarism-match"
                html_rows += f"""<tr class="{row_class}"><td class="line-num">{i1+k+1 if k<(i2-i1) else ""}</td><td class="code-col">{html.escape(txt1)}</td><td class="line-num">{j1+k+1 if k<(j2-j1) else ""}</td><td class="code-col">{html.escape(txt2)}</td></tr>"""
        
        full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>So sánh chi tiết</title><style>body{{font-family:sans-serif;background:#f4f4f4;padding:20px}}.container{{background:white;padding:20px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}}table{{width:100%;border-collapse:collapse;font-family:'Consolas',monospace;font-size:13px;table-layout:fixed}}td{{padding:2px 5px;border:1px solid #ddd;word-wrap:break-word}}.line-num{{width:30px;color:#999;text-align:right;background:#f9f9f9}}.code-col{{width:45%;white-space:pre-wrap}}.plagiarism-match{{background-color:#fff59d;border-bottom:1px solid #e6db74}}.diff-change{{color:#999}}.diff-delete{{background-color:#fff0f0}}.diff-insert{{background-color:#f0fff0}}</style></head><body><div class="container"><h2>Logic giống nhau: {score}%</h2><p><a href="index.html">⬅ Quay lại Báo cáo</a></p><table><thead><tr><th colspan="2">{file1}</th><th colspan="2">{file2}</th></tr></thead><tbody>{html_rows}</tbody></table></div></body></html>"""
        report_name = f"{file1}_VS_{file2}.html"
        with open(os.path.join(OUTPUT_FOLDER, report_name), 'w', encoding='utf-8') as f: f.write(full_html)
        return report_name

    def run(self):
        self.load_files()
        self.create_file_list() # Tạo file list.html
        filenames = list(self.files.keys())
        if len(filenames) < 2: return
        summary = []
        print("\n--- Bắt đầu so sánh ---")
        for i in range(len(filenames)):
            for j in range(i + 1, len(filenames)):
                f1, f2 = filenames[i], filenames[j]
                norm_list1 = [self.normalize_line(line) for line in self.files[f1].splitlines()]
                norm_list2 = [self.normalize_line(line) for line in self.files[f2].splitlines()]
                clean1 = [x for x in norm_list1 if x.strip()]
                clean2 = [x for x in norm_list2 if x.strip()]
                matcher = difflib.SequenceMatcher(None, clean1, clean2)
                score = round(matcher.ratio() * 100, 2)
                print(f"🔹 {f1} vs {f2} -> {score}%")
                if score >= (THRESHOLD * 100):
                    link = self.generate_side_by_side_html(f1, f2, self.files[f1], self.files[f2], score)
                    summary.append({'pair': f"{f1} vs {f2}", 'score': score, 'link': link})
        self.create_dashboard(summary)

    def create_dashboard(self, data):
        html = """<html><head><title>Báo cáo Đạo văn</title><link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css"></head><body class="container mt-5"><div class="d-flex justify-content-between align-items-center mb-4"><h2 class="text-danger">⚠️ Kết quả Quét Đạo Văn</h2><a href="list.html" class="btn btn-outline-primary">📂 Xem Danh sách File Gốc</a></div><table class="table table-bordered table-striped"><thead class="thead-dark"><tr><th>Cặp sinh viên</th><th>Độ giống (Logic)</th><th>Chi tiết</th></tr></thead><tbody>"""
        data.sort(key=lambda x: x['score'], reverse=True)
        if not data: html += "<tr><td colspan='3' class='text-center'>Không có cặp nào vượt ngưỡng cảnh báo.</td></tr>"
        for item in data:
            html += f"<tr><td>{item['pair']}</td><td class='font-weight-bold text-danger'>{item['score']}%</td><td><a href='{item['link']}' class='btn btn-primary btn-sm' target='_blank'>Xem chi tiết</a></td></tr>"
        html += "</tbody></table></body></html>"
        with open(os.path.join(OUTPUT_FOLDER, 'index.html'), 'w', encoding='utf-8') as f: f.write(html)
        print(f"\n✅ ĐÃ HOÀN TẤT! Mở '{OUTPUT_FOLDER}/list.html' để xem danh sách hoặc 'index.html' để xem báo cáo.")

if __name__ == "__main__":
    PlagiarismChecker().run()