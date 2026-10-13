"""Package source and demonstration outputs; omit secrets, caches and model weights."""
from pathlib import Path
import zipfile
import os

if __name__=='__main__':
    root=Path(__file__).resolve().parent; target=root/'dist/bo1_intelligent_data_platform.zip'; target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        excluded={'.git','.venv','__pycache__','models','.cache','.archive','dist','logs'}
        for directory,folders,files in os.walk(root):
            folders[:]=[name for name in folders if name not in excluded]
            for name in files:
                path=Path(directory)/name; relative=path.relative_to(root)
                if name=='.env' or path.suffix=='.pyc': continue
                archive.write(path,arcname=str(Path('bo1_intelligent_data_platform')/relative))
    print(target)
