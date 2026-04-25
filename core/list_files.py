import os
import json

PROGRAMMING_EXTENSIONS = (
    '.py', '.pyw', '.pyi', '.pyx',
    '.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.mts', '.cts',
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh',
    '.cs', '.cshtml', '.csx',
    '.java', '.jar', '.jsp', '.kt', '.kts',
    '.html', '.htm', '.css', '.scss', '.sass', '.less',
    '.go', '.rs', '.swift', '.dart',
    '.php', '.rb', '.pl', '.pm', '.sh', '.bash', '.zsh', '.lua',
    '.r', '.m',
    '.sql', '.json', '.yaml', '.yml', '.toml', '.xml', '.md',
    '.txt', '.text'
)



def list_files_in_directory(directory):

    file_paths = []

    file_info_list = []



    # مسیر پوشه والد برای بررسی pubspec.yaml

    parent_dir = os.path.dirname(directory)

    pubspec_path = os.path.join(parent_dir, 'pubspec.yaml')



    # بررسی اینکه آیا پروژه فلاتری است

    if os.path.isfile(pubspec_path):

        file_paths.append(pubspec_path)

        try:

            with open(pubspec_path, "r", encoding="utf-8") as f:

                content = f.read()

            lines = content.splitlines()

            numbered_content = "\n".join([f"Line {i+1}: {line}" for i, line in enumerate(lines)])

            file_info_list.append({

                "text": f"اسم فایل: pubspec.yaml\nمسیر فایل: {pubspec_path}\nتعداد خطوط: {len(lines)}\nشروع کد:\n{numbered_content}"

            })

        except Exception as e:

            file_info_list.append({"text": f"خطا در خواندن pubspec.yaml: {str(e)}"})



    # پیمایش دایرکتوری

    for root, _, files in os.walk(directory):

        if 'backups' in root:

            continue

        

        for file in files:

            # استفاده از tuple پسوندها برای فیلتر سریع

            if not file.lower().endswith(PROGRAMMING_EXTENSIONS):

                continue



            file_path = os.path.join(root, file)

            file_paths.append(file_path)



            try:

                with open(file_path, "r", encoding="utf-8") as f:

                    content = f.read()

                lines = content.splitlines()

                numbered_content = "\n".join([f"Line {i+1}: {line}" for i, line in enumerate(lines)])

                line_count = len(lines)

            except Exception as e:

                numbered_content = f"خطا در خواندن فایل: {str(e)}"

                line_count = 0



            file_info_list.append({

                "text": f"اسم فایل: {file}\nمسیر فایل: {file_path}\nتعداد خطوط: {line_count}\nشروع کد:\n{numbered_content}"

            })



    return json.dumps(file_paths, ensure_ascii=False, indent=4), json.dumps(file_info_list, ensure_ascii=False, indent=4)



# تست اجرا (استفاده از raw string برای جلوگیری از خطای unicodeescape)
# if __name__ == "__main__":
#     paths, infos = list_files_in_directory(r'C:\Users\fani\Desktop\MahoCode')
#     print("File Paths:\n", paths)
#     print("\nFile Infos:\n", infos)