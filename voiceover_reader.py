"""
The Witcher 3 - Universal Voiceover Engine
===========================================
Core background service handling real-time subtitle extraction,
multi-engine TTS (VITS / Kokoro / Edge-TTS), multi-character voice casting,
auto-translation, overhead barks filtering, and digital volume control.
"""

import os
import re
import sys
import json
import time
import queue
import ctypes
from ctypes import wintypes
import hashlib
import asyncio
import urllib.request
import urllib.parse
import subprocess
import threading
import socket
from pathlib import Path
import numpy as np

# Đảm bảo UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Đảm bảo SSL Certifi cho môi trường đóng gói PyInstaller
try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
except Exception:
    pass

# Lock socket port
_LOCK_PORT = 49202
_lock_socket = None

def acquire_single_instance_lock():
    global _lock_socket
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_socket.bind(("127.0.0.1", _LOCK_PORT))
        return True
    except socket.error:
        return False


def get_base_dir() -> Path:
    """Xác định chính xác thư mục chứa tài nguyên cả khi chạy script lẫn khi đóng gói .exe."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            p = Path(sys._MEIPASS)
            if (p / "kokoro").exists():
                return p
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "_internal" / "kokoro").exists():
            return exe_dir / "_internal"
        if (exe_dir / "kokoro").exists():
            return exe_dir
    return Path(__file__).parent


def get_windows_documents_folder() -> Path:
    """Lấy đường dẫn thư mục Documents chính xác nhất của Windows (kể cả khi đổi ổ đĩa hoặc dùng OneDrive)."""
    try:
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        res = ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
        if res == 0 and buf.value:
            return Path(buf.value)
    except Exception:
        pass

    user_prof = Path(os.environ.get("USERPROFILE", "."))
    candidates = [
        user_prof / "Documents",
        user_prof / "OneDrive" / "Documents",
        user_prof / "My Documents",
    ]
    for c in candidates:
        if c.exists():
            return c
    return user_prof / "Documents"


# Cờ ẩn hoàn toàn cửa sổ dòng lệnh cmd khi chạy tiến trình ngầm trên Windows (Mục 5)
CREATE_NO_WINDOW = 0x08000000

# Audio libraries
try:
    import sounddevice as sd
    import soundfile as sf
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import onnxruntime as ort
    import vig2p
    HAS_KOKORO = True
except ImportError:
    HAS_KOKORO = False

# Edge-TTS voice mapping per language
EDGE_VOICE_MAP = {
    "vi": {
        "female1": ("vi-VN-HoaiMyNeural", "Nữ - Hoài My"),
        "male1": ("vi-VN-NamMinhNeural", "Nam - Nam Minh"),
    },
    "en": {
        "female1": ("en-US-JennyNeural", "Female - Jenny"),
        "female2": ("en-US-AriaNeural", "Female - Aria"),
        "male1": ("en-US-GuyNeural", "Male - Guy"),
        "male2": ("en-US-ChristopherNeural", "Male - Christopher"),
    },
    "fr": {
        "female1": ("fr-FR-DeniseNeural", "Femme - Denise"),
        "female2": ("fr-FR-EloiseNeural", "Femme - Eloise"),
        "male1": ("fr-FR-HenriNeural", "Homme - Henri"),
        "male2": ("fr-FR-AlainNeural", "Homme - Alain"),
    },
    "de": {
        "female1": ("de-DE-KatjaNeural", "Frau - Katja"),
        "female2": ("de-DE-AmalaNeural", "Frau - Amala"),
        "male1": ("de-DE-KillianNeural", "Mann - Killian"),
        "male2": ("de-DE-ConradNeural", "Mann - Conrad"),
    },
    "es": {
        "female1": ("es-ES-ElviraNeural", "Mujer - Elvira"),
        "female2": ("es-ES-AbrilNeural", "Mujer - Abril"),
        "male1": ("es-ES-AlvaroNeural", "Hombre - Alvaro"),
        "male2": ("es-ES-DarioNeural", "Hombre - Dario"),
    },
    "pl": {
        "female1": ("pl-PL-ZofiaNeural", "Kobieta - Zofia"),
        "female2": ("pl-PL-AgnieszkaNeural", "Kobieta - Agnieszka"),
        "male1": ("pl-PL-MarekNeural", "Mężczyzna - Marek"),
    },
    "ru": {
        "female1": ("ru-RU-SvetlanaNeural", "Женский - Светлана"),
        "female2": ("ru-RU-DariyaNeural", "Женский - Дарья"),
        "male1": ("ru-RU-DmitryNeural", "Мужской - Дмитрий"),
    },
    "zh": {
        "female1": ("zh-CN-XiaoxiaoNeural", "女声 - 晓晓"),
        "female2": ("zh-CN-XiaoyiNeural", "女声 - 晓伊"),
        "male1": ("zh-CN-YunjianNeural", "男声 - 云健"),
        "male2": ("zh-CN-YunxiNeural", "男声 - 云希"),
    },
    "ja": {
        "female1": ("ja-JP-NanamiNeural", "女性 - 七海"),
        "female2": ("ja-JP-AoiNeural", "女性 - 葵"),
        "male1": ("ja-JP-KeitaNeural", "男性 - 圭太"),
        "male2": ("ja-JP-DaichiNeural", "男性 - 大智"),
    },
    "it": {
        "female1": ("it-IT-ElsaNeural", "Donna - Elsa"),
        "male1": ("it-IT-DiegoNeural", "Uomo - Diego"),
    },
    "pt": {
        "female1": ("pt-BR-FranciscaNeural", "Mulher - Francisca"),
        "male1": ("pt-BR-AntonioNeural", "Homem - Antonio"),
    },
}

KOKORO_VOICES_BY_LANG = {
    "vi": {
        "female1": ("diem_trinh.npy", "Nữ - Diễm Trinh"),
        "female2": ("mai_linh.npy", "Nữ - Mai Linh"),
        "male1": ("hung_thinh.npy", "Nam - Hưng Thịnh"),
        "male2": ("tuan_ngoc.npy", "Nam - Tuấn Ngọc"),
    },
    "en": {
        "female1": ("af_sarah.npy", "Female (US) - Sarah"),
        "female2": ("af_bella.npy", "Female (US) - Bella"),
        "female3": ("bf_emma.npy", "Female (UK) - Emma"),
        "male1": ("am_adam.npy", "Male (US) - Adam"),
        "male2": ("am_michael.npy", "Male (US) - Michael"),
        "male3": ("bm_george.npy", "Male (UK) - George"),
    },
    "es": {
        "female1": ("ef_dora.npy", "Mujer - Dora"),
        "male1": ("em_alex.npy", "Hombre - Alex"),
    },
    "fr": {
        "female1": ("ff_siwis.npy", "Femme - Siwis"),
    },
    "it": {
        "female1": ("if_sara.npy", "Donna - Sara"),
        "male1": ("im_nicola.npy", "Uomo - Nicola"),
    },
    "pt": {
        "female1": ("pf_dora.npy", "Mulher - Dora"),
        "male1": ("pm_alex.npy", "Homem - Alex"),
    },
}

VITS_VOICE_CONFIG = {
    "vi": {
        "female1": ("vi_VN-vais1000-medium.onnx", [], "Nữ - VAIS 1000 (Tiếng Việt)", "0.85"),
        "male1": ("vi_VN-vivos-x_low.onnx", ["--speaker", "5"], "Nam - VIVOS (Tiếng Việt)", "0.75"),
    },
    "en": {
        "female1": ("en_US-lessac-medium.onnx", [], "Female - Lessac (English)", "0.9"),
        "male1": ("en_US-ryan-medium.onnx", [], "Male - Ryan (English)", "0.85"),
    },
    "pl": {
        "male1": ("pl_PL-darkman-medium.onnx", [], "Mężczyzna - Darkman (Polski)", "0.85"),
    },
    "de": {
        "male1": ("de_DE-thorsten-low.onnx", [], "Mann - Thorsten (Deutsch)", "0.85"),
    },
    "fr": {
        "female1": ("fr_FR-siwis-low.onnx", [], "Femme - Siwis (Français)", "0.85"),
    },
    "es": {
        "female1": ("es_ES-sharvard-medium.onnx", [], "Mujer - Sharvard (Español)", "0.85"),
    },
    "ru": {
        "male1": ("ru_RU-dmitri-medium.onnx", [], "Мужской - Дмитрий (Русский)", "0.85"),
    },
    "it": {
        "female1": ("it_IT-paola-medium.onnx", [], "Donna - Paola (Italiano)", "0.85"),
    },
    "pt": {
        "male1": ("pt_BR-faber-medium.onnx", [], "Homem - Faber (Português)", "0.85"),
    },
    "zh": {
        "female1": ("zh_CN-huayan-medium.onnx", [], "女声 - 华妍 (中文)", "0.85"),
    },
}

def get_engine_voices(engine_type: str, lang: str):
    """Trả về danh sách (key, label) theo công nghệ và ngôn ngữ."""
    if engine_type == "vits":
        lang_voices = VITS_VOICE_CONFIG.get(lang, VITS_VOICE_CONFIG["vi"])
        return [(k, cfg[2]) for k, cfg in lang_voices.items()]
    elif engine_type == "kokoro":
        lang_voices = KOKORO_VOICES_BY_LANG.get(lang, KOKORO_VOICES_BY_LANG["vi"])
        return [(k, cfg[1]) for k, cfg in lang_voices.items()]
    else:  # online (Edge-TTS)
        lang_voices = EDGE_VOICE_MAP.get(lang, EDGE_VOICE_MAP["vi"])
        return [(k, label) for k, (vname, label) in lang_voices.items()]

def get_supported_speech_languages(engine_type: str):
    """Trả về danh sách các ngôn ngữ đọc khả dụng theo từng engine."""
    if engine_type == "vits":
        return [
            ("vi", "Tiếng Việt"),
            ("en", "English"),
            ("pl", "Polski"),
            ("de", "Deutsch"),
            ("fr", "Français"),
            ("es", "Español"),
            ("ru", "Русский"),
            ("it", "Italiano"),
            ("pt", "Português"),
            ("zh", "简体中文"),
        ]
    elif engine_type == "kokoro":
        return [
            ("vi", "Tiếng Việt"),
            ("en", "English"),
            ("es", "Español"),
            ("fr", "Français"),
            ("it", "Italiano"),
            ("pt", "Português"),
        ]
    else:  # online
        return [
            ("vi", "Tiếng Việt"),
            ("en", "English"),
            ("pl", "Polski"),
            ("de", "Deutsch"),
            ("fr", "Français"),
            ("es", "Español"),
            ("zh", "简体中文"),
            ("ja", "日本語"),
            ("ru", "Русский"),
            ("it", "Italiano"),
            ("pt", "Português"),
        ]


NAME_PRONUNCIATION_VI = {
    r"\bGeralt\b": "Gia-ran",
    r"\bYennefer\b": "Yên-nơ-phơ",
    r"\bCiri\b": "Xi-ri",
    r"\bVesemir\b": "Vét-xơ-mia",
    r"\bTriss\b": "T-rít",
    r"\bDandelion\b": "Đan-đê-lai-ơn",
    r"\bNovigrad\b": "Nô-vi-gơ-rát",
    r"\bVelen\b": "Vê-len",
    r"\bSkellige\b": "S-ke-li-gơ",
    r"\bKaer Morhen\b": "Kae Mo-hen",
    r"\bWitcher\b": "Uých-chơ",
    r"\bEmhyr\b": "Em-hia",
    r"\bNilfgaard\b": "Niu-gạt",
}

TEST_SAMPLES = {
    "vi": "Được rồi, nói chuyện sau nhé, thầy Vesemir.",
    "en": "All right, talk to you later, Master Vesemir.",
    "pl": "W porządku, porozmawiamy później, mistrzu Vesemirze.",
    "de": "In Ordnung, wir sprechen später, Meister Vesemir.",
    "fr": "D'accord, on se parle plus tard, Maître Vesemir.",
    "es": "De acuerdo, hablaremos más tarde, maestro Vesemir.",
    "zh": "好的，回头见，维瑟米尔大师。",
    "ja": "分かりました、また後で話しましょう、ヴェセミル師匠。",
    "ru": "Хорошо, поговорим позже, мастер Весемир.",
    "it": "D'accordo, parleremo più tardi, maestro Vesemir.",
    "pt": "Tudo bem, falamos mais tarde, mestre Vesemir.",
}

MODE_NOTIFY_TEXTS = {
    "vi": {
        "vits": "Chế độ VITS ngoại tuyến.",
        "kokoro": "Chế độ Kokoro ngoại tuyến.",
        "online": "Chế độ trực tuyến Edge-TTS.",
    },
    "en": {
        "vits": "VITS offline mode.",
        "kokoro": "Kokoro offline mode.",
        "online": "Edge-TTS online mode.",
    },
    "pl": {
        "vits": "Tryb offline VITS.",
        "kokoro": "Tryb offline Kokoro.",
        "online": "Tryb online Edge-TTS.",
    },
    "de": {
        "vits": "VITS Offline-Modus.",
        "kokoro": "Kokoro Offline-Modus.",
        "online": "Edge-TTS Online-Modus.",
    },
    "fr": {
        "vits": "Mode hors-ligne VITS.",
        "kokoro": "Mode hors-ligne Kokoro.",
        "online": "Mode en ligne Edge-TTS.",
    },
    "es": {
        "vits": "Modo sin conexión VITS.",
        "kokoro": "Modo sin conexión Kokoro.",
        "online": "Modo en línea Edge-TTS.",
    },
    "ru": {
        "vits": "Офлайн-режим VITS.",
        "kokoro": "Офлайн-режим Kokoro.",
        "online": "Онлайн-режим Edge-TTS.",
    },
    "zh": {
        "vits": "VITS 离线模式。",
        "kokoro": "Kokoro 离线模式。",
        "online": "Edge-TTS 在线模式。",
    },
    "ja": {
        "vits": "VITS オフラインモード。",
        "kokoro": "Kokoro オフラインモード。",
        "online": "Edge-TTS オンラインモード。",
    },
    "it": {
        "vits": "Modalità offline VITS.",
        "kokoro": "Modalità offline Kokoro.",
        "online": "Modalità online Edge-TTS.",
    },
    "pt": {
        "vits": "Modo offline VITS.",
        "kokoro": "Modo offline Kokoro.",
        "online": "Modo online Edge-TTS.",
    },
}


def clean_raw_text(text: str) -> str:
    """Xóa các thẻ HTML trong phụ đề game."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&quot;", '"').replace("&amp;", "&")
    text = re.sub(r"\.{2,}", ", ", text)
    text = re.sub(r"-{2,}", ", ", text)
    return text.strip()


