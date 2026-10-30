"""Generate manuscript numbers from measured CSVs; never substitute estimates."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LATEX = ROOT / 'latex'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--benchmarks-only', action='store_true')
args = parser.parse_args()


def table(title, label, headings, rows, spec, resize=False):
    lines = [r'\begin{table}[htbp]', r'\centering', r'\small',
             r'\caption{'+title+'}', r'\label{'+label+'}']
    if resize:
        lines.append(r'\resizebox{\textwidth}{!}{%')
    lines += [r'\begin{tabular}{'+spec+'}', r'\toprule',
              ' & '.join(headings)+r' \\', r'\midrule']
    lines += [' & '.join(map(str,row))+r' \\' for row in rows]
    lines += [r'\bottomrule', r'\end{tabular}'+('}' if resize else ''), r'\end{table}']
    return '\n'.join(lines).replace('هٔ','ۀ')+'\n'


def number(value):
    return r'\en{--}' if pd.isna(value) else f'{value:.4f}'


benchmark = pd.read_csv(ROOT/'Crypto/results/benchmark_all.csv')
assert len(benchmark)==15 and set(benchmark.homomorphic_test)=={'PASS'}
names = {'damgard_jurik':r'Damgård--Jurik ($s=1$)', 'paillier':'Paillier',
         'benaloh':'Benaloh', 'rsa':'RSA', 'elgamal':'ElGamal'}
parts = []
for operation,title,label in [
    ('additive','زمان‌های طرح‌های جمعی برای ۱۰۰ پیام و تجمیع وزن‌دار','tab:crypto-additive'),
    ('multiplicative','زمان‌های آزمون ضرب دو پیام؛ رمزگذاری و رمزگشایی جداگانه اندازه‌گیری نشده‌اند','tab:crypto-multiplicative')]:
    rows = [[r'\en{'+names[row['scheme']]+'}',int(row.key_bits)] +
            [number(row[c]) for c in ['keygen_ms','encryption_ms','aggregation_ms','decryption_ms','total_ms']]
            for _,row in benchmark[benchmark.operation==operation].iterrows()]
    parts.append(table(title,label,['طرح','بیت','تولید کلید','رمزگذاری','تجمیع/آزمون','رمزگشایی','کل'],rows,'llrrrrr',True))
(LATEX/'results/crypto-benchmark-tables.tex').write_text('\n'.join(parts))

sbhe = pd.read_csv(ROOT/'Crypto/Benaloh_signcryption/results/benaloh_summary_results_20260823_180220.csv')
assert len(sbhe)==9
rows = [[int(r.bits),int(r.num_clients),number(r.total_avg_ms),number(r.total_std_ms)] for _,r in sbhe.iterrows()]
parts = [table('میانگین و انحراف معیار زمان کل در فایل خلاصهٔ ذخیره‌شده؛ واحد میلی‌ثانیه',
               'tab:sbhe-total',['بیت','کلاینت','میانگین کل','انحراف معیار'],rows,'rrrr')]
rows = [[int(r.bits),int(r.num_clients)]+[number(r[c]) for c in [
        'setup_avg_ms','registration_avg_ms','encryption_avg_ms','aggregation_avg_ms','decryption_avg_ms']]
        for _,r in sbhe.iterrows()]
parts.append(table('میانگین زمان مرحله‌های پروتکل در اجرای ذخیره‌شده؛ واحد میلی‌ثانیه',
                   'tab:sbhe-phases',['بیت','کلاینت','آماده‌سازی','ثبت هویت','رمزگذاری','تجمیع/بررسی','رمزگشایی'],rows,'rrrrrrr',True))
(LATEX/'results/sbhe-performance-tables.tex').write_text('\n'.join(parts))
if args.benchmarks_only:
    print('Generated the archived cryptographic benchmark tables.')
    raise SystemExit(0)

output = LATEX/'results/models'
metadata = json.loads((output/'run_metadata.json').read_text())
validation = pd.read_csv(output/'validation_metrics.csv')
test = pd.read_csv(output/'final_test_metrics.csv').set_index('setting')
assert len(validation)==4 and len(test)==2
ranked = validation.sort_values(['f1_positive','f1_macro','roc_auc','model'],ascending=[False,False,False,True],kind='mergesort')
best = ranked.iloc[0]
assert best['model']==metadata['best_model']
assert abs(best.threshold-metadata['selected_threshold'])<1e-12
selected = test.loc['Validation-selected']
default_test = test.loc['Default 0.50']
model_source = ROOT/'Notebooks/finding-the-best-model-fixed.ipynb'
assert hashlib.sha256(model_source.read_bytes()).hexdigest()==metadata['source_notebook_sha256']
pretty = {'Random Forest':'جنگل تصادفی','Decision Tree':'درخت تصمیم',
          'XGBoost':r'\en{XGBoost}','Naive Bayes voting':'رأی‌گیری بیز ساده'}
values = {'BestModel':pretty[best['model']], 'BestModelEnglish':best['model'],
          'BestThreshold':f'{best.threshold:.2f}', 'BestValFone':number(best.f1_positive),
          'BestTestAccuracyPercent':f'{100*selected.accuracy:.2f}',
          'BestTestPrecision':number(selected.precision_positive),
          'BestTestRecall':number(selected.recall_positive),
          'BestTestFone':number(selected.f1_positive), 'BestTestAUC':number(selected.roc_auc),
          'DefaultTestAccuracyPercent':f'{100*default_test.accuracy:.2f}',
          'DefaultTestFone':number(default_test.f1_positive),
          'DefaultTestRecall':number(default_test.recall_positive)}
(output/'summary.tex').write_text('\n'.join('\\newcommand{\\'+key+'}{'+value+'}' for key,value in values.items())+'\n')

rows = [[pretty[r['model']],f'{r.threshold:.2f}']+[number(r[c]) for c in [
    'accuracy','precision_positive','recall_positive','f1_positive','f1_macro','roc_auc']]
    for _,r in validation.iterrows()]
parts = [table('مقایسهٔ چهار مدل بر اعتبارسنجی؛ تمام معیارها در مقیاس صفر تا یک‌اند',
    'tab:models-validation',['مدل','آستانه','دقت کلی','دقت مثبت','بازیابی مثبت',r'$F_1$ مثبت',r'$F_1$ کلان',r'\en{ROC AUC}'],rows,'lrrrrrrr',True)]
rows = [[('پیش‌فرض' if setting=='Default 0.50' else 'منتخب اعتبارسنجی'),f'{r.threshold:.2f}']+
    [number(r[c]) for c in ['accuracy','precision_positive','recall_positive','f1_positive','roc_auc','average_precision']]
    for setting,r in test.iterrows()]
parts.append(table('ارزیابی آزمون فقط برای مدل منتخب؛ دو تنظیم آستانه برای همان مدل',
    'tab:models-test',['تنظیم','آستانه','دقت کلی','دقت مثبت','بازیابی مثبت',r'$F_1$ مثبت',r'\en{ROC AUC}',r'\en{AP}'],rows,'lrrrrrrr',True))
training = pd.read_csv(output/'training_summary.csv')
rows = [[pretty[r['model']],number(r.best_cv_score),number(r.fit_or_search_seconds)] for _,r in training.iterrows()]
parts.append(table('گزارش برازش و جست‌وجو؛ خط تیره یعنی جست‌وجوی اعتبارسنجی برای آن مدل تعریف نشده است',
    'tab:models-training',['مدل',r'بهترین $F_1$ در جست‌وجوی آموزش','زمان برازش/جست‌وجو (ثانیه)'],rows,'lrr'))
rows = []
for name, parameters in metadata['best_parameters'].items():
    fields = []
    for key,value in sorted(parameters.items()):
        key = key.removeprefix('classifier__').replace('_',r'\_')
        fields.append(r'\texttt{'+key+'}='+str(value).replace('_',r'\_'))
    rows.append([pretty[name],r'\engcell{'+', '.join(fields)+'}'])
parts.append(table('فراپارامترهای منتخب جست‌وجوی تصادفی؛ انتخاب فقط از اعتبارسنجی متقابلِ آموزش',
    'tab:models-hyperparameters',['مدل','مقدارهای منتخب'],rows,r'lp{0.62\textwidth}'))
coverage = pd.read_csv(output/'vocabulary_coverage.csv',index_col=0)
rows = [[{'train':'آموزش','validation':'اعتبارسنجی','test':'آزمون'}[i],int(r['rows']),
         number(r.token_coverage),int(r.all_oov_rows),number(r.all_oov_fraction)] for i,r in coverage.iterrows()]
parts.append(table('پوشش بازنمایی مدل منتخب؛ واژگان فقط از آموزش آموخته شده‌اند',
    'tab:models-coverage',['بخش','تعداد سند','پوشش توکن','سند کاملاً ناشناخته','سهم سند ناشناخته'],rows,'lrrrr'))
cm = pd.read_csv(output/'final_test_confusion.csv',index_col=0)
assert cm.shape==(2,2) and int(cm.to_numpy().sum())==46342
tn,fp,fn,tp = map(int,cm.to_numpy().ravel())
assert abs((tp+tn)/(tp+tn+fp+fn)-selected.accuracy)<1e-12
assert abs(2*tp/(2*tp+fp+fn)-selected.f1_positive)<1e-12
parts.append(table('شمارش خطاهای مدل منتخب در آزمون، با آستانهٔ تثبیت‌شده',
    'tab:models-errors',[r'$TN$',r'$FP$',r'$FN$',r'$TP$'],[[tn,fp,fn,tp]],'rrrr'))
(output/'tables.tex').write_text('\n'.join(parts))
provenance = {
    'dataset_sha256':metadata['dataset_sha256'],
    'dataset_original_source':'nikhileswarkomati/suicide-watch',
    'checksum_matched_archive':'https://raw.githubusercontent.com/KoreanMSG/anymo-ml/main/Suicide_Detection.csv.gz',
    'raw_dataset_redistributed':False,
    'source_notebook_sha256':metadata['source_notebook_sha256'],
    'federated_notebook_sha256':hashlib.sha256((ROOT/'Notebooks/federated_xgboost_10_20_50_100.ipynb').read_bytes()).hexdigest(),
    'recorded_scientific_versions':metadata['versions'],
    'xgboost_provider':{'distribution':'xgboost-cpu','version':importlib.metadata.version('xgboost-cpu')},
    'best_model':metadata['best_model'], 'selection_uses_test':False,
    'manuscript_values_are_rounded_from_csv':True,
}
(output/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
print('Generated all measured model tables and abstract/conclusion values:',metadata['best_model'])
