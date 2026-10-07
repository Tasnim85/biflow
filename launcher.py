"""Reliable Windows/local launcher: one server, health check, then browser."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parent
LOGS=ROOT/'logs'
STATE=LOGS/'server.json'

def healthy(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/_stcore/health',timeout=2) as response:
            return response.status==200
    except Exception: return False

def process_alive(pid):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,int(pid))
        if not handle: return False
        code=wintypes.DWORD()
        try: return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally: kernel.CloseHandle(handle)
    try: os.kill(int(pid),0); return True
    except OSError: return False

def dependencies():
    required=['pandas','numpy','sklearn','networkx','streamlit','plotly','pydantic','langgraph']
    return [name for name in required if importlib.util.find_spec(name) is None]

def free_port():
    for port in range(8501,8512):
        try:
            with socket.socket() as candidate:
                candidate.bind(('127.0.0.1',port))
            return port
        except OSError: continue
    raise RuntimeError('Aucun port disponible entre 8501 et 8511.')

class NativeProcess:
    def __init__(self,pid): self.pid=pid
    def poll(self): return None if process_alive(self.pid) else 1
    def terminate(self): subprocess.run(['taskkill','/PID',str(self.pid),'/T','/F'],capture_output=True)

def start_server(command):
    if os.name=='nt':
        # Start-Process creates a native background service that survives the launcher.
        def ps(value): return "'"+str(value).replace("'","''")+"'"
        pid_file=LOGS/'launch_pid.txt'
        pid_file.unlink(missing_ok=True)
        script="$ErrorActionPreference='Stop'; $env:PYTHONUTF8='1'; $env:PYTHONUNBUFFERED='1'; $bo1Process=Start-Process -FilePath "+ps(command[0])+" -ArgumentList "+ps(subprocess.list2cmdline(command[1:]))+" -WorkingDirectory "+ps(ROOT)+" -WindowStyle Hidden -RedirectStandardOutput "+ps(LOGS/'server.log')+" -RedirectStandardError "+ps(LOGS/'server-error.log')+" -PassThru; [System.IO.File]::WriteAllText("+ps(pid_file)+",$bo1Process.Id.ToString())"
        encoded=base64.b64encode(script.encode('utf-16-le')).decode()
        # No captured pipes: inherited pipe handles can otherwise keep communicate()
        # waiting until the background server exits on Windows.
        with (LOGS/'launcher-error.log').open('w',encoding='utf-8') as error_log:
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=error_log,creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
        if result.returncode or not pid_file.exists(): raise RuntimeError((LOGS/'launcher-error.log').read_text(encoding='utf-8',errors='replace'))
        return NativeProcess(int(pid_file.read_text(encoding='utf-8').strip()))
    with (LOGS/'server.log').open('a',encoding='utf-8') as log:
        return subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)

def launch(open_browser=True):
    LOGS.mkdir(exist_ok=True)
    missing=dependencies()
    if missing:
        raise RuntimeError('Dependances absentes: '+', '.join(missing)+'. Lancez installer.bat une fois.')
    try:
        state=json.loads(STATE.read_text(encoding='utf-8'))
        if state.get('project')==str(ROOT) and process_alive(state['pid']) and healthy(state['port']):
            url=f"http://localhost:{state['port']}"
            print('BO1 est deja demarre: '+url,flush=True)
            if open_browser: webbrowser.open(url)
            return state
    except (OSError,ValueError,KeyError): pass
    port=free_port()
    command=[sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),'--server.port',str(port),
        '--server.address','127.0.0.1','--server.headless','true','--browser.gatherUsageStats','false','--server.fileWatcherType','none']
    process=start_server(command)
    print('Demarrage de BO1, verification du serveur...',flush=True)
    for _ in range(60):
        if process.poll() is not None:
            error_file=LOGS/'server-error.log'
            details=(error_file if error_file.exists() else LOGS/'server.log').read_text(encoding='utf-8',errors='replace')[-2500:]
            raise RuntimeError('Le serveur a quitte avant le demarrage.\n'+details)
        if healthy(port):
            state={'project':str(ROOT),'pid':process.pid,'port':port,'url':f'http://localhost:{port}','started_at':time.time()}
            STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
            print('BO1 FINAL PRET: '+state['url'],flush=True)
            print('Vous pouvez fermer cette fenetre. Le serveur reste actif.',flush=True)
            if open_browser: webbrowser.open(state['url'])
            return state
        time.sleep(1)
    process.terminate()
    raise RuntimeError('Demarrage trop long. Voir logs/server.log.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--no-browser',action='store_true'); parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    try:
        if args.check:
            missing=dependencies(); print('Python:',sys.executable); print('Projet:',ROOT); print('Dependances:',missing or 'OK')
            sys.exit(1 if missing else 0)
        launch(not args.no_browser)
    except Exception as error:
        print('ERREUR: '+str(error),file=sys.stderr,flush=True); sys.exit(1)
