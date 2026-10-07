"""Explicit, one-time model setup. Never called by the application."""
from pathlib import Path
from huggingface_hub import snapshot_download

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    path=snapshot_download('sentence-transformers/all-MiniLM-L6-v2',local_dir=root/'models/all-MiniLM-L6-v2',cache_dir=root/'models/.cache',
        revision='1110a243fdf4706b3f48f1d95db1a4f5529b4d41',
        allow_patterns=['*.json','*.txt','model.safetensors','1_Pooling/*'])
    print('Local model ready:',path)
