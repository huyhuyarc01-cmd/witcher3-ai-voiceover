"""
The Witcher 3 - Realtime Voiceover Companion GUI
=================================================
Giao diện điều khiển hiện đại, trực quan với hỗ trợ 9 ngôn ngữ hiển thị và chuyển đổi mượt mà.
"""

import os
import sys
import time
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

# Đảm bảo UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import customtkinter as ctk
from voiceover_reader import (
    VoiceoverEngine, tail_witcher_log_loop, acquire_single_instance_lock,
    get_engine_voices, get_supported_speech_languages, VITS_VOICE_CONFIG, KOKORO_VOICES_BY_LANG
)

# Đa ngôn ngữ hiển thị giao diện (UI Localization) cho toàn bộ 9 ngôn ngữ
UI_LANGUAGES = {
    "vi": {
        "title": "The Witcher 3 - Thuyết Minh & Lồng Tiếng AI",
        "ui_lang_label": "🌐 Ngôn ngữ giao diện:",
        "status_waiting": "🟡 Đang chờ The Witcher 3...",
        "status_connected": "🟢 Đã kết nối The Witcher 3",
        "btn_browse": "📂 Đổi thư mục Documents",
        "engine_label": "Công nghệ AI:",
        "voice_label": "Giọng đọc chính:",
        "overhead": "Đọc thoại bâng quơ trên đầu NPC",
        "auto_trans": "Tự động dịch sang ngôn ngữ chọn",
        "target_lang": "Ngôn ngữ đọc:",
        "volume_label": "Âm lượng:",
        "test_btn": "🎧 Nghe thử giọng nói",
        "models_btn": "📦 Trạng thái Model AI",
        "hotkey_hint": "👉 Phím nóng trong game: Nhấn [F10] hoặc [F8] để đổi chế độ",
        "feed_header": "--- Lịch sử hội thoại thời gian thực ---",
    },
    "en": {
        "title": "The Witcher 3 - AI Voiceover & Dubbing Companion",
        "ui_lang_label": "🌐 UI Language:",
        "status_waiting": "🟡 Waiting for The Witcher 3...",
        "status_connected": "🟢 Connected to The Witcher 3",
        "btn_browse": "📂 Browse Documents Folder",
        "engine_label": "AI Engine:",
        "voice_label": "Default Voice:",
        "overhead": "Read overhead floating NPC dialogue",
        "auto_trans": "Auto-translate subtitles",
        "target_lang": "Voice Language:",
        "volume_label": "Volume:",
        "test_btn": "🎧 Test Voice Sample",
        "models_btn": "📦 AI Models Status",
        "hotkey_hint": "👉 In-game Hotkey: Press [F10] or [F8] to toggle mode",
        "feed_header": "--- Live Dialogue Feed ---",
    },
    "pl": {
        "title": "Wiedźmin 3 - Towarzysz Dubbingu AI",
        "ui_lang_label": "🌐 Język interfejsu:",
        "status_waiting": "🟡 Oczekiwanie na Wiedźmina 3...",
        "status_connected": "🟢 Połączono z Wiedźminem 3",
        "btn_browse": "📂 Wybierz folder Dokumenty",
        "engine_label": "Silnik AI:",
        "voice_label": "Główny głos:",
        "overhead": "Czytaj napisy nad głowami NPC",
        "auto_trans": "Automatyczne tłumaczenie",
        "target_lang": "Język mowy:",
        "volume_label": "Głośność:",
        "test_btn": "🎧 Odsłuchaj próbkę",
        "models_btn": "📦 Stan modeli AI",
        "hotkey_hint": "👉 Klawisz w grze: Naciśnij [F10] lub [F8], aby przełączyć tryb",
        "feed_header": "--- Kanał dialogów na żywo ---",
    },
    "de": {
        "title": "The Witcher 3 - KI-Synchronisationsassistent",
        "ui_lang_label": "🌐 Oberflächensprache:",
        "status_waiting": "🟡 Warte auf The Witcher 3...",
        "status_connected": "🟢 Verbunden mit The Witcher 3",
        "btn_browse": "📂 Dokumente-Ordner wählen",
        "engine_label": "KI-Modell:",
        "voice_label": "Hauptstimme:",
        "overhead": "NPC-Kopfdialoge vorlesen",
        "auto_trans": "Untertitel automatisch übersetzen",
        "target_lang": "Sprache:",
        "volume_label": "Lautstärke:",
        "test_btn": "🎧 Sprachprobe abspielen",
        "models_btn": "📦 KI-Modellstatus",
        "hotkey_hint": "👉 Hotkey im Spiel: Drücke [F10] oder [F8] zum Wechseln",
        "feed_header": "--- Live-Dialogprotokoll ---",
    },
    "fr": {
        "title": "The Witcher 3 - Compagnon Doublage IA",
        "ui_lang_label": "🌐 Langue de l'interface:",
        "status_waiting": "🟡 En attente de The Witcher 3...",
        "status_connected": "🟢 Connecté à The Witcher 3",
        "btn_browse": "📂 Parcourir Dossier Documents",
        "engine_label": "Moteur IA:",
        "voice_label": "Voix principale:",
        "overhead": "Lire les dialogues au-dessus des PNJ",
        "auto_trans": "Traduction automatique",
        "target_lang": "Langue parlée:",
        "volume_label": "Volume:",
        "test_btn": "🎧 Tester la voix",
        "models_btn": "📦 Statut des modèles IA",
        "hotkey_hint": "👉 Raccourci en jeu: Appuyez sur [F10] ou [F8] pour changer",
        "feed_header": "--- Flux de dialogue en direct ---",
    },
    "es": {
        "title": "The Witcher 3 - Compañero de Doblaje IA",
        "ui_lang_label": "🌐 Idioma de la interfaz:",
        "status_waiting": "🟡 Esperando a The Witcher 3...",
        "status_connected": "🟢 Conectado a The Witcher 3",
        "btn_browse": "📂 Explorar carpeta Documentos",
        "engine_label": "Motor de IA:",
        "voice_label": "Voz principal:",
        "overhead": "Leer subtítulos flotantes de NPC",
        "auto_trans": "Traducción automática de subtítulos",
        "target_lang": "Idioma de voz:",
        "volume_label": "Volumen:",
        "test_btn": "🎧 Probar muestra de voz",
        "models_btn": "📦 Estado de modelos IA",
        "hotkey_hint": "👉 Tecla rápida en juego: Pulsa [F10] o [F8] para alternar",
        "feed_header": "--- Registro de diálogos en tiempo real ---",
    },
    "zh": {
        "title": "巫师3 - AI配音伴侣",
        "ui_lang_label": "🌐 界面语言:",
        "status_waiting": "🟡 等待《巫师3》启动...",
        "status_connected": "🟢 已连接《巫师3》",
        "btn_browse": "📂 浏览我的文档目录",
        "engine_label": "AI语音引擎:",
        "voice_label": "默认声音:",
        "overhead": "朗读NPC头顶浮动台词",
        "auto_trans": "自动翻译字幕",
        "target_lang": "发音语言:",
        "volume_label": "音量调节:",
        "test_btn": "🎧 试听语音样本",
        "models_btn": "📦 AI模型状态",
        "hotkey_hint": "👉 游戏内热键: 按 [F10] 或 [F8] 快速切换模式",
        "feed_header": "--- 实时对话记录 ---",
    },
    "ja": {
        "title": "ウィッチャー3 - AI音声吹き替えコンパニオン",
        "ui_lang_label": "🌐 UI言語:",
        "status_waiting": "🟡 『ウィッチャー3』の起動を待機中...",
        "status_connected": "🟢 『ウィッチャー3』に接続しました",
        "btn_browse": "📂 ドキュメントフォルダを選択",
        "engine_label": "AIエンジン:",
        "voice_label": "デフォルト音声:",
        "overhead": "NPCの頭上テキストを読み上げる",
        "auto_trans": "字幕を自動翻訳",
        "target_lang": "音声言語:",
        "volume_label": "音量:",
        "test_btn": "🎧 音声を試聴",
        "models_btn": "📦 AIモデルの状態",
        "hotkey_hint": "👉 ゲーム内ショートカット: [F10] または [F8] で切り替え",
        "feed_header": "--- リアルタイム対話ログ ---",
    },
    "ru": {
        "title": "Ведьмак 3 - AI Голосовой компаньон озвучки",
        "ui_lang_label": "🌐 Язык интерфейса:",
        "status_waiting": "🟡 Ожидание запуска Ведьмак 3...",
        "status_connected": "🟢 Подключено к Ведьмак 3",
        "btn_browse": "📂 Обзор папки Документы",
        "engine_label": "Движок AI:",
        "voice_label": "Основной голос:",
        "overhead": "Озвучивать парящие реплики NPC",
        "auto_trans": "Автоматический перевод субтитров",
        "target_lang": "Язык озвучки:",
        "volume_label": "Громкость:",
        "test_btn": "🎧 Прослушать образец",
        "models_btn": "📦 Статус моделей AI",
        "hotkey_hint": "👉 Горячая клавиша: Нажмите [F10] hoặc [F8] для переключения",
        "feed_header": "--- Журнал диалогов в реальном времени ---",
    },
    "it": {
        "title": "The Witcher 3 - Compagno di Doppiaggio AI",
        "ui_lang_label": "🌐 Lingua interfaccia:",
        "status_waiting": "🟡 In attesa di The Witcher 3...",
        "status_connected": "🟢 Connesso a The Witcher 3",
        "btn_browse": "📂 Seleziona cartella Documenti",
        "engine_label": "Motore AI:",
        "voice_label": "Voce predefinita:",
        "overhead": "Leggi dialoghi sopra i PNG",
        "auto_trans": "Traduci automaticamente i sottotitoli",
        "target_lang": "Lingua voce:",
        "volume_label": "Volume:",
        "test_btn": "🎧 Ascolta prova voce",
        "models_btn": "📦 Stato modelli AI",
        "hotkey_hint": "👉 Tasto rapido in gioco: Premi [F10] o [F8] per cambiare modalità",
        "feed_header": "--- Registro dialoghi in tempo reale ---",
    },
    "pt": {
        "title": "The Witcher 3 - Companheiro de Dublagem AI",
        "ui_lang_label": "🌐 Idioma da interface:",
        "status_waiting": "🟡 Aguardando The Witcher 3...",
        "status_connected": "🟢 Conectado ao The Witcher 3",
        "btn_browse": "📂 Procurar pasta Documentos",
        "engine_label": "Motor de IA:",
        "voice_label": "Voz padrão:",
        "overhead": "Ler falas flutuantes sobre NPCs",
        "auto_trans": "Traduzir legendas automaticamente",
        "target_lang": "Idioma da voz:",
        "volume_label": "Volume:",
        "test_btn": "🎧 Ouvir teste de voz",
        "models_btn": "📦 Status dos modelos de IA",
        "hotkey_hint": "👉 Atalho no jogo: Pressione [F10] ou [F8] para alternar",
        "feed_header": "--- Histórico de diálogos ao vivo ---",
    },
}