def apply_language_pronunciation(text: str, target_lang: str) -> str:
    """Chỉ áp dụng từ điển phiên âm khi đích đến là tiếng Việt (Mục 6)."""
    if target_lang == "vi":
        for pattern, replacement in NAME_PRONUNCIATION_VI.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text.strip()


def translate_text(text: str, target_lang: str) -> str:
    """Tự động dịch nhanh văn bản sang ngôn ngữ đích."""
    if not text or target_lang in ("auto", "none"):
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=" + target_lang + "&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2.5) as res:
            data = json.loads(res.read().decode("utf-8"))
            translated = "".join([item[0] for item in data[0] if item[0]])
            return translated.strip() if translated else text
    except Exception:
        return text


class VoiceoverEngine:
    def __init__(self, config_callback=None, dialogue_callback=None, status_callback=None, mode_callback=None):
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.running = True
        self.is_playing = False
        self.stop_event = threading.Event()
        
        self.dialogue_callback = dialogue_callback
        self.status_callback = status_callback
        self.mode_callback = mode_callback

        # Thư mục cache và cấu hình
        self.cache_dir = Path(os.environ.get("LOCALAPPDATA", ".")) / "TheWitcher3_Voiceover_Cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.cache_dir / "user_config.json"

        # Cấu hình mặc định (Mục 4: Tất cả các option bổ sung mặc định là TẮT)
        self.engine_type = "vits"         # 'vits', 'kokoro', 'online'
        self.voice_type = "female1"       # key của giọng đọc
        self.read_overhead = False        # MẶC ĐỊNH TẮT
        self.auto_translate = False       # MẶC ĐỊNH TẮT
        self.target_lang = "vi"           # Ngôn ngữ đích
        self.ui_lang = "vi"               # Ngôn ngữ giao diện
        self.volume = 100                 # Âm lượng (0 - 150%)
        self.custom_log_path = ""         # Đường dẫn log tùy chỉnh nếu có

        self.load_config()

        base_dir = get_base_dir()
        self.base_dir = base_dir
        self.piper_exe = base_dir / "piper" / "piper.exe"
        self.piper_models_dir = base_dir / "piper" / "models"

        # Kokoro assets
        self.kokoro_dir = base_dir / "kokoro"
        self.kokoro_model = self.kokoro_dir / "kokoro_vi.int8.onnx"
        self.kokoro_config = self.kokoro_dir / "config.json"
        self.kokoro_sess = None
        self.kokoro_vocab = {}
        self.kokoro_styles = {}

        self.init_kokoro()

        # Threads
        self.synth_thread = threading.Thread(target=self._synth_loop, daemon=True)
        self.synth_thread.start()

        self.player_thread = threading.Thread(target=self._player_loop, daemon=True)
        self.player_thread.start()

        self.hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.hotkey_thread.start()

    def init_kokoro(self):
        """Khởi tạo Kokoro model và load các voicepack."""
        if HAS_KOKORO and self.kokoro_model.exists() and self.kokoro_config.exists():
            try:
                with open(self.kokoro_config, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.kokoro_vocab = cfg.get("vocab", {})
                self.kokoro_sess = ort.InferenceSession(str(self.kokoro_model))
                try:
                    from kokoro_onnx.tokenizer import Tokenizer
                    self.kokoro_tokenizer = Tokenizer()
                except Exception as te:
                    self.kokoro_tokenizer = None
                    print(f"[Kokoro Tokenizer Init Warning] {te}")

                vp_dir = self.kokoro_dir / "voicepacks"
                if vp_dir.exists():
                    for f in vp_dir.glob("*.npy"):
                        try:
                            self.kokoro_styles[f.name] = np.load(str(f))
                        except Exception:
                            pass
            except Exception as e:
                print(f"[Kokoro Init Error] {e}")

    def load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.engine_type = data.get("engine_type", self.engine_type)
                self.voice_type = data.get("voice_type", self.voice_type)
                self.read_overhead = data.get("read_overhead", False)
                self.auto_translate = data.get("auto_translate", False)
                self.target_lang = data.get("target_lang", self.target_lang)
                self.ui_lang = data.get("ui_lang", self.ui_lang)
                self.volume = data.get("volume", self.volume)
                self.custom_log_path = data.get("custom_log_path", self.custom_log_path)
            except Exception:
                pass

    def save_config(self):
        data = {
            "engine_type": self.engine_type,
            "voice_type": self.voice_type,
            "read_overhead": self.read_overhead,
            "auto_translate": self.auto_translate,
            "target_lang": self.target_lang,
            "ui_lang": self.ui_lang,
            "volume": self.volume,
            "custom_log_path": self.custom_log_path,
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_available_voice_keys(self):
        """Trả về danh sách các key giọng đọc khả dụng theo engine và target_lang hiện tại."""
        voices = get_engine_voices(self.engine_type, self.target_lang)
        return [k for k, _ in voices]

    def toggle_mode(self):
        """Chuyển đổi qua lại giữa các engine khi bấm F10/F8 và thông báo bằng đúng ngôn ngữ."""
        modes = ["vits"]
        if self.kokoro_sess is not None:
            modes.append("kokoro")
        if HAS_EDGE_TTS:
            modes.append("online")

        cur_idx = modes.index(self.engine_type) if self.engine_type in modes else 0
        new_mode = modes[(cur_idx + 1) % len(modes)]
        self.engine_type = new_mode
        self.save_config()

        if self.mode_callback:
            try:
                self.mode_callback(new_mode)
            except Exception:
                pass

        # Khi tùy chọn dịch được bật: thông báo bằng ngôn ngữ đọc được chọn (target_lang)
        # Nếu không bật dịch: thông báo theo ngôn ngữ giao diện (ui_lang)
        notify_lang = self.target_lang if self.auto_translate else self.ui_lang
        if notify_lang not in MODE_NOTIFY_TEXTS:
            notify_lang = "vi"

        text_dict = MODE_NOTIFY_TEXTS.get(notify_lang, MODE_NOTIFY_TEXTS["vi"])
        notify_text = text_dict.get(new_mode, f"Mode {new_mode}")

        def _play_notify():
            ext = "wav" if new_mode in ("vits", "kokoro") else "mp3"
            notify_file = self.cache_dir / f"mode_notify_{new_mode}_{notify_lang}.{ext}"

            # Nếu chưa có file cache thì tổng hợp
            if not notify_file.exists() or notify_file.stat().st_size < 500:
                if new_mode == "vits":
                    vlang = notify_lang if notify_lang in VITS_VOICE_CONFIG else "vi"
                    self._synth_vits_piper(notify_text, "female1", vlang, notify_file)
                elif new_mode == "kokoro":
                    klang = notify_lang if notify_lang in KOKORO_VOICES_BY_LANG else "vi"
                    self._synth_kokoro(notify_text, "female1", klang, notify_file)
                else:  # online
                    self._synth_online_edge(notify_text, "female1", notify_lang, notify_file)

            if notify_file.exists():
                self._play_file(notify_file)
            else:
                fallback_sound = self.base_dir / "sounds" / f"mode_{new_mode}.wav"
                if fallback_sound.exists():
                    self._play_file(fallback_sound)

        threading.Thread(target=_play_notify, daemon=True).start()

    def _hotkey_loop(self):
        VK_F10 = 0x79
        VK_F8 = 0x77
        last_f10 = False
        last_f8 = False
        while self.running:
            state_f10 = bool(ctypes.windll.user32.GetAsyncKeyState(VK_F10) & 0x8000)
            state_f8 = bool(ctypes.windll.user32.GetAsyncKeyState(VK_F8) & 0x8000)
            if (state_f10 and not last_f10) or (state_f8 and not last_f8):
                self.toggle_mode()
            last_f10 = state_f10
            last_f8 = state_f8
            time.sleep(0.08)

    def enqueue(self, speaker: str, text: str):
        cleaned = clean_raw_text(text)
        if not cleaned:
            return
        if not self.read_overhead and speaker.upper() == "NPC":
            return
        self.stop_event.clear()
        self.text_queue.put((speaker, cleaned))

    def _synth_vits_piper(self, text: str, voice_type: str, lang: str, output_file: Path) -> bool:
        """Tổng hợp VITS ONNX với đúng model theo ngôn ngữ và giới tính, ẩn cửa sổ cmd hoàn toàn."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        lang_voices = VITS_VOICE_CONFIG.get(lang, VITS_VOICE_CONFIG["vi"])
        cfg = lang_voices.get(voice_type)
        if not cfg:
            cfg = list(lang_voices.values())[0]

        model_filename, speaker_arg, _, speed_scale = cfg
        model_path = self.piper_models_dir / model_filename
        if not model_path.exists():
            model_path = self.piper_models_dir / "vi_VN-vais1000-medium.onnx"
            speaker_arg = []
            speed_scale = "0.85"

        try:
            cmd = [
                str(self.piper_exe),
                "-m", str(model_path),
                "-f", str(output_file),
                "--length_scale", speed_scale
            ] + speaker_arg

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            proc.communicate(input=text.encode("utf-8"), timeout=6)
            return proc.returncode == 0 and output_file.exists() and output_file.stat().st_size > 1000
        except Exception:
            return False

    def _synth_kokoro(self, text: str, voice_type: str, lang: str, output_file: Path) -> bool:
        if self.kokoro_sess is None:
            return False
        try:
            lang_voices = KOKORO_VOICES_BY_LANG.get(lang, KOKORO_VOICES_BY_LANG["vi"])
            voice_entry = lang_voices.get(voice_type, list(lang_voices.values())[0])
            vfile = voice_entry[0]

            style_arr = self.kokoro_styles.get(vfile)
            if style_arr is None:
                vp_file = self.kokoro_dir / "voicepacks" / vfile
                if vp_file.exists():
                    style_arr = np.load(str(vp_file))
                    self.kokoro_styles[vfile] = style_arr
                elif self.kokoro_styles:
                    style_arr = list(self.kokoro_styles.values())[0]
                else:
                    return False

            if lang == "vi":
                phonemes = vig2p.phonemize_text(text)
                tokens = [0] + [self.kokoro_vocab[c] for c in phonemes if c in self.kokoro_vocab] + [0]
            else:
                if self.kokoro_tokenizer is None:
                    try:
                        from kokoro_onnx.tokenizer import Tokenizer
                        self.kokoro_tokenizer = Tokenizer()
                    except Exception as te:
                        try:
                            with open(self.cache_dir / "kokoro_synth_error.log", "a", encoding="utf-8") as f:
                                f.write(f"[{time.ctime()}] Tokenizer lazy load error: {te}\n")
                        except Exception:
                            pass
                        return False
                if lang == "en":
                    k_lang = "en-gb" if vfile.startswith("b") else "en-us"
                elif lang == "fr":
                    k_lang = "fr-fr"
                elif lang == "pt":
                    k_lang = "pt-br"
                else:
                    k_lang = lang  # es, it
                phonemes = self.kokoro_tokenizer.phonemize(text, lang=k_lang)
                tokens = [0] + self.kokoro_tokenizer.tokenize(phonemes) + [0]

            if len(tokens) <= 2:
                return False
            input_ids = np.array([tokens], dtype=np.int64)

            idx = min(len(tokens), len(style_arr) - 1)
            style = style_arr[idx].astype(np.float32)
            if style.ndim == 1:
                style = style.reshape(1, -1)
            elif style.shape != (1, 256):
                style = style.reshape(1, 256)

            speed = np.array(1.15 if len(text) > 50 else 1.05, dtype=np.float32)
            outputs = self.kokoro_sess.run(None, {"input_ids": input_ids, "ref_s": style, "speed": speed})
            waveform = outputs[0]
            sf.write(str(output_file), waveform, 24000)
            return output_file.exists() and output_file.stat().st_size > 1000
        except Exception as e:
            try:
                err_log = self.cache_dir / "kokoro_synth_error.log"
                with open(err_log, "a", encoding="utf-8") as f:
                    f.write(f"[{time.ctime()}] Kokoro Synth Error: {e}\n")
            except Exception:
                pass
            return False

    def _synth_online_edge(self, text: str, voice_type: str, target_lang: str, output_file: Path) -> bool:
        lang_voices = EDGE_VOICE_MAP.get(target_lang, EDGE_VOICE_MAP["vi"])
        voice_tuple = lang_voices.get(voice_type, list(lang_voices.values())[0])
        voice_name = voice_tuple[0]
        rate_str = "+30%" if len(text) > 60 else "+20%"

        async def _gen():
            comm = edge_tts.Communicate(text, voice_name, rate=rate_str)
            await asyncio.wait_for(comm.save(str(output_file)), timeout=3.5)

        try:
            if output_file.exists():
                try:
                    output_file.unlink()
                except Exception:
                    pass
            # Chạy loop an toàn trong thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_gen())
            finally:
                loop.close()

            return output_file.exists() and output_file.stat().st_size > 300
        except Exception:
            return False

    def test_voice_sample(self, engine_type: str, voice_key: str, target_lang: str):
        """Hàm thử giọng trực tiếp đúng 100% theo lựa chọn trên giao diện (Mục 3, 4)."""
        sample_text = TEST_SAMPLES.get(target_lang, TEST_SAMPLES["vi"])
        if engine_type == "kokoro":
            if target_lang not in KOKORO_VOICES_BY_LANG:
                target_lang = "vi"
                sample_text = TEST_SAMPLES["vi"]
        elif engine_type == "vits":
            if target_lang not in VITS_VOICE_CONFIG:
                target_lang = "vi"
                sample_text = TEST_SAMPLES["vi"]

        sample_text = apply_language_pronunciation(sample_text, target_lang)

        test_file = self.cache_dir / f"test_preview_{engine_type}_{voice_key}_{target_lang}.wav"
        if engine_type == "online":
            test_file = self.cache_dir / f"test_preview_{engine_type}_{voice_key}_{target_lang}.mp3"

        success = False
        if engine_type == "vits":
            success = self._synth_vits_piper(sample_text, voice_key, target_lang, test_file)
        elif engine_type == "kokoro":
            success = self._synth_kokoro(sample_text, voice_key, target_lang, test_file)
        else:
            success = self._synth_online_edge(sample_text, voice_key, target_lang, test_file)

        if success and test_file.exists():
            if self.dialogue_callback:
                self.dialogue_callback("Test Voice", sample_text, f"{engine_type.upper()} ({voice_key})", False)
            self._play_file(test_file)
            return True
        return False

    def _synth_loop(self):
        while self.running:
            try:
                speaker, raw_text = self.text_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            current_mode = self.engine_type
            effective_lang = self.target_lang

            if current_mode == "kokoro":
                if effective_lang not in KOKORO_VOICES_BY_LANG:
                    effective_lang = "vi"
            elif current_mode == "vits":
                if effective_lang not in VITS_VOICE_CONFIG:
                    effective_lang = "vi"

            # Tự động dịch nếu được bật
            spoken_text = raw_text
            if self.auto_translate:
                spoken_text = translate_text(raw_text, effective_lang)

            # Áp dụng chuẩn phiên âm
            spoken_text = apply_language_pronunciation(spoken_text, effective_lang)

            assigned_voice = self.voice_type

            key = f"{spoken_text}_{current_mode}_{assigned_voice}_{effective_lang}".encode("utf-8")
            h = hashlib.md5(key).hexdigest()[:16]
            ext = "wav" if current_mode in ("vits", "kokoro") else "mp3"
            cache_file = self.cache_dir / f"tts_{current_mode}_{h}.{ext}"

            if cache_file.exists() and cache_file.stat().st_size > 300:
                if not self.stop_event.is_set():
                    self.audio_queue.put((cache_file, speaker, spoken_text, True, current_mode))
                self.text_queue.task_done()
                continue

            success = False
            used_mode = current_mode

            if current_mode == "vits":
                success = self._synth_vits_piper(spoken_text, assigned_voice, effective_lang, cache_file)
            elif current_mode == "kokoro":
                success = self._synth_kokoro(spoken_text, assigned_voice, effective_lang, cache_file)
            else:  # online (Edge-TTS Cloud)
                success = self._synth_online_edge(spoken_text, assigned_voice, effective_lang, cache_file)

            if success and not self.stop_event.is_set():
                self.audio_queue.put((cache_file, speaker, spoken_text, False, used_mode))

            self.text_queue.task_done()

    def _player_loop(self):
        while self.running:
            try:
                audio_file, speaker, text, is_cached, mode_name = self.audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not self.stop_event.is_set():
                if self.dialogue_callback:
                    self.dialogue_callback(speaker, text, mode_name, is_cached)
                else:
                    tag = "SSD Cache" if is_cached else mode_name
                    print(f"\n>> [{tag}] {speaker}: {text}")

                self.is_playing = True
                self._play_file(audio_file)
                self.is_playing = False

            self.audio_queue.task_done()

    def _play_file(self, filepath: Path) -> bool:
        if self.stop_event.is_set():
            return False

        abs_path = str(filepath.resolve())
        vol_multiplier = max(0.0, min(1.5, self.volume / 100.0))

        if HAS_SOUNDDEVICE:
            try:
                data, fs = sf.read(abs_path)
                data = data * vol_multiplier
                sd.play(data, fs)
                duration = len(data) / float(fs)
                start_time = time.time()
                while time.time() - start_time < duration:
                    if self.stop_event.is_set():
                        sd.stop()
                        return False
                    time.sleep(0.02)
                sd.stop()
                return True
            except Exception:
                pass
        return False


def get_witcher_log_candidates(engine: VoiceoverEngine):
    """Tìm tất cả các vị trí có thể có của file scriptslog.txt."""
    candidates = []

    if engine.custom_log_path and Path(engine.custom_log_path).exists():
        p = Path(engine.custom_log_path)
        if p.is_file():
            candidates.append(p)
        elif p.is_dir():
            candidates.extend([p / "scriptslog.txt", p / "scriptlog.txt"])

    win_docs = get_windows_documents_folder()
    tw3_docs = win_docs / "The Witcher 3"
    candidates.extend([tw3_docs / "scriptslog.txt", tw3_docs / "scriptlog.txt"])

    user_prof = Path(os.environ.get("USERPROFILE", "."))
    onedrive_docs = user_prof / "OneDrive" / "Documents" / "The Witcher 3"
    candidates.extend([onedrive_docs / "scriptslog.txt", onedrive_docs / "scriptlog.txt"])

    std_docs = user_prof / "Documents" / "The Witcher 3"
    candidates.extend([std_docs / "scriptslog.txt", std_docs / "scriptlog.txt"])

    unique_candidates = []
    seen = set()
    for c in candidates:
        s = str(c.resolve()) if c.exists() else str(c)
        if s not in seen:
            seen.add(s)
            unique_candidates.append(c)

    return unique_candidates


def tail_witcher_log_loop(engine: VoiceoverEngine):
    log_file = None

    while engine.running:
        candidates = get_witcher_log_candidates(engine)

        found = None
        for cand in candidates:
            if cand.exists():
                found = cand
                break

        if found:
            log_file = found
            break

        if engine.status_callback:
            engine.status_callback(False, candidates[0].name)

        time.sleep(1)

    if not engine.running:
        return

    if engine.status_callback:
        engine.status_callback(True, log_file.name)

    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        last_file_size = os.path.getsize(log_file)
        last_line_key = ""

        while engine.running:
            try:
                current_size = os.path.getsize(log_file)
                if current_size < last_file_size:
                    f.seek(0, os.SEEK_SET)
                last_file_size = current_size
            except Exception:
                pass

            line = f.readline()
            if not line:
                time.sleep(0.02)
                continue

            if "[VNVoice]" in line:
                try:
                    payload = line.split("[VNVoice]", 1)[1].strip()
                    parts = payload.split("###")
                    if len(parts) >= 3:
                        sub_id, speaker, text = parts[0], parts[1], parts[2]
                        line_key = f"{sub_id}::{text}"
                        if line_key != last_line_key:
                            last_line_key = line_key
                            engine.enqueue(speaker, text)
                except Exception:
                    pass
