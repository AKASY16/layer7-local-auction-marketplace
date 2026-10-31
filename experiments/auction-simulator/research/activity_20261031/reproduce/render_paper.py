"""Read-only PDF previews. Existing local renderer supplies missing capability."""
import sys
from pathlib import Path
VENDOR=Path(r'C:\Users\USER\Documents\Codex\2026-10-29\https-github-com-akasy16-layer7-local\work\new-materials-review-2026-10-31\vendor')
sys.path.insert(0,str(VENDOR))
import pymupdf
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'research/activity_20261031/paper_previews';OUT.mkdir(parents=True,exist_ok=True)
for name,path,pages in [('new_manuscript',ROOT/'research/papers/simonsohn_2010_revalidation/ebays_crowded_evenings_2010.pdf',[1,33,34,36,37,40]),
                       ('published',ROOT/'research/papers/C_Simonsohn_2010_CrowdedEvenings.pdf',[1,9,10])]:
    d=pymupdf.open(path)
    for p in pages:d[p-1].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(OUT/f'{name}_{p:02d}.png')
print('Rendered9source pages without editing PDF')
