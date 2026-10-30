# پایان‌نامۀ کارشناسی ارشد سجاد رنجبر یزدی

«حفظ امنیت داده‌های حساس در پیش‌بینی خودکشی با رویکردی مبتنی بر یادگیری مشارکتی و رمزگذاری همریخت در پردازش زبان طبیعی»

- [PDF پایان‌نامه با قلم B Zar](latex/thesis.pdf)
- [منبع LaTeX](latex/main.tex) و [راهنمای ساخت](latex/README.md)
- [شرح اصلاحات و منشأ نتایج](latex/MIGRATION.md)
- [گزارش کنترل PDF و سازگاری نتایج](latex/results/validation.json)
- [اجرای کامل نوت‌بوک مقایسۀ مدل‌ها](latex/results/models/executed.ipynb)

فایل‌های نوت‌بوک اصلی در `Notebooks/` و پیاده‌سازی‌ها و بنچمارک‌های رمزنگاری در `Crypto/` نگهداری می‌شوند.

برای ساخت PDF از ریشۀ مخزن، پس از نصب XeLaTeX، XePersian و latexmk:

```bash
bash latex/build.sh
```
