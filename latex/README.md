# نسخۀ LaTeX پایان‌نامه

[PDF نهایی](thesis.pdf) · [منبع اصلی](main.tex) · [شرح تبدیل و اصلاحات](MIGRATION.md) · [گزارش کنترل نهایی](results/validation.json)

موتور ساخت **XeLaTeX**، بستۀ فارسی **XePersian** و قلم متن فارسی **B Zar** با نسخۀ ضخیم واقعی است. قلم لاتین **Latin Modern Roman** است. قالب ظاهری از PDF موجود در مخزن بازسازی شده است؛ فایل قالب رسمی دانشگاه یا Word کامل در دسترس نبود.

## ساخت PDF

از ریشۀ مخزن:

```bash
# Debian / Ubuntu، در محیطی با مجوز نصب بسته
sudo apt-get install latexmk texlive-xetex texlive-lang-arabic texlive-latex-extra fonts-dejavu
bash latex/build.sh
```

در TeX Live نیز بسته‌های `xepersian`، `bidi`، `pgf` و `latexmk` لازم‌اند. جدول‌ها و شکل‌های نتایج در مخزن قرار دارند؛ ساخت PDF به دیتاست، اجرای Python یا آموزش دوبارۀ مدل‌ها وابسته نیست. خروجی `latex/thesis.pdf` است و فایل‌های موقت در `latex/build/` ساخته می‌شوند. `latexmk` تعداد دور لازم برای تثبیت فهرست‌ها و ارجاع‌ها را اجرا می‌کند.

در محیط ابری این کار، بستۀ فارسیِ Debian پس از کنترل امضای مخزن و SHA-256، به‌صورت محلی در `/workspace/.texlive` نصب شده است؛ `build.sh` این مسیر را شناسایی می‌کند. برای نصب عادی TeX Live به این مسیر نیازی نیست.

قلم‌ها همراه با مأخذ و هش در [fonts](fonts/SOURCE.md) قرار دارند. اعداد متن با B Zar و اعداد فرمول‌ها لاتین‌اند. نشانه‌های جداکنندۀ عددیِ فاقد گلیف در B Zar از DejaVu Sans تأمین می‌شوند. برای اضافه پس از «ه»، نویسۀ «ۀ» به کار رفته است. ترتیب بسته‌ها در `sbu-thesis.sty` را حفظ کنید؛ XePersian باید پس از بسته‌های مؤثر بر جهت متن بارگذاری شود.

## ساختار منبع

- `frontmatter/`: صفحه‌های آغازین، سپاسگزاری، چکیده‌ها و جلد انگلیسی؛ تشکر از هر دو داور در پاراگراف سوم سپاسگزاری است.
- `chapters/`: مقدمه، چهار فصل اصلی و نتیجه‌گیری؛ روش و نتایج متمرکز و مشارکتی در فایل‌های جدا هستند.
- `appendices/`، `acronyms.tex`، `glossary.tex` و `references.tex`: پنج پیوست، اختصارات، واژه‌نامه و منابع.
- `figures/`: شکل‌های برداری LaTeX، نمودارهای نتایج و تصاویر استخراج‌شده؛ نسخۀ قدیمیِ شکل‌های جایگزین‌شده فقط بایگانی شده است.
- `results/`: خروجی‌های عددی، منشأ داده‌ها، نسخۀ اجراشدۀ نوت‌بوک متمرکز و جدول‌های تولیدشده.
- `scripts/`: استخراج منابع، اجرای نوت‌بوک، تولید جدول‌ها و کنترل PDF.

## کنترل و بازتولید نتایج

دستورهای این بخش از ریشۀ مخزن اجرا می‌شوند. برای کنترل PDF و بازتولید جدول‌ها محیط Python 3.12 مستقل بسازید:

```bash
python3.12 -m venv /tmp/thesis-analysis
/tmp/thesis-analysis/bin/pip install -r latex/requirements-analysis.txt
/tmp/thesis-analysis/bin/python -B latex/scripts/validate.py
```

کنترل شامل شمارش خطاهای مدل، سازگاری معیارها، منشأ نوت‌بوک‌ها، صحت تقسیم کلاینت‌ها، ارجاع‌ها و پیوندهای داخلی، اندازه و تعداد صفحه‌ها، قلم تعبیه‌شده و خطاهای تایپوگرافی است. گزارش قابل ذخیره با `--report latex/results/validation.json` تولید می‌شود.

برای بازسازی تصاویر استخراج‌شده، خروجی‌های ذخیره‌شدۀ مشارکتی و جدول‌ها:

```bash
/tmp/thesis-analysis/bin/python -B latex/scripts/extract_assets.py
/tmp/thesis-analysis/bin/python -B latex/scripts/extract_federated_results.py
/tmp/thesis-analysis/bin/python -B latex/scripts/generate_tables.py
bash latex/build.sh
/tmp/thesis-analysis/bin/python -B latex/scripts/validate.py
```

نوت‌بوک اصلاح‌شدۀ متمرکز هنگام دریافت خروجی نداشت؛ نسخۀ کامل آن با تنظیم‌های اصلی اجرا شده و در [executed.ipynb](results/models/executed.ipynb) نگهداری می‌شود. اجرای دوبارۀ آن اختیاری و زمان‌بر است:

```bash
/tmp/thesis-analysis/bin/python -m ipykernel install --sys-prefix --name thesis-results
/tmp/thesis-analysis/bin/python -B latex/scripts/run_models.py /absolute/path/Suicide_Detection.csv \
  --work-dir /tmp/thesis-model-run
/tmp/thesis-analysis/bin/python -B latex/scripts/generate_tables.py
bash latex/build.sh
/tmp/thesis-analysis/bin/python -B latex/scripts/validate.py --report latex/results/validation.json
```

دیتاست اصلی از مجموعۀ `nikhileswarkomati/suicide-watch` است. نسخۀ استفاده‌شده از [بایگانی عمومی فشرده](https://raw.githubusercontent.com/KoreanMSG/anymo-ml/main/Suicide_Detection.csv.gz) دریافت و هش فایل CSV بازشده با هش ثبت‌شده در نوت‌بوک مشارکتی تطبیق داده شد:

```text
1ec16b065a2fae36488de16e8abfc326586a576a25901e09467223e545ddd295
```

این کنترل در `run_models.py` پیش از اجرا الزامی است. دادۀ خام در مخزن بازنشر نشده است. نسخه‌های علمی و تنظیم‌های اجرا در [فرادادۀ اجرا](results/models/run_metadata.json) ثبت شده‌اند. در جدول نسخه‌های خود نوت‌بوک، نام توزیع `xgboost` یافت نمی‌شود؛ فراهم‌کنندۀ نصب‌شده `xgboost-cpu==3.4.1` است و واردسازی و آموزش XGBoost با موفقیت انجام شده است. این تفاوت در [منشأ نتایج](results/models/provenance.json) ثبت شده است.

خروجی‌های مشارکتی از اجرای ذخیره‌شدۀ نوت‌بوک ارسالی استخراج شده‌اند. بنچمارک‌های رمزنگاری نیز از CSVهای موجود مخزن می‌آیند. این دو دسته، در این تبدیل دوباره اجرا نشده‌اند. تفاوت پروتکل‌ها و محدودۀ مقایسۀ آن‌ها در متن پایان‌نامه توضیح داده شده است.
