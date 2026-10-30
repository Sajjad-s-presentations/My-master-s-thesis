"""Extract original illustrations without rasterising whole thesis pages."""
from pathlib import Path
import hashlib
import json
import fitz

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / 'پایان نامه نهایی.pdf'
OUT = ROOT / 'latex/figures/original'
OUT.mkdir(parents=True, exist_ok=True)

names = {
    2: 'university-logo', 28: 'federated-architecture', 34: 'literature-overview',
    41: 'nlp-workflow', 44: 'text-cleaning', 57: 'random-forest-flow',
    60: 'old-random-forest-confusion', 62: 'decision-tree-flow',
    66: 'old-decision-tree-confusion', 67: 'xgboost-flow',
    72: 'old-xgboost-confusion', 73: 'bayes-model',
    79: 'old-naive-bayes-confusion', 84: 'old-threshold-analysis',
    87: 'old-error-distribution', 94: 'aes-shamir-workflow',
    98: 'elgamal-workflow', 101: 'paillier-workflow', 104: 'benaloh-workflow',
    112: 'crypto-key-generation', 113: 'crypto-encryption',
    115: 'crypto-total-time', 118: 'crypto-performance', 121: 'sbhe-workflow',
    132: 'sbhe-performance', 133: 'sbhe-phases', 134: 'sbhe-phase-shares',
    135: 'sbhe-scalability', 140: 'dena-architecture', 172: 'university-logo-en',
}
document = fitz.open(PDF)
manifest = []
for page_number, page in enumerate(document, 1):
    for number, image in enumerate(page.get_images(full=True), 1):
        extracted = document.extract_image(image[0])
        stem = names.get(page_number, f'page-{page_number:03d}')
        if number > 1:
            stem += f'-{number}'
        path = OUT / (stem + '.' + extracted['ext'])
        path.write_bytes(extracted['image'])
        manifest.append({
            'page': page_number, 'path': str(path.relative_to(ROOT / 'latex')),
            'width': extracted['width'], 'height': extracted['height'],
            'sha256': hashlib.sha256(extracted['image']).hexdigest(),
            'superseded': stem.startswith('old-'),
        })
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(f'Extracted {len(manifest)} illustrations; original page text is not used as an image.')
