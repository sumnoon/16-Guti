"""Copy the files the game needs at runtime from game/ into www/, the folder Capacitor packs into the Android app.

Leaves out development files (page.html, build_index.py, start scripts) and assets/models-glb/
(plain .glb copies for Unity / Godot / Blender; the game loads assets/models/*.json).
Run from the project root:  python tools/build_web.py   (or: npm run web)
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME, WWW = ROOT / 'game', ROOT / 'www'
FILES = ['index.html', 'manifest.webmanifest', 'sw.js']
DIRS = ['js', 'vendor', 'assets/models', 'assets/tex', 'assets/ui']

subprocess.run([sys.executable, str(GAME / 'build_index.py')], check=True)   # index.html follows page.html
if WWW.exists():
    shutil.rmtree(WWW)
for f in FILES:
    (WWW / f).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GAME / f, WWW / f)
for d in DIRS:
    shutil.copytree(GAME / d, WWW / d)
size = sum(p.stat().st_size for p in WWW.rglob('*') if p.is_file())
print(f'www/ ready: {sum(1 for p in WWW.rglob("*") if p.is_file())} files, {size / 1e6:.1f} MB')
