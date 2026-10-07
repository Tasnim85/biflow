"""Package source and demonstration outputs; omit secrets, caches and model weights."""
from pathlib import Path
import zipfile

if __name__=='__main__':
    root=Path(__file__).resolve().parent; target=root/'dist/BO1_FINAL.zip'; target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob('*'):
            relative=path.relative_to(root)
            if not path.is_file() or any(p in ['.venv','__pycache__','models','.cache','.archive','dist','logs'] for p in relative.parts) or path.name=='.env' or path.suffix=='.pyc': continue
            archive.write(path,arcname=str(Path('BO1_FINAL')/relative))
    print(target)
