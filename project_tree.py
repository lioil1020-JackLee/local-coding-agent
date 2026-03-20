import os

def generate_final_clean_md():
    output_file = 'project_tree.md'
    # 補回完整的排除清單
    exclude = {
        'project_tree.md',
        'project_tree.py',
        'gen_tree.py',
        'py_file_lines.md',
        '.git',
        '__pycache__',
        '.venv',
        '.vscode',
        '.pytest_cache', 
        'uv.lock',
        '*.pyc',
        '.env',
        '.env.example'
    }

    def count_lines(file_path):
        if not file_path.endswith('.py'): return None
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except: return 0

    # 1. 收集資料並計算對齊寬度
    nodes = []
    max_tree_w = 0
    max_line_val = 0

    def scan(path, prefix=""):
        nonlocal max_tree_w, max_line_val
        try:
            items = sorted(os.listdir(path))
            # 過濾排除項目
            items = [i for i in items if i not in exclude and not any(i.endswith(x[1:]) for x in exclude if x.startswith('*'))]
            
            for i, item in enumerate(items):
                full_path = os.path.join(path, item)
                is_last = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                
                tree_text = f"{prefix}{connector}{item}"
                line_cnt = count_lines(full_path)
                
                nodes.append({'text': tree_text, 'lines': line_cnt})
                
                # 計算最大寬度
                max_tree_w = max(max_tree_w, len(tree_text))
                if line_cnt is not None:
                    max_line_val = max(max_line_val, line_cnt)

                if os.path.isdir(full_path):
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    scan(full_path, new_prefix)
        except: pass

    scan(".")
    if not nodes: return
    max_num_w = len(str(max_line_val))

    # 2. 寫入檔案
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Project Structure\n\n")
        
        for n in nodes:
            if n['lines'] is not None:
                # 檔案行：純文字對齊
                padding = " " * (max_tree_w - len(n['text']) + 5)
                num_str = str(n['lines']).rjust(max_num_w)
                f.write(f"  {n['text']}{padding}{num_str} lines  \n")
            else:
                # 目錄行
                f.write(f"  {n['text']}  \n")

    print(f"✅ 已生成完整排除的純淨版：{output_file}")

generate_final_clean_md()