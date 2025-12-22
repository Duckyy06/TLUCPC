import os
import re
import difflib
import html
import io
from flask import Flask, request, render_template, send_file, redirect, url_for, session

# --- 1. CẤU HÌNH ---
SECRET_KEY = 'group6_plagiarism_checker'

# --- 2. KHO DỮ LIỆU ---
USERS = {
    'admin': {'password': 'admin', 'role': 'admin'},
    'giangvien':  {'password': 'gv123', 'role': 'lecturer'},
    'sinhvien':  {'password': 'sv123', 'role': 'student'},
}

MEMORY_FILES = {} 

KEYWORDS = {
    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 
    'break', 'continue', 'import', 'def', 'class', 'public', 'private', 'return'
}
DATA_TYPES = {'int', 'string', 'float', 'double', 'char', 'bool', 'void'}

app = Flask(__name__, template_folder='frontend')
app.secret_key = SECRET_KEY

# --- 3. CLASS LOGIC ---
class PlagiarismLogic:
    def normalize_line(self, line):
        # 1. Xóa các lệnh Nhập/Xuất (I/O)
        line = re.sub(r'(std::)?(cout|cin|cerr)\s*(<<|>>).*?;', '', line) 
        line = re.sub(r'(printf|scanf|puts|gets|getchar)\s*\(.*?\);', '', line)
        line = re.sub(r'\bprint\s*\(.*?\)', '', line)
        line = re.sub(r'\binput\s*\(.*?\)', '', line)
        line = re.sub(r'System\.out\.print(ln|f)?\s*\(.*?\);', '', line)

        # 2. Xóa Boilerplate C++ (include, using namespace)
        line = re.sub(r'^\s*#include.*', '', line)
        line = re.sub(r'^\s*using\s+namespace.*', '', line)

        # 3. [MỚI] Xóa 'return 0;' và 'return;'
        # Giải thích: Regex này tìm từ khóa return, theo sau là số 0 (có thể có khoảng trắng), và dấu chấm phẩy
        line = re.sub(r'return\s+0\s*;', '', line) 
        line = re.sub(r'return\s*;', '', line)

        # Kiểm tra dòng rỗng
        if not line.strip() or line.strip() == ';': return ""
        if len(line.strip()) < 2 or line.strip() in ['{', '}', '};', '];', '):', 'else']: return ""
        
        # 4. Token hóa
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

    def calculate_score(self, content1, content2):
        norm_list1 = [self.normalize_line(line) for line in content1.splitlines()]
        norm_list2 = [self.normalize_line(line) for line in content2.splitlines()]
        clean1 = [x for x in norm_list1 if x.strip()]
        clean2 = [x for x in norm_list2 if x.strip()]
        if not clean1 or not clean2: return 0.0
        matcher = difflib.SequenceMatcher(None, clean1, clean2)
        return round(matcher.ratio() * 100, 2)

    def compare(self, f1, f2):
        content1 = MEMORY_FILES.get(f1, "")
        content2 = MEMORY_FILES.get(f2, "")
        return self.calculate_score(content1, content2)

    def get_max_similarity(self, target_filename):
        if target_filename not in MEMORY_FILES: return 0.0
        max_score = 0.0
        target_content = MEMORY_FILES[target_filename]
        for other_fname, other_content in MEMORY_FILES.items():
            if other_fname == target_filename: continue 
            score = self.calculate_score(target_content, other_content)
            if score > max_score: max_score = score
        return max_score

    def generate_comparison_html(self, f1, f2):
        content1 = MEMORY_FILES.get(f1, "")
        content2 = MEMORY_FILES.get(f2, "")
        lines1 = content1.splitlines(); lines2 = content2.splitlines()
        norm_lines1 = [self.normalize_line(line) for line in lines1]
        norm_lines2 = [self.normalize_line(line) for line in lines2]
        matcher = difflib.SequenceMatcher(None, norm_lines1, norm_lines2)
        
        rows = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            segment1 = lines1[i1:i2]; segment2 = lines2[j1:j2]
            max_len = max(len(segment1), len(segment2))
            segment1 += [""] * (max_len - len(segment1))
            segment2 += [""] * (max_len - len(segment2))
            css_class = ""
            if tag == 'equal': css_class = "match"     
            elif tag == 'replace': css_class = "diff"  
            elif tag == 'delete': css_class = "diff"
            elif tag == 'insert': css_class = "diff"

            for k in range(max_len):
                row_class = css_class
                if tag == 'equal':
                     if not self.normalize_line(segment1[k]).strip() or not self.normalize_line(segment2[k]).strip():
                         row_class = ""
                
                rows.append({
                    'class': row_class,
                    'num1': i1+k+1 if k<(i2-i1) else '',
                    'txt1': segment1[k],
                    'num2': j1+k+1 if k<(j2-j1) else '',
                    'txt2': segment2[k]
                })
        
        # Xử lý hậu kỳ: Bỏ highlight dòng khai báo hàm nếu nội dung không trùng
        for i in range(len(rows)):
            current_row = rows[i]
            if current_row['class'] == 'match':
                txt = current_row['txt1'].strip()
                is_function_header = False
                if '(' in txt and ')' in txt:
                    start_word = txt.split('(')[0].strip().split()[-1] if txt.split('(')[0].strip() else ""
                    if start_word not in ['if', 'for', 'while', 'switch', 'catch', 'else']:
                         is_function_header = True
                
                if is_function_header:
                    body_matches = False
                    for j in range(i + 1, len(rows)):
                        next_row = rows[j]
                        if next_row['txt1'].strip(): 
                            if next_row['class'] == 'match':
                                body_matches = True
                            break 
                    if not body_matches:
                        current_row['class'] = "" 

        return rows

