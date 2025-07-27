import os

def count_lines_of_code(directory):
    extensions = ['.py', '.cpp', '.c', '.h', '.java', '.js', '.html', '.css']  # 可根据需要调整
    total_lines = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                    total_lines += sum(1 for _ in f)

    return total_lines

if __name__ == "__main__":
    directory = "."  # 当前目录
    total_lines = count_lines_of_code(directory)
    print(f"代码总行数: {total_lines}")