"""Validate the manuscript build, references, graphics and numerical provenance."""
from pathlib import Path
import argparse
import collections
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import fitz
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LATEX = ROOT/'latex'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--preview', action='store_true', help='Typography-only check; does not validate central model results.')
parser.add_argument('--report', type=Path, help='Write a JSON report only after every check passes.')
args = parser.parse_args()
job = 'preview' if args.preview else 'main'
master = LATEX/'build/preview.tex' if args.preview else LATEX/'main.tex'
seen = set()
sources = []


def visit(path):
    path = path.resolve()
    assert path.is_file(), f'Missing input: {path}'
    if path in seen:
        return
    seen.add(path)
    text = path.read_text()
    sources.append((path,text))
    for target in re.findall(r'\\input\{([^}]+)\}', text):
        visit(LATEX/(target if Path(target).suffix else target+'.tex'))


visit(master)
combined = '\n'.join(text for _,text in sources)
labels = re.findall(r'\\label\{([^}]+)\}', combined)
duplicates = [key for key,count in collections.Counter(labels).items() if count>1]
assert not duplicates, f'Duplicate labels: {duplicates}'
references = set(re.findall(r'\\(?:ref|eqref|pageref)\{([^}]+)\}',combined))
assert references <= set(labels), f'Unresolved source references: {references-set(labels)}'
bib = set(re.findall(r'\\bibitem\{([^}]+)\}',combined))
bib_entries = re.findall(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})',combined,re.S)
assert all(len(body.strip())>25 for _,body in bib_entries), 'Empty or truncated bibliography entry.'
citations = {key.strip() for match in re.findall(r'\\cite\{([^}]+)\}',combined) for key in match.split(',')}
assert citations <= bib, f'Missing bibliography entries: {citations-bib}'
assert {f'ref{i}' for i in range(1,183)} <= bib, 'Original bibliography is incomplete.'
assert not re.search(r'\\(?:includepdf|includegraphics).*?پایان',combined), 'Source thesis pages must not replace editable text.'
graphics = []
superseded = {str((LATEX/row['path']).resolve()) for row in
              json.loads((LATEX/'figures/original/manifest.json').read_text()) if row['superseded']}
for path,text in sources:
    for target in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',text):
        candidates = [LATEX/target, LATEX/'figures'/target]
        if not Path(target).suffix:
            candidates = [Path(str(c)+ext) for c in candidates for ext in ['.pdf','.png','.jpeg','.jpg']]
        match = next((candidate for candidate in candidates if candidate.is_file()),None)
        assert match is not None, f'Missing graphic in {path.name}: {target}'
        assert '/old-' not in str(match), f'Superseded model figure still printed: {target}'
        assert str(match.resolve()) not in superseded, f'Superseded workflow still printed: {target}'
        graphics.append(match)
    for figure in re.findall(r'\\begin\{figure\}.*?\\end\{figure\}',text,re.S):
        assert r'\caption{' in figure and r'\label{' in figure, f'Uncaptioned/unlabelled figure in {path}'

log = (LATEX/f'build/{job}.log').read_text()
assert 'Missing character:' not in log, 'Missing font glyphs in TeX log.'
assert not re.search(r'(?:Reference|Citation).*?undefined',log), 'Undefined rendered cross-reference or citation.'
assert 'There were undefined references' not in log
assert 'Label(s) may have changed' not in log, 'Cross-references need another build.'
assert not re.search(r'LaTeX Font Warning: Font shape.*undefined',log), 'Unresolved font style.'
overfull = [(axis,float(size)) for axis,size in re.findall(r'Overfull \\([hv])box \(([0-9.]+)pt',log)]
assert not overfull, f'Overfull boxes require layout review: {overfull}'
pdf = LATEX/f'build/{job}.pdf'
doc = fitz.open(pdf)
assert len(doc)>60, 'Unexpectedly incomplete thesis.'
assert all(abs(page.rect.width-595.276)<2 and abs(page.rect.height-841.89)<2 for page in doc), 'Non-A4 page found.'
text = '\n'.join(page.get_text() for page in doc)
minimum_text = 100000 if args.preview else 140000
assert len(text)>minimum_text, 'Unexpectedly little editable text in manuscript.'
assert len(doc.get_toc())>60, 'Expected structured PDF outline is missing.'
for page in doc:
    for link in page.get_links():
        if link['kind']==fitz.LINK_GOTO:
            assert 0<=link['page']<len(doc), f'Invalid internal link on physical page {page.number+1}'