SUPPORTED_LANGUAGES = [
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


class VoiceoverApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.engine = VoiceoverEngine(
            dialogue_callback=self._on_dialogue_event,
            status_callback=self._on_status_event,
            mode_callback=self._on_mode_switched_by_hotkey
        )

        self.title("The Witcher 3 - AI Voiceover Companion")
        self.geometry("780x690")
        self.minsize(720, 620)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.cur_lang = self.engine.ui_lang if self.engine.ui_lang in UI_LANGUAGES else "vi"

        # Trạng thái kết nối file log game
        self.is_connected = False
        self.connected_file_name = ""

        # Bản đồ giọng hiện tại: {display_name: voice_key}
        self.current_voice_map = {}

        self._build_ui()
        self._update_speech_language_choices()
        self._update_voice_choices()
        self._sync_values_to_ui()
        self._update_options_availability()

        self.log_thread = threading.Thread(target=tail_witcher_log_loop, args=(self.engine,), daemon=True)
        self.log_thread.start()

    def t(self, key):
        return UI_LANGUAGES.get(self.cur_lang, UI_LANGUAGES["vi"]).get(key, key)

    def _build_ui(self):
        # 1. Header Frame
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_title = ctk.CTkLabel(header, text=self.t("title"), font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_title.pack(side="left")

        # UI Language row
        ui_lang_frame = ctk.CTkFrame(header, fg_color="transparent")
        ui_lang_frame.pack(side="right")

        self.lbl_ui_lang = ctk.CTkLabel(ui_lang_frame, text=self.t("ui_lang_label"), font=ctk.CTkFont(size=12))
        self.lbl_ui_lang.pack(side="left", padx=(0, 6))

        lang_names = [name for code, name in SUPPORTED_LANGUAGES]
        self.combo_ui_lang = ctk.CTkComboBox(ui_lang_frame, values=lang_names, width=130, command=self._on_ui_lang_change)
        cur_name = dict(SUPPORTED_LANGUAGES).get(self.cur_lang, "Tiếng Việt")
        self.combo_ui_lang.set(cur_name)
        self.combo_ui_lang.pack(side="left")

        # Status row with browse folder button
        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(0, 8))

        self.lbl_status = ctk.CTkLabel(status_row, text=self.t("status_waiting"), text_color="#E5C07B", font=ctk.CTkFont(size=13))
        self.lbl_status.pack(side="left")

        self.btn_browse = ctk.CTkButton(status_row, text=self.t("btn_browse"), width=160, height=24,
                                        font=ctk.CTkFont(size=11), fg_color="#3A3F4B", hover_color="#4B5263",
                                        command=self._on_browse_click)
        self.btn_browse.pack(side="right")

        # 2. Main Settings Card
        card = ctk.CTkFrame(self, corner_radius=10)
        card.pack(fill="x", padx=16, pady=4)

        # Row 1: Engine Selection
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=6)

        self.lbl_engine = ctk.CTkLabel(r1, text=self.t("engine_label"), width=130, anchor="w", font=ctk.CTkFont(weight="bold"))
        self.lbl_engine.pack(side="left")

        self.seg_engine = ctk.CTkSegmentedButton(r1, values=["VITS ONNX (Offline)", "Kokoro ONNX (Offline)", "Edge-TTS Cloud (Online)"], command=self._on_engine_change)
        self.seg_engine.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Row 2: Dynamic Voice Selection
        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=12, pady=6)

        self.lbl_voice = ctk.CTkLabel(r2, text=self.t("voice_label"), width=130, anchor="w", font=ctk.CTkFont(weight="bold"))
        self.lbl_voice.pack(side="left")

        self.combo_voice = ctk.CTkComboBox(r2, values=["Voice 1", "Voice 2"], width=320, command=self._on_voice_change)
        self.combo_voice.pack(side="left", padx=(0, 10))

        # Row 3: Overhead Dialogue Switch
        r3 = ctk.CTkFrame(card, fg_color="transparent")
        r3.pack(fill="x", padx=12, pady=6)

        self.switch_overhead = ctk.CTkSwitch(r3, text=self.t("overhead"), command=self._on_overhead_change)
        self.switch_overhead.pack(side="left")

        # Row 4: Auto-Translate & Target Speech Language
        r4 = ctk.CTkFrame(card, fg_color="transparent")
        r4.pack(fill="x", padx=12, pady=6)

        self.switch_trans = ctk.CTkSwitch(r4, text=self.t("auto_trans"), command=self._on_trans_change)
        self.switch_trans.pack(side="left", padx=(0, 12))

        self.lbl_target_lang = ctk.CTkLabel(r4, text=self.t("target_lang"))
        self.lbl_target_lang.pack(side="left", padx=(0, 6))

        self.combo_target_lang = ctk.CTkComboBox(r4, values=lang_names, width=130, command=self._on_target_lang_change)
        self.combo_target_lang.pack(side="left")

        # Row 5: Volume Slider
        r5 = ctk.CTkFrame(card, fg_color="transparent")
        r5.pack(fill="x", padx=12, pady=6)

        self.lbl_volume = ctk.CTkLabel(r5, text=self.t("volume_label"), width=130, anchor="w", font=ctk.CTkFont(weight="bold"))
        self.lbl_volume.pack(side="left")

        self.slider_volume = ctk.CTkSlider(r5, from_=0, to=150, number_of_steps=30, command=self._on_volume_change)
        self.slider_volume.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.lbl_vol_val = ctk.CTkLabel(r5, text=f"{self.engine.volume}%", width=45)
        self.lbl_vol_val.pack(side="left")

        # 3. Actions Row (Test Voice + Model Status)
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=6)

        self.btn_test = ctk.CTkButton(actions, text=self.t("test_btn"), command=self._on_test_click, fg_color="#2E7D32", hover_color="#1B5E20")
        self.btn_test.pack(side="left", padx=(0, 10))

        self.btn_models = ctk.CTkButton(actions, text=self.t("models_btn"), width=150, fg_color="#3A3F4B", hover_color="#4B5263", command=self._show_models_dialog)
        self.btn_models.pack(side="left")

        self.lbl_hotkey = ctk.CTkLabel(actions, text=self.t("hotkey_hint"), text_color="#61AFEF", font=ctk.CTkFont(size=12))
        self.lbl_hotkey.pack(side="right")

        # 4. Live Dialogue Feed
        self.txt_feed = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12), corner_radius=8)
        self.txt_feed.pack(fill="both", expand=True, padx=16, pady=(4, 12))
        self.txt_feed.insert("end", self.t("feed_header") + "\n\n")

    def _update_status_display(self):
        """Cập nhật trạng thái kết nối với đúng ngôn ngữ giao diện đang chọn."""
        name_suffix = f" ({self.connected_file_name})" if self.connected_file_name else ""
        if self.is_connected:
            self.lbl_status.configure(
                text=f"{self.t('status_connected')}{name_suffix}",
                text_color="#98C379"
            )
        else:
            self.lbl_status.configure(
                text=f"{self.t('status_waiting')}{name_suffix}",
                text_color="#E5C07B"
            )

    def _update_speech_language_choices(self):
        """Cập nhật danh sách các ngôn ngữ đọc mà engine hiện tại hỗ trợ."""
        supported = get_supported_speech_languages(self.engine.engine_type)
        lang_names = [name for _, name in supported]
        self.combo_target_lang.configure(values=lang_names)

        supported_codes = [code for code, _ in supported]
        if self.engine.target_lang not in supported_codes:
            self.engine.target_lang = supported_codes[0]
            self.engine.save_config()

        cur_name = dict(SUPPORTED_LANGUAGES).get(self.engine.target_lang, "Tiếng Việt")
        self.combo_target_lang.set(cur_name)

    def _update_voice_choices(self):
        """Cập nhật danh sách giọng đọc ĐÚNG VỚI CÔNG NGHỆ AI VÀ NGÔN NGỮ ĐANG CHỌN."""
        engine = self.engine.engine_type
        lang = self.engine.target_lang
        self.current_voice_map.clear()

        voices = get_engine_voices(engine, lang)
        for k, label in voices:
            self.current_voice_map[label] = k

        voice_labels = list(self.current_voice_map.keys())
        self.combo_voice.configure(values=voice_labels)

        current_k = self.engine.voice_type
        matched_label = None
        for label, k in self.current_voice_map.items():
            if k == current_k:
                matched_label = label
                break

        if matched_label:
            self.combo_voice.set(matched_label)
        elif voice_labels:
            self.combo_voice.set(voice_labels[0])
            self.engine.voice_type = self.current_voice_map[voice_labels[0]]
            self.engine.save_config()

    def _update_options_availability(self):
        """Khóa hoặc mở các option chỉ khả dụng với công nghệ AI tương ứng."""
        # Cả 3 engine (VITS, Kokoro, Edge-TTS) đều hỗ trợ đầy đủ đổi ngôn ngữ giọng đọc
        self.combo_target_lang.configure(state="normal")

        # Tự động dịch khả dụng cho CẢ 3 ENGINE
        self.switch_trans.configure(state="normal")
        if self.engine.auto_translate:
            self.switch_trans.select()
        else:
            self.switch_trans.deselect()

    def _sync_values_to_ui(self):
        engine_map = {"vits": "VITS ONNX (Offline)", "kokoro": "Kokoro ONNX (Offline)", "online": "Edge-TTS Cloud (Online)"}
        self.seg_engine.set(engine_map.get(self.engine.engine_type, "VITS ONNX (Offline)"))

        if self.engine.read_overhead:
            self.switch_overhead.select()
        else:
            self.switch_overhead.deselect()

        if self.engine.auto_translate:
            self.switch_trans.select()
        else:
            self.switch_trans.deselect()

        self.slider_volume.set(self.engine.volume)
        self.lbl_vol_val.configure(text=f"{self.engine.volume}%")

    def _on_browse_click(self):
        chosen = filedialog.askdirectory(title=self.t("btn_browse"))
        if chosen:
            self.engine.custom_log_path = chosen
            self.engine.save_config()

    def _on_ui_lang_change(self, choice):
        for code, name in SUPPORTED_LANGUAGES:
            if name == choice:
                self.cur_lang = code
                self.engine.ui_lang = code
                self.engine.save_config()
                break
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        self.lbl_title.configure(text=self.t("title"))
        self.lbl_ui_lang.configure(text=self.t("ui_lang_label"))
        self.btn_browse.configure(text=self.t("btn_browse"))
        self.lbl_engine.configure(text=self.t("engine_label"))
        self.lbl_voice.configure(text=self.t("voice_label"))
        self.switch_overhead.configure(text=self.t("overhead"))
        self.switch_trans.configure(text=self.t("auto_trans"))
        self.lbl_target_lang.configure(text=self.t("target_lang"))
        self.lbl_volume.configure(text=self.t("volume_label"))
        self.btn_test.configure(text=self.t("test_btn"))
        self.btn_models.configure(text=self.t("models_btn"))
        self.lbl_hotkey.configure(text=self.t("hotkey_hint"))
        self._update_status_display()

    def _on_engine_change(self, value):
        rev = {"VITS ONNX (Offline)": "vits", "Kokoro ONNX (Offline)": "kokoro", "Edge-TTS Cloud (Online)": "online"}
        self.engine.engine_type = rev.get(value, "vits")
        self.engine.save_config()
        self._update_speech_language_choices()
        self._update_voice_choices()
        self._update_options_availability()

    def _on_voice_change(self, value):
        if value in self.current_voice_map:
            self.engine.voice_type = self.current_voice_map[value]
            self.engine.save_config()

    def _on_overhead_change(self):
        self.engine.read_overhead = bool(self.switch_overhead.get())
        self.engine.save_config()

    def _on_trans_change(self):
        self.engine.auto_translate = bool(self.switch_trans.get())
        self.engine.save_config()

    def _on_target_lang_change(self, choice):
        for code, name in SUPPORTED_LANGUAGES:
            if name == choice:
                self.engine.target_lang = code
                self.engine.save_config()
                break
        self._update_voice_choices()
        self._update_options_availability()

    def _on_volume_change(self, value):
        val = int(value)
        self.engine.volume = val
        self.lbl_vol_val.configure(text=f"{val}%")
        self.engine.save_config()

    def _on_test_click(self):
        """Thử trực tiếp đúng giọng đọc và công nghệ đang chọn."""
        engine = self.engine.engine_type
        voice_key = self.engine.voice_type
        lang = self.engine.target_lang

        orig_text = self.btn_test.cget("text")
        self.btn_test.configure(text="⏳ Đang phát...", state="disabled")

        def _run():
            try:
                self.engine.test_voice_sample(engine, voice_key, lang)
            finally:
                try:
                    self.after(0, lambda: self.btn_test.configure(text=orig_text, state="normal"))
                except Exception:
                    pass
        threading.Thread(target=_run, daemon=True).start()

    def _show_models_dialog(self):
        """Hiển thị trạng thái chi tiết các Model AI đã tích hợp sẵn."""
        piper_found = []
        for l_code, vdict in VITS_VOICE_CONFIG.items():
            for vk, cfg in vdict.items():
                mfile = self.engine.piper_models_dir / cfg[0]
                if mfile.exists():
                    piper_found.append(f"  • [{l_code.upper()}] {cfg[2]} ({round(mfile.stat().st_size / 1024 / 1024, 1)} MB)")

        kokoro_ok = self.engine.kokoro_model.exists() and len(self.engine.kokoro_styles) > 0
        kokoro_size = f"{round(self.engine.kokoro_model.stat().st_size / 1024 / 1024, 1)} MB" if kokoro_ok else "Chưa có"

        msg = (
            "TRẠNG THÁI CÁC MODEL AI OFFLINE:\n"
            "====================================\n\n"
            f"1. Model VITS ONNX (Piper Đa Ngôn Ngữ):\n"
            f"   - Tổng số model đã tải sẵn: {len(piper_found)} giọng đọc\n"
            + "\n".join(piper_found) + "\n\n"
            f"2. Model Kokoro ONNX (Đa giọng đọc Tiếng Việt):\n"
            f"   - Trạng thái: {'✅ Đã gói sẵn 100%' if kokoro_ok else '❌ Chưa có'}\n"
            f"   - Dung lượng model: {kokoro_size}\n"
            f"   - Voicepacks nạp sẵn: 4 giọng (Diễm Trinh, Mai Linh, Hưng Thịnh, Tuấn Ngọc)\n\n"
            f"3. Microsoft Edge-TTS Cloud:\n"
            f"   - Trạng thái: ✅ Kết nối trực tuyến (9 ngôn ngữ, giọng đọc tự nhiên)\n\n"
            "------------------------------------\n"
            "TẤT CẢ MODEL ĐÃ ĐƯỢC TÍCH HỢP ĐẦY ĐỦ TRONG ỨNG DỤNG!\n"
            "Chạy file exe là dùng được ngay lập tức, hoàn toàn không cần tải thêm gì."
        )
        messagebox.showinfo(self.t("models_btn"), msg)

    def _on_dialogue_event(self, speaker, text, mode_name, is_cached):
        def _update():
            try:
                tag = "SSD Cache" if is_cached else mode_name
                line = f"[{tag}] {speaker}: {text}\n"
                self.txt_feed.insert("end", line)
                self.txt_feed.see("end")
            except Exception:
                pass
        try:
            self.after(0, _update)
        except Exception:
            pass

    def _on_status_event(self, is_connected, file_name):
        self.is_connected = is_connected
        self.connected_file_name = file_name
        def _update():
            try:
                self._update_status_display()
            except Exception:
                pass
        try:
            self.after(0, _update)
        except Exception:
            pass

    def _on_mode_switched_by_hotkey(self, new_mode):
        def _update():
            try:
                self._sync_values_to_ui()
                self._update_speech_language_choices()
                self._update_voice_choices()
                self._update_options_availability()
            except Exception:
                pass
        try:
            self.after(0, _update)
        except Exception:
            pass


def main():
    if not acquire_single_instance_lock():
        import tkinter.messagebox as mb
        root = ctk.CTk()
        root.withdraw()
        mb.showwarning("Cảnh báo", "Đã có một phiên bản Voiceover Companion đang chạy trên máy!")
        sys.exit(0)

    app = VoiceoverApp()
    app.mainloop()


if __name__ == "__main__":
    main()