logic_handler = PlagiarismLogic()

# --- 4. ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = USERS.get(request.form['username'])
        if user and user['password'] == request.form['password']:
            session['username'] = request.form['username']
            session['role'] = user['role']
            if user['role'] == 'admin': return redirect(url_for('manage_users')) 
            else: return redirect(url_for('dashboard'))    
        else:
            error = "Sai tên đăng nhập hoặc mật khẩu!"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'username' not in session or session['role'] != 'admin': return "Cấm", 403
    error = None
    if request.method == 'POST':
        new_user = request.form['username']
        if new_user in USERS: error = "Đã tồn tại!"
        else:
            USERS[new_user] = {'password': request.form['password'], 'role': request.form['role']}
            create_account_list()
            return redirect(url_for('manage_users'))
    return render_template('admin.html', users=USERS, error=error, my_user=session['username'])

@app.route('/delete_user/<username>')
def delete_user(username):
    if session.get('role') != 'admin': return "Cấm", 403
    if username != 'admin' and username in USERS: 
        del USERS[username]
        create_account_list()
    return redirect(url_for('manage_users'))

@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))
    if session['role'] == 'admin': return redirect(url_for('manage_users'))

    sorted_files = sorted(MEMORY_FILES.keys())
    similarity_map = {}
    if len(sorted_files) > 1:
        for fname in sorted_files: similarity_map[fname] = logic_handler.get_max_similarity(fname)
    else:
        for fname in sorted_files: similarity_map[fname] = 0.0
    
    return render_template('dashboard.html', 
                           files=MEMORY_FILES, 
                           file_list=sorted_files, 
                           role=session['role'], 
                           username=session['username'], 
                           scores=similarity_map)

@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    if session.get('role') != 'student': return "Cấm", 403
    if request.method == 'POST':
        for file in request.files.getlist("files"):
            if file.filename:
                try:
                    file_content = file.read().decode('utf-8', errors='ignore')
                    safe_name = f"{session['username']}_{file.filename}"
                    MEMORY_FILES[safe_name] = file_content
                except Exception as e:
                    print(f"Lỗi đọc file {file.filename}: {e}")
        return redirect(url_for('dashboard'))
    return render_template('upload.html')

@app.route('/download/<filename>')
def download_file(filename):
    if session.get('role') != 'lecturer': return "Cấm", 403
    if filename in MEMORY_FILES:
        content = MEMORY_FILES[filename]
        mem_file = io.BytesIO()
        mem_file.write(content.encode('utf-8'))
        mem_file.seek(0)
        return send_file(mem_file, as_attachment=True, download_name=filename, mimetype='text/plain')
    return "File không tồn tại", 404

@app.route('/delete/<filename>')
def delete_file(filename):
    if 'username' not in session: return redirect(url_for('login'))
    if session['role'] == 'admin': return "Cấm", 403
    
    owner_prefix = f"{session['username']}_"
    if session['role'] != 'admin' and not filename.startswith(owner_prefix): return "Cấm", 403
    
    if filename in MEMORY_FILES:
        del MEMORY_FILES[filename]
    return redirect(url_for('dashboard'))

@app.route('/scan')
def scan():
    if session.get('role') != 'lecturer': return "Cấm", 403
    filenames = list(MEMORY_FILES.keys())
    results = []
    for i in range(len(filenames)):
        for j in range(i + 1, len(filenames)):
            f1, f2 = filenames[i], filenames[j]
            score = logic_handler.compare(f1, f2)
            if score > 50: results.append({'f1': f1, 'f2': f2, 'score': score})
    results.sort(key=lambda x: x['score'], reverse=True)
    return render_template('report.html', data=results)

@app.route('/compare/<f1>/<f2>')
def compare_view(f1, f2):
    if session.get('role') != 'lecturer': return "Cấm", 403
    if f1 not in MEMORY_FILES or f2 not in MEMORY_FILES: return "File không tồn tại", 404
    score = logic_handler.compare(f1, f2)
    rows = logic_handler.generate_comparison_html(f1, f2)
    return render_template('compare.html', f1=f1, f2=f2, score=score, rows=rows)

def create_account_list():
    filename = "account.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("====================================================\n")
            f.write("           DANH SÁCH TÀI KHOẢN HỆ THỐNG             \n")
            f.write("====================================================\n")
            f.write(f"{'VAI TRÒ':<15} | {'TÊN ĐĂNG NHẬP':<20} | {'MẬT KHẨU':<10}\n")
            f.write("-" * 55 + "\n")
            sorted_users = sorted(USERS.items(), key=lambda item: item[1]['role'])
            for username, info in sorted_users:
                role_vn = "Khác"
                if info['role'] == 'admin': role_vn = "QUẢN TRỊ VIÊN"
                elif info['role'] == 'lecturer': role_vn = "Giảng viên"
                elif info['role'] == 'student': role_vn = "Sinh viên"
                f.write(f"{role_vn:<15} | {username:<20} | {info['password']:<10}\n")
            f.write("-" * 55 + "\n")
        print(f"✅ Đã cập nhật file danh sách tài khoản: {filename}")
    except Exception as e:
        print(f"⚠️ Lỗi khi tạo file tài khoản: {e}")

if __name__ == "__main__":
    create_account_list()
    app.run(debug=True, port=5000)