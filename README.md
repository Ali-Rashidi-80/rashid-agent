<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>README - همیار کد رشید</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .lang-btn { background: #007bff; color: white; border: none; padding: 10px 20px; cursor: pointer; margin-bottom: 20px; }
        .lang-btn:hover { background: #0056b3; }
        .lang { display: none; }
        .lang.default { display: block; }
        h1, h2 { color: #007bff; }
        code { background: #f8f8f8; padding: 2px 4px; border-radius: 4px; }
        pre { background: #f8f8f8; padding: 10px; border-radius: 4px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <button class="lang-btn" onclick="toggleLang()">تغییر زبان / Change Language</button>
        
        <div id="fa" class="lang default">
            <h1>همیار کد رشید</h1>
            <p>این پروژه یک ابزار هوشمند برای کمک به برنامه‌نویسان در مدیریت و تغییرات کدهای برنامه‌نویسی است. ساخته شده توسط علی رشیدی.</p>
            <h2>ویژگی‌ها</h2>
            <ul>
                <li>تغییرات دقیق و بدون نقص در کد</li>
                <li>تحلیل و بهینه‌سازی کد</li>
                <li>پیاده‌سازی قابلیت‌های جدید</li>
                <li>پیشنهاد قابلیت‌های جدید</li>
                <li>اصلاح نام توابع و متغیرها</li>
                <li>پاک‌سازی کدهای اضافی</li>
            </ul>
            <h2>نصب و اجرا</h2>
            <p>برای نصب وابستگی‌ها:</p>
            <pre><code>pip install -r requirements.txt</code></pre>
            <p>برای اجرای سرور:</p>
            <pre><code>python main.py</code></pre>
            <p>سپس به آدرس <code>http://127.0.0.1:8000</code> بروید.</p>
            <h2>مشارکت</h2>
            <p>مشارکت‌ها خوش‌آمد هستند! لطفاً یک Issue باز کنید یا Pull Request ارسال کنید.</p>
            <h2>مجوز</h2>
            <p>این پروژه تحت مجوز MIT منتشر شده است.</p>
        </div>
        
        <div id="en" class="lang">
            <h1>Rashid Code Assistant</h1>
            <p>This project is an intelligent tool to assist programmers in managing and modifying programming codes. Created by Ali Rashidi.</p>
            <h2>Features</h2>
            <ul>
                <li>Precise and flawless code changes</li>
                <li>Code analysis and optimization</li>
                <li>Implementation of new features</li>
                <li>Suggestion of new features</li>
                <li>Correction of function and variable names</li>
                <li>Cleanup of redundant code</li>
            </ul>
            <h2>Installation and Running</h2>
            <p>To install dependencies:</p>
            <pre><code>pip install -r requirements.txt</code></pre>
            <p>To run the server:</p>
            <pre><code>python main.py</code></pre>
            <p>Then go to <code>http://127.0.0.1:8000</code>.</p>
            <h2>Contributing</h2>
            <p>Contributions are welcome! Please open an Issue or send a Pull Request.</p>
            <h2>License</h2>
            <p>This project is released under the MIT License.</p>
        </div>
    </div>
    
    <script>
        function toggleLang() {
            const fa = document.getElementById('fa');
            const en = document.getElementById('en');
            if (fa.style.display === 'none') {
                fa.style.display = 'block';
                en.style.display = 'none';
            } else {
                fa.style.display = 'none';
                en.style.display = 'block';
            }
        }
    </script>
</body>
</html>
