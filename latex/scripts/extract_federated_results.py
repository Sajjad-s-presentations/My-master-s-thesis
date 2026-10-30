"""Export tables/figures already stored in the supplied federated notebook."""
from pathlib import Path
from io import StringIO
import base64
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'Notebooks/federated_xgboost_10_20_50_100.ipynb'
nb = json.loads(source.read_text())
tables = ROOT / 'latex/results/federated'
figures = ROOT / 'latex/figures/federated'
tables.mkdir(parents=True, exist_ok=True)
figures.mkdir(parents=True, exist_ok=True)
manifest = []
for index, cell in enumerate(nb['cells']):
    table_number = image_number = 0
    for output in cell.get('outputs', []):
        data = output.get('data', {})
        if 'text/html' in data and '<table' in ''.join(data['text/html']):
            frame = pd.read_html(StringIO(''.join(data['text/html'])))[0]
            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = [next((part for part in col if not part.startswith('Unnamed:')),
                                      f'index_{i}') for i, col in enumerate(frame.columns)]
            else:
                frame.columns = [('row' if str(c).startswith('Unnamed:') else c) for c in frame.columns]
            path = tables / f'cell-{index:02d}-table-{table_number}.csv'
            frame.to_csv(path, index=False)
            manifest.append({'cell': index, 'type': 'table',
                             'path': str(path.relative_to(ROOT)), 'rows': len(frame),
                             'columns': list(map(str, frame.columns))})
            table_number += 1
        if 'image/png' in data:
            raw = data['image/png']
            if isinstance(raw, list):
                raw = ''.join(raw)
            path = figures / f'cell-{index:02d}-figure-{image_number}.png'
            path.write_bytes(base64.b64decode(raw))
            manifest.append({'cell': index, 'type': 'figure', 'path': str(path.relative_to(ROOT))})
            image_number += 1
metadata = {'source_notebook': str(source.relative_to(ROOT)),
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'dataset_sha256': '1ec16b065a2fae36488de16e8abfc326586a576a25901e09467223e545ddd295',
            'precision': 'Rounded values archived in notebook HTML outputs; no full-precision predictions inferred.',
            'artifacts': manifest}
(tables / 'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
print(f'Extracted {sum(a["type"]=="table" for a in manifest)} tables and '
      f'{sum(a["type"]=="figure" for a in manifest)} figures.')
