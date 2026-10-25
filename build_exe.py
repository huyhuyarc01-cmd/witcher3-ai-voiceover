import subprocess
import sys
import shutil
from pathlib import Path

tool_dir = Path(r"C:\Users\Administrator\.gemini\antigravity\scratch\tw3-voiceover\tool")
dist_dir = Path(r"C:\Users\Administrator\.gemini\antigravity\scratch\tw3-voiceover\dist")
build_dir = Path(r"C:\Users\Administrator\.gemini\antigravity\scratch\tw3-voiceover\build")
desktop_dir = Path(r"C:\Users\Administrator\Desktop\TW3_Voiceover_Companion")

print("Starting PyInstaller build...")
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--windowed",
    "--name", "TW3_Voiceover_Companion",
    f"--distpath={str(dist_dir)}",
    f"--workpath={str(build_dir)}",
    f"--add-data={str(tool_dir / 'piper')};piper",
    f"--add-data={str(tool_dir / 'kokoro')};kokoro",
    f"--add-data={str(tool_dir / 'sounds')};sounds",
    "--collect-all", "customtkinter",
    "--collect-all", "sounddevice",
    "--collect-all", "soundfile",
    "--collect-all", "vig2p",
    "--collect-all", "sea_g2p",
    "--collect-all", "onnxruntime",
    "--collect-all", "edge_tts",
    "--collect-all", "certifi",
    "--collect-all", "aiohttp",
    str(tool_dir / "app_gui.py")
]

res = subprocess.run(cmd)
print("PyInstaller exit code:", res.returncode)

if res.returncode == 0:
    source = dist_dir / "TW3_Voiceover_Companion"
    print(f"Copying build to Desktop: {desktop_dir}...")
    shutil.copytree(source, desktop_dir, dirs_exist_ok=True)
    print("Deployment to Desktop completed successfully!")