font_listing = subprocess.check_output(['pdffonts',str(pdf)],text=True)
assert 'BZar' in font_listing and 'BZarBold' in font_listing, 'Required B Zar regular and bold fonts not embedded.'
aux = (LATEX/f'build/{job}.aux').read_text()
last = re.search(r'\\zref@newlabel\{LastPage\}.*?\\abspage\{(\d+)\}',aux)
assert last and int(last[1])==len(doc), 'Absolute page count does not match the rendered PDF.'


def numeric_rows(label):
    """Read printed numerical table bodies, excluding captions and column labels."""
    tail = combined.split(r'\label{'+label+'}',1)[1].split(r'\end{table}',1)[0]
    body = tail.split(r'\midrule',1)[1].split(r'\bottomrule',1)[0]
    return [[float(value) for value in re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?',line)]
            for line in body.split(r'\\') if line.strip()]


def same_numbers(label, expected):
    actual = numeric_rows(label)
    assert len(actual)==len(expected), f'Printed row count differs: {label}'
    for a,b in zip(actual,expected):
        assert len(a)==len(b) and all(abs(x-y)<1e-8 for x,y in zip(a,b)), f'Printed values differ: {label}: {a} vs {b}'

federated = pd.read_csv(LATEX/'results/federated/cell-26-table-0.csv')
assert list(federated.n_clients)==[10,20,50,100]
assert list(federated.test_accuracy.round(4))==[0.9158,0.9093,0.893,0.87]
partition = pd.read_csv(LATEX/'results/federated/cell-13-table-0.csv')
assert all(abs(partition.n_clients*partition.mean_rows-148380)<1e-7)
same_numbers('tab:fl-partition',partition[['n_clients','min_rows','mean_rows','max_rows',
                                        'min_positive_fraction','max_positive_fraction']].values.tolist())
same_numbers('tab:fl-selected',federated[['n_clients','threshold','test_accuracy',
    'test_precision_positive','test_recall_positive','test_f1_positive','test_f1_macro']].values.tolist())
same_numbers('tab:fl-ranking',federated[['n_clients','test_roc_auc','test_average_precision',
    'test_fn','test_fp','pipeline_wall_seconds']].values.tolist())
fixed = pd.read_csv(LATEX/'results/federated/cell-26-table-1.csv')
same_numbers('tab:fl-fixed',fixed[['n_clients','test_accuracy','test_precision_positive',
    'test_recall_positive','test_f1_positive','test_f1_macro']].values.tolist())
split_counts = pd.read_csv(LATEX/'results/models/split_counts.csv')
same_numbers('tab:fl-split',[[r.negative,r.positive,r.total,round(r.positive/r.total,6)]
                           for _,r in split_counts.iterrows()])
for k,cell in [(10,18),(20,20),(50,22),(100,24)]:
    metrics = pd.read_csv(LATEX/f'results/federated/cell-{cell:02d}-table-0.csv')
    selected = metrics[(metrics.split=='test') & (metrics.setting=='validation_selected')].iloc[0]
    assert selected.tn+selected.fp+selected.fn+selected.tp==46342
    assert abs((selected.tn+selected.tp)/46342-selected.accuracy)<0.000051
    row = federated[federated.n_clients==k].iloc[0]
    assert abs(row.test_fn-selected.fn)<1e-9 and abs(row.test_fp-selected.fp)<1e-9
metadata = json.loads((LATEX/'results/federated/source.json').read_text())
assert hashlib.sha256((ROOT/metadata['source_notebook']).read_bytes()).hexdigest()==metadata['source_sha256']
for row in json.loads((LATEX/'results/notebook-inputs.json').read_text()):
    assert hashlib.sha256((ROOT/row['repository_path']).read_bytes()).hexdigest()==row['repository_sha256']

if not args.preview:
    result = LATEX/'results/models'
    meta = json.loads((result/'run_metadata.json').read_text())
    assert meta['cv_folds']==3 and meta['search_iterations']==10 and meta['seed']==42
    assert meta['word2vec']['vector_size']==100 and meta['word2vec']['epochs']==5
    assert meta['dataset_sha256']=='1ec16b065a2fae36488de16e8abfc326586a576a25901e09467223e545ddd295'
    val = pd.read_csv(result/'validation_metrics.csv')
    assert len(val)==4 and len(set(val.model))==4
    ranked = val.sort_values(['f1_positive','f1_macro','roc_auc','model'],ascending=[False,False,False,True],kind='mergesort')
    assert ranked.iloc[0]['model']==meta['best_model']
    test = pd.read_csv(result/'final_test_metrics.csv').set_index('setting')
    chosen = test.loc['Validation-selected']
    matrix = pd.read_csv(result/'final_test_confusion.csv',index_col=0).to_numpy()
    tn,fp,fn,tp = matrix.ravel()
    assert matrix.shape==(2,2) and matrix.sum()==46342
    assert abs(chosen.accuracy-(tn+tp)/matrix.sum())<1e-12
    assert abs(chosen.f1_positive-2*tp/(2*tp+fp+fn))<1e-12
    same_numbers('tab:models-validation',val[['threshold','accuracy','precision_positive',
        'recall_positive','f1_positive','f1_macro','roc_auc']].round(4).values.tolist())
    same_numbers('tab:models-test',test[['threshold','accuracy','precision_positive',
        'recall_positive','f1_positive','roc_auc','average_precision']].round(4).values.tolist())
    same_numbers('tab:models-errors',[[tn,fp,fn,tp]])
    notebook = json.loads((result/'executed.ipynb').read_text())
    original = json.loads((ROOT/'Notebooks/finding-the-best-model-fixed.ipynb').read_text())
    for expected,executed in zip(original['cells'],notebook['cells']):
        assert ''.join(expected['source'])==''.join(executed['source']), 'Original notebook cell changed during execution.'
    assert hashlib.sha256((ROOT/'Notebooks/finding-the-best-model-fixed.ipynb').read_bytes()).hexdigest()==meta['source_notebook_sha256']
    code = [c for c in notebook['cells'] if c['cell_type']=='code' and ''.join(c['source']).strip()]
    assert code and all(c.get('execution_count') is not None for c in code)
    assert not any(o.get('output_type')=='error' for c in code for o in c.get('outputs',[]))
    assert (LATEX/'thesis.pdf').read_bytes()==pdf.read_bytes(), 'Published artifact differs from checked build.'
    assert r'\BestModel' not in text and 'در حال محاسبه' not in text
    ack = (LATEX/'frontmatter/acknowledgements.tex').read_text().split('\n\n')[2]
    assert 'دکتر هادی فراهانی' in ack and 'دکتر سعید رضا خردپیشه' in ack
    outline = doc.get_toc()
    fa_page = next(row[2]-1 for row in outline if row[1]=='چکیده')
    en_page = next(row[2]-1 for row in outline if row[1]=='چکیدۀ انگلیسی')
    assert 'Word2Vec' in doc[fa_page].get_text(), 'Persian abstract missing body.'
    assert 'Keywords:' in doc[en_page].get_text() and 'privacy.' in doc[en_page].get_text(), 'English abstract exceeds one page.'
    print(f'PASS: full model notebook completed ({len(code)} code cells), four validation models, final test and confusion counts verified.')
print(f'PASS: {len(doc)} A4 pages, {len(sources)} editable inputs, {len(labels)} unique labels, '
      f'{len(bib)} bibliography entries and {len(graphics)} graphic placements.')
print('PASS: embedded B Zar regular/bold, complete page count, internal links, zero missing glyphs and zero overfull boxes.')
print('PASS: archived federated metrics, partition sizes and uploaded-notebook provenance verified.')
if args.preview:
    print('TYPOGRAPHY PREVIEW ONLY: central model results and the final master are not validated by this run.')
if args.report:
    report = {
        'status':'PASS', 'checked_utc':datetime.now(timezone.utc).isoformat(),
        'preview_only':args.preview, 'pdf':str(pdf.relative_to(ROOT)),
        'published_pdf':'latex/thesis.pdf' if not args.preview else None,
        'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
        'physical_a4_pages':len(doc), 'editable_text_characters':len(text),
        'editable_tex_inputs':len(sources), 'unique_labels':len(labels),
        'bibliography_entries':len(bib), 'graphic_placements':len(graphics),
        'pdf_outline_entries':len(doc.get_toc()), 'missing_glyphs':0,
        'undefined_references':0, 'overfull_boxes':0,
        'b_zar_regular_and_bold_embedded':True,
        'federated_client_counts':[10,20,50,100],
        'printed_numerical_tables_match_csv':True,
        'federated_evidence':'Archived outputs in the supplied notebook; not rerun.',
        'crypto_evidence':'Existing repository benchmark CSVs; not rerun.',
    }
    if not args.preview:
        report.update({'model_notebook_completed_code_cells':len(code),
                       'best_model':meta['best_model'], 'selected_threshold':meta['selected_threshold'],
                       'test_samples':int(matrix.sum()), 'test_accuracy':float(chosen.accuracy),
                       'test_positive_f1':float(chosen.f1_positive)})
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Saved validation report:',args.report)
