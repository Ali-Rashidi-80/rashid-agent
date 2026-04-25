import os
import json
import re
from dotenv import load_dotenv
from .list_files import list_files_in_directory
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")  # استفاده از متغیر محیطی برای امنیت
)



def read_directory_path():

    config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.txt")

    try:

        with open(config_file_path, 'r') as file:

            directory_path = file.readline().strip()

            return directory_path

    except Exception as e:

        print(f"خطا در خواندن مسیر از فایل: {str(e)}")

        return None



def write_directory_path(new_path):

    config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.txt")

    try:

        with open(config_file_path, 'w') as file:

            file.write(new_path.strip())

        return True

    except Exception as e:

        print(f"خطا در نوشتن مسیر در فایل: {str(e)}")

        return False



def fix_and_parse_json(response_data):

    if isinstance(response_data, dict):

        return response_data

    if not response_data or not isinstance(response_data, str):

        return {'error': 'Invalid or empty response data'}

    response_data = response_data.strip()

    if not response_data:

        return {'error': 'Response data is empty'}

    # Extract JSON from code blocks

    pattern = re.compile(r'```json(.*?)```', re.DOTALL | re.IGNORECASE)

    match = pattern.search(response_data)

    if match:

        json_text = match.group(1).strip()

    else:

        pattern2 = re.compile(r'```(.*?)```', re.DOTALL)

        match2 = pattern2.search(response_data)

        if match2:

            json_text = match2.group(1).strip()

        else:

            json_text = response_data

    if not json_text:

        return {'error': 'No JSON content found'}

    # Clean up trailing commas in objects and arrays

    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)

    # Fix unclosed quotes (simple heuristic)

    if json_text.count('"') % 2 != 0:

        json_text += '"'

    # Fix unclosed braces and brackets

    open_braces = json_text.count('{') - json_text.count('}')

    json_text += '}' * open_braces

    open_brackets = json_text.count('[') - json_text.count(']')

    json_text += ']' * open_brackets

    if json_text[0] not in ['{', '[']:

        return {'error': 'Response does not start with valid JSON structure'}

    try:

        return json.loads(json_text)

    except json.JSONDecodeError as e:

        return {'error': f'JSON decode error: {str(e)}'}



def payload(user_text: str) -> dict:

    json_list, json_info = list_files_in_directory(read_directory_path())

    text_ListDirectory = json.dumps(json_list)

    json_format = [{

        "type": "",

        "start_number_line": 0,

        "code": "",

        "Total_lines": 0,

        "end_number_line": 1,

        "new_code": ""

    }]

    json_format2 = [{"path": "",

                 "edits": json_format,

                 "info": "",

                 "log": ""}]
    
    
    instructions_path = os.path.join(os.path.dirname(__file__), 'instructions.txt')
    with open(instructions_path, 'r', encoding='utf-8') as f:
        dastor = f.read()


    payload_dict = {
        "system_instruction": {
            "parts": [
                {"text": """Just create the outputs in the following JSON format:\n{"message": "", "pip": "", "edits": [{"path": "", "edits": [{"type": "", "start_number_line": 0, "code": "", "Total_lines": 0, "end_number_line": 1, "new_code": ""}], "info": "", "log": ""}], "log": ""}\nThis json will be used for changes to the programming files and must be filled in carefully.\nNo changes should be made to the above Jason structure."""},
                {"text": """هویت یابی:\nاسمت دستیار هوشمند رشید است\nبرای مدیریت و تغییرات در پروژه های برنامه نویسی آفریده شدی\nخیلی کامل هستی و دارای درو و تفکر و میتونی به درخواست های کاربر جواب کامل بدی\nسازندت علی رشیدی هست\nوظیفته تمامی درخواست های کاربر را با دقت انجام بدی\nاگه کاربر ازت خواست سرچ انجام بدی ، انجام بده و جوابش بده"""},
                {"text": """توانایی هات :\n1- تغیرات دقیق و بدون نقص در کد\n2- تحلیل کد ها و بهینه سازی\n3- پیاده سازی قابلیت های جدید\n4- پیشنهاد قابلیت های جدید در کد\n5-اصلاح نام توابع و متغییر های بدون مفهوم به نام های استاندارد\n6- پاک سازی کامند های اضافی در کد و کامند گزاری دقیق تر و بهتر"""},
                {"text": "نکته :امکان افزودن دایرکتوری جدید برای ایجاد یک کد ماژولار را داری و میتوانی دایرکتوری های جدیدی از خودت اضاف کنی"},
                {"text": dastor},
                {"text": """مهم : اگه صفحه ای مشکلات سینتکسی داشت وظیفه داری ویرایش های لازم برای خطا های سینتکسی اراعه بدی\nنکته : اگه کدی return Scaffold( این شکلی بود باید دقت کنی موقع ویرایش و دادن کد جدید return یا سکوپ دلیمیترها ها رو پاک نکنی که کد کاربر خراب شه و باید سینتکس هارو دقیق برسی کنی و برسی کنی اگه new_code با code جایگذین شه ، کد بدست اومده خطا نداشته باشه\nباید مستندات هر زبان کامل برسی کنی تا کد اشتباه ندی و از پارامتر های منسوخ شده هم استفاده نکنی\nدرصورت نیاز می توانی کل کد به یک باره ویرایش و در 1 ویرایش کد اصلاح شده کامل بدهی"""},
                {"text": "مهم : به هیچ عنوان نباید توی کدت Line 48: اینجور شماره لاین باشه و این ها فقط برای راهنمای خودت برای پیدا کردن مقادیر لاین نامبر ها یعنی start_number_line و end_number_line هستن "},
                {"text": "به زبان فارسی جواب کاربر بگو و میتونی درمورد دستوراتی که بهت داده شده به کاربر توضیح بدی "},
                {"text": "دستور : باید تا 1 خط قبل و بعد new_code رو به کاربر بدی درصورت وجود و توی لاین نامبر ها ام اون 2 خط اضافی در نظر بگیری"},
                {"text": "دستور : You must give your answer in one part only and in a Json structure without any additional explanation."}
            ]
        },
        "contents": [
            {"role": "user", "parts": json.loads(json_info)},
            {"role": "user", "parts": [{"text": "در ادامه لیست دایرکتوری فایل کد ها فرستاده می شود"}, {"text": text_ListDirectory}, {"text": user_text}]}
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "stopSequences": ["Title"],
            "temperature": 0.3131412,
            "topP": 1,
            "topK": 1
        },
        "tools": [{"google_search": {}}]
    }

    # ساخت پیام‌های ورودی
    messages = [
        {"role": "system", "content": json.dumps(payload_dict, ensure_ascii=False)},
        {"role": "user", "content": f"اطلاعات فایل‌ها: {json_info}"},
        {"role": "user", "content": f"لیست دایرکتوری: {text_ListDirectory}"},
        {"role": "user", "content": user_text}
    ]

    try:
        # ارسال درخواست به OpenAI
        response = client.chat.completions.create(
            
            model="grok-code-fast-1",  # یا مدل مورد نظر شما
            #model="gemini-3.1-flash-lite-preview",
            
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3131412
        )

        generated_text = response.choices[0].message.content
        print(generated_text)
        generated_js = fix_and_parse_json(generated_text)
        return generated_js

    except Exception as e:
        return {'error': str(e)}
