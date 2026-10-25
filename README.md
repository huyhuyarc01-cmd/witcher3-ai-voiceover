# Witcher Voice - Companion Tool Source Code

Open-source real-time AI voiceover and subtitle dubbing companion tool for **The Witcher 3: Wild Hunt**.

## Architecture & Features
- **HUD Dialogue Hook**: Receives real-time dialogue and ambient oneliners from the in-game script (`modVNVoiceover`).
- **Engines Supported**:
  - **Kokoro ONNX**: High-speed offline neural voice model.
  - **Piper / VITS ONNX**: Multi-language offline neural TTS (Vietnamese, English, Spanish, French, German, Italian, Polish, Russian, Chinese, Portuguese).
  - **Microsoft Edge-TTS**: Studio-grade online cloud voices across 100+ languages.
- **GUI**: Modern dark-mode interface built with CustomTkinter.

## How to Build from Source
1. **Requirements**: Python 3.10+ (64-bit).
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt pyinstaller
   ```
3. **Download offline models**:
   Run `setup_piper.ps1` in PowerShell to fetch required Piper VITS ONNX binaries.
4. **Compile executable**:
   ```bash
   python build_exe.py
   ```
   The compiled standalone binary will be generated in `dist/TW3_Voiceover_Companion/`.

## License
MIT / Apache 2.0 (Open Source).
