# 🚀 همیار کد رشید | Rashid Code Assistant v2

> **Monorepo:** FastAPI + Next.js 15 + Postgres + Redis + ARQ — branch `feature/rashid-agent-v2`  
> راه‌اندازی: [docs/quickstart-fa.md](docs/quickstart-fa.md)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-yellow.svg)](https://python.org)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()

## معرفی | Introduction

**همیار کد رشید** یک ابزار هوشمند و قدرتمند برای مدیریت، بهینه‌سازی و اعمال تغییرات دقیق در کدهای برنامه‌نویسی است. این ابزار با استفاده از هوش مصنوعی پیشرفته، تحلیل کد را انجام داده و پیشنهادهای عملی ارائه می‌دهد. طراحی شده برای توسعه‌دهندگان حرفه‌ای و مبتدیان، با رابط کاربری مدرن و سریع.

*Rashid Code Assistant is an intelligent tool for precise code management, optimization, and changes. Powered by AI, it analyzes code and provides actionable suggestions.*

**ساخته توسط علی رشیدی | Created by Ali Rashidi**

---

<div dir="rtl">

## 🌟 ویژگی‌های کلیدی | Key Features

- ✅ **تغییرات دقیق و بدون نقص در کد** | Precise, flawless code changes
- 🔍 **تحلیل هوشمند و بهینه‌سازی** | Smart analysis & optimization
- ✨ **پیاده‌سازی قابلیت‌های جدید** | Implementation of new features
- 🧹 **اصلاح نام‌ها و پاک‌سازی کد** | Rename variables & code cleanup
- 🌐 **پشتیبانی چندزبانه** | Multi-language support (Python, JS, HTML, CSS, etc.)
- ⚡ **رابط کاربری سریع و مدرن** | Fast, modern UI with dark mode
- 🔄 **سیستم بکاپ خودکار** | Automatic backup system
- 🤖 **ادغام با هوش مصنوعی** | AI-powered code assistance via OpenAI API
- 📱 **پشتیبانی از موبایل** | Responsive design
- 🔒 **امنیت بالا** | High security with path restrictions
- 📊 **گزارش‌گیری پیشرفته** | Advanced logging and reporting

</div>

---

## 📋 پیش‌نیازها | Prerequisites

- **Python 3.11+** | Python 3.11+
- **Node.js 20+** و npm | Node.js 20+ and npm
- **Docker Desktop** (Postgres + Redis) | Docker Desktop
- **کلید API Metis/OpenAI** در `.env` | API key in `.env`
- راهنمای کامل: [docs/quickstart-fa.md](docs/quickstart-fa.md)

---

## ⚙️ نصب و اجرا | Installation & Setup

```powershell
git clone <repo-url> rashid-agent
cd rashid-agent
copy .env.example .env   # سپس METIS_API_KEY را پر کنید

pip install -e ".[dev]"
.\scripts\infra-up.ps1
.\scripts\migrate.ps1
.\scripts\dev.ps1          # API :8000

# ترمینال دوم — UI
cd frontend && npm install && npm run dev   # :3000

# اختیاری — worker
.\scripts\dev-worker.ps1
```

Legacy UI قدیمی (`legacy/main.py`) منسوخ است؛ `python main.py` در ریشه فقط پیام راهنما می‌دهد. از stack بالا استفاده کنید.

---

## 📖 نحوه استفاده | Usage Guide

### شروع کار | Getting Started

1. **انتخاب مسیر پروژه**: از طریق دکمه "انتخاب مسیر پروژه" در رابط وب، پوشه پروژه خود را انتخاب کنید.

2. **ارسال درخواست**: در فیلد متن، درخواست خود را به زبان طبیعی تایپ کنید (مثلاً "بهبود عملکرد کد" یا "اضافه کردن ویژگی جدید").

3. **بررسی پاسخ**: ابزار کدهای پروژه را تحلیل کرده و تغییرات پیشنهادی را نمایش می‌دهد.

4. **اعمال تغییرات**: تغییرات را بررسی کرده و با کلیک روی "اعمال تغییرات"، آنها را روی فایل‌ها اعمال کنید. سیستم بکاپ خودکار از تغییرات محافظت می‌کند.

### مثال‌های درخواست | Example Requests

- "تابع جدیدی برای مرتب‌سازی لیست اضافه کن."
- "کدهای تکراری را شناسایی و پاکسازی کن."
- "نام متغیرهای بدون معنی را به نام‌های استاندارد تغییر بده."
- "بهینه‌سازی عملکرد حلقه‌ها."
- "اضافه کردن قابلیت لاگ‌گیری به برنامه."

### نکات مهم | Important Notes

- **بکاپ خودکار**: هر تغییر در پوشه `backups` ذخیره می‌شود و می‌توانید نسخه‌های قبلی را بازیابی کنید.
- **پشتیبانی زبان‌ها**: پایتون، جاوا اسکریپت، HTML، CSS، جاوا، سی‌پلاس‌پلاس و غیره.
- **امنیت**: تغییرات فقط در مسیر پروژه انتخاب‌شده اعمال می‌شود و خارج از آن مجاز نیست.
- **پشتیبانی**: برای مشکلات، از بخش Issues در گیت‌هاب استفاده کنید.

---

## 🔧 تنظیمات پیشرفته | Advanced Configuration

- **متغیرهای محیطی اضافی**: علاوه بر `OPENAI_API_KEY`، می‌توانید تنظیمات دیگری مانند `DEBUG=True` اضافه کنید.
- **فایل config.txt**: مسیر پروژه پیش‌فرض در این فایل ذخیره می‌شود.
- **پورت API:** در `scripts/dev.ps1` و `docker-compose.yml` (پیش‌فرض: 8000). UI در `:3000`.
- **تنظیمات بکاپ**: تعداد نسخه‌های بکاپ را در `set_json.py` تنظیم کنید.

---

## ❓ سوالات متداول | FAQ

### چگونه کلید API را دریافت کنم؟
کلید API را از وب‌سایت OpenAI دریافت کنید و در فایل `.env` قرار دهید.

### آیا ابزار آفلاین کار می‌کند؟
خیر، ابزار نیاز به اتصال اینترنت برای ارتباط با API هوش مصنوعی دارد.

### چگونه تغییرات را لغو کنم؟
از سیستم بکاپ استفاده کنید و نسخه قبلی را بازیابی کنید.

---

## 🐛 مشکلات شناخته شده | Known Issues

- در برخی سیستم‌ها، انتخاب مسیر ممکن است نیاز به مجوزهای اضافی داشته باشد.
- اگر API پاسخ ندهد، اتصال اینترنت را بررسی کنید.

---

## 🤝 مشارکت | Contributing

از مشارکت شما در بهبود این پروژه استقبال می‌کنیم! راه‌های مشارکت:

- ⭐ **ستاره بزنید** به مخزن | Star the repository
- 🐛 **گزارش باگ‌ها** | Report bugs via Issues
- 🔄 **ارسال Pull Request** | Submit pull requests
- 💡 **پیشنهاد ویژگی‌ها** | Suggest new features

### راهنمای مشارکت | Contribution Guidelines

1. کد را از شاخه `main` کلون کنید.
2. تغییرات خود را در یک شاخه جداگانه اعمال کنید.
3. تست‌های لازم را اجرا کنید.
4. Pull Request ارسال کنید و تغییرات را توضیح دهید.

---

## 📄 مجوز | License

این پروژه تحت مجوز **MIT License** منتشر شده است. این مجوز اجازه استفاده، تغییر و توزیع آزاد را می‌دهد، به شرطی که کپی‌رایت حفظ شود.

---

## 📞 تماس و پشتیبانی | Contact & Support

- **ایجادکننده**: علی رشیدی | Ali Rashidi
- **ایمیل**: [your-email@example.com]
- **گیت‌هاب**: [https://github.com/your-repo/maho-code]
- **لینکدین**: [https://linkedin.com/in/your-profile]

برای سوالات، پیشنهادات یا گزارش باگ‌ها، لطفاً از طریق Issues در گیت‌هاب تماس بگیرید. ما پاسخگوی شما هستیم!

---

🇮🇷 **پشتیبانی فارسی** | 🇺🇸 **English Support** | 🌙 Dark Mode در UI

---

*آخرین به‌روزرسانی: ۱۴۰۳/۱۰/۰۶ | Last Updated: 2024-12-27*

</div>