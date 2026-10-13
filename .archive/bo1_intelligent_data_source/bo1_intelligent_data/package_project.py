"""Package source and demonstration outputs; omit secrets, caches and model weights."""
from pathlib import Path
import zipfile

if __name__=='__main__':
    root=Path(__file__).resolve().parent; target=root.parent/'bo1_intelligent_data_source.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob('*'):
            relative=path.relative_to(root)
            if not path.is_file() or any(p in ['.venv','__pycache__','models','.cache'] for p in relative.parts) or path.name=='.env' or path.suffix=='.pyc': continue
            archive.write(path,arcname=str(Path(root.name)/relative))
        for name in ['run_demo.bat','run_demo.ps1']:
            archive.write(root.parent/name,arcname=name)
    print(target)
