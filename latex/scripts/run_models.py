"""Execute the supplied corrected notebook, export real results, retain provenance.

Does not alter its model/search settings or use the test set for model selection.
The original notebook stays unchanged; an executed copy and CSVs are archived.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('dataset', type=Path)
parser.add_argument('--work-dir', type=Path, default=ROOT.parent/'thesis-output',
                    help='External working/cache directory; defaults to a sibling of the checkout.')
parser.add_argument('--kernel-name', default='thesis-results', help='Registered Jupyter kernel.')
args = parser.parse_args()
expected = '1ec16b065a2fae36488de16e8abfc326586a576a25901e09467223e545ddd295'
assert hashlib.sha256(args.dataset.read_bytes()).hexdigest() == expected
source = ROOT / 'Notebooks/finding-the-best-model-fixed.ipynb'
output = ROOT / 'latex/results/models'
output.mkdir(parents=True, exist_ok=True)
os.environ['SUICIDE_DATA_PATH'] = str(args.dataset.resolve())
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '2'
os.environ['OMP_NUM_THREADS'] = '2'
execution_root = args.work_dir.expanduser().resolve()
for variable,subdir in [('MPLCONFIGDIR','config/matplotlib'),
                        ('IPYTHONDIR','config/ipython'),
                        ('JUPYTER_RUNTIME_DIR','runtime/jupyter')]:
    directory = execution_root/subdir
    directory.mkdir(parents=True,exist_ok=True)
    os.environ[variable] = str(directory)
work = execution_root/'models-execution'
work.mkdir(parents=True,exist_ok=True)
nb = nbformat.read(source, as_version=4)
nb.cells.append(nbformat.v4.new_markdown_cell(
    '## Thesis export\nAdded by `latex/scripts/run_models.py` after the original '
    'notebook completes. Exports existing results without refitting or test-set tuning.'))
nb.cells.append(nbformat.v4.new_code_cell(r'''
import json, hashlib, sys
export_root = Path(EXPORT_DIRECTORY)
figure_root = export_root.parents[1] / 'figures/models'
figure_root.mkdir(parents=True, exist_ok=True)
validation_table.to_csv(export_root / 'validation_metrics.csv', index=False)
training_summary.to_csv(export_root / 'training_summary.csv')
final_test_results.to_csv(export_root / 'final_test_metrics.csv')
coverage_table.to_csv(export_root / 'vocabulary_coverage.csv')
split_counts = pd.DataFrame([
    {'split': name, 'negative': int((frame['label']==0).sum()),
     'positive': int(frame['label'].sum()), 'total': len(frame)}
    for name, frame in [('train', train_df), ('validation', validation_df), ('test', test_df)]])
split_counts.to_csv(export_root / 'split_counts.csv', index=False)
pd.DataFrame(classification_report(y_test, final_predictions, labels=[0,1],
    output_dict=True, zero_division=0)).to_csv(export_root / 'final_test_classification.csv')
for model_name in fitted_models:
    slug = model_name.lower().replace(' ', '-')
    p = validation_probabilities[model_name]
    cutoff = selected_thresholds[model_name]
    matrix = confusion_matrix(y_validation, p >= cutoff, labels=[0,1])
    pd.DataFrame(matrix, index=['actual_negative','actual_positive'],
        columns=['predicted_negative','predicted_positive']).to_csv(export_root / f'validation_confusion_{slug}.csv')
    threshold_curves[model_name].to_csv(export_root / f'validation_thresholds_{slug}.csv', index=False)
    fig, ax = plt.subplots(figsize=(5.6,4.6))
    ConfusionMatrixDisplay(matrix, display_labels=['non-suicide','suicide']).plot(
        ax=ax, cmap='Blues', values_format='d', colorbar=False)
    ax.set_title(f'{model_name}: validation, threshold={cutoff:.2f}')
    fig.tight_layout(); fig.savefig(figure_root / f'validation-confusion-{slug}.pdf'); plt.close(fig)
matrix = confusion_matrix(y_test, final_predictions, labels=[0,1])
pd.DataFrame(matrix, index=['actual_negative','actual_positive'],
    columns=['predicted_negative','predicted_positive']).to_csv(export_root / 'final_test_confusion.csv')
fig, axes = plt.subplots(1,3,figsize=(16,4.5))
ConfusionMatrixDisplay(matrix, display_labels=['non-suicide','suicide']).plot(ax=axes[0],cmap='Blues',values_format='d',colorbar=False)
axes[0].set_title(f'{best_name}: final test, threshold={best_threshold:.2f}')
RocCurveDisplay.from_predictions(y_test,test_probabilities,ax=axes[1],name=best_name)
axes[1].plot([0,1],[0,1],'--',color='gray')
PrecisionRecallDisplay.from_predictions(y_test,test_probabilities,ax=axes[2],name=best_name)
fig.tight_layout();fig.savefig(figure_root/'final-test.pdf');plt.close(fig)
fig, axes=plt.subplots(2,2,figsize=(11,8))
for ax,(model_name,curve) in zip(axes.ravel(),threshold_curves.items()):
    for metric in ['accuracy','precision_positive','recall_positive','f1_positive']:
        ax.plot(curve['threshold'],curve[metric],label=metric)
    ax.axvline(selected_thresholds[model_name],color='black',linestyle='--')
    ax.set(title=model_name,xlabel='Threshold',ylabel='Validation score',ylim=(0,1.02))
axes[0,0].legend(fontsize=7)
fig.tight_layout();fig.savefig(figure_root/'validation-thresholds.pdf');plt.close(fig)
metadata = {'best_model':best_name,'selected_threshold':best_threshold,'seed':SEED,
    'dataset_sha256':hashlib.sha256(Path(os.environ['SUICIDE_DATA_PATH']).read_bytes()).hexdigest(),
    'versions':versions,'python':sys.version.split()[0], 'cv_folds':CV_FOLDS,
    'search_iterations':SEARCH_ITERATIONS,'word2vec':W2V_CONFIG,
    'best_parameters':{name:search.best_params_ for name,search in search_results.items()},
    'selection':'validation positive F1, macro F1, ROC AUC, model name; final test only for frozen winner',
    'source_notebook_sha256':SOURCE_SHA256}
(export_root/'run_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print('EXPORTED:', export_root, '| best model:',best_name,'| threshold:',best_threshold)
'''.replace('EXPORT_DIRECTORY', repr(str(output))).replace('SOURCE_SHA256', repr(hashlib.sha256(source.read_bytes()).hexdigest()))))

def progress(cell, cell_index, **kwargs):
    print(time.strftime('%Y-%m-%d %H:%M:%S'), 'starting cell', cell_index, flush=True)

def save_progress(cell, cell_index, **kwargs):
    nbformat.write(nb, output / 'executed.ipynb')
    print(time.strftime('%Y-%m-%d %H:%M:%S'), 'completed cell', cell_index, flush=True)

client = NotebookClient(nb, kernel_name=args.kernel_name, timeout=14400,
    resources={'metadata': {'path': str(work)}},
    on_cell_start=progress, on_cell_executed=save_progress)
try:
    client.execute()
finally:
    nbformat.write(nb, output / 'executed.ipynb')
assert (output / 'run_metadata.json').is_file(), 'Result export did not complete.'
print('Complete corrected-model notebook executed successfully.', flush=True)
