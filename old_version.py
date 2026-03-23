#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ✦  AURA VIDEO DOWNLOADER  ✦  v1.0                        ║
║                                                                              ║
║  Всё, что делает 4K Video Downloader Plus за $45 — только бесплатно.        ║
║  Использует yt-dlp + ffmpeg (как и 4K VD+, только мы не скрываем это).      ║
║  Powered by PySide6 (Qt6)                                                    ║
║                                                                              ║
║  Платформы:                                                                  ║
║    🎬 YouTube, VK Video, Rutube, Twitch, Dailymotion, Vimeo,               ║
║       Bilibili, OK.ru, Дзен                                                 ║
║    📱 TikTok, Instagram, Twitter/X, Facebook, Reddit                        ║
║    🔞 Pornhub, XVideos, xHamster                                            ║
║                                                                              ║
║  Режимы: Канал · Плейлист · Видео · Аудио                                   ║
║  Фичи:   Прокси · Субтитры · 8K · aria2c · Smart Mode · SponsorBlock      ║
║                                                                              ║
║  «Зачем платить $45 за GUI к yt-dlp, если можно не платить?» — Aura         ║
╚══════════════════════════════════════════════════════════════════════════════╝

REQUIREMENTS:
  - Python 3.9+
  - PySide6:  pip install PySide6
  - yt-dlp:   pip install yt-dlp
  - ffmpeg in PATH
"""

import os
import sys
import re
import json
import random
import subprocess
import threading
import datetime
import time
import shutil
import webbrowser
from pathlib import Path

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QDialog, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QLineEdit, QComboBox,
        QRadioButton, QCheckBox, QGroupBox, QButtonGroup, QPlainTextEdit,
        QTreeWidget, QTreeWidgetItem, QHeaderView, QProgressBar, QStatusBar,
        QToolBar, QFileDialog, QMessageBox, QInputDialog, QFrame, QScrollArea,
        QSplitter, QSystemTrayIcon, QMenu
    )
    from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
    from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
except ImportError:
    print("=" * 60)
    print("  PySide6 не найден / PySide6 not found!")
    print()
    print("  Установите / Install:")
    print("    pip install PySide6")
    print("=" * 60)
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
#  КОНСТАНТЫ
# ══════════════════════════════════════════════════════════════════════════════

SETTINGS_FOLDER_NAME = "aura_video_downloader_settings"
POINTER_FILE_NAME = ".aura_video_downloader_pointer"  # single file in home, NOT inside settings folder
APP_VERSION = "1.0"
CONFIG_FILENAME = "config.json"
POINTER_FILENAME = "pointer.txt"  # legacy (for migration)
YTDLP_CONFIG_FILENAME = "yt-dlp.conf"


def resource_path(relative_path):
    """Get absolute path to resource — works for dev and PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def find_binary(name):
    """Find binary in system PATH using shutil.which (not pip/Python packages)."""
    path = shutil.which(name)
    return path if path else name  # fallback to bare name for subprocess

def get_pointer_file():
    """Pointer is a SINGLE FILE in user's home dir — no extra folders created."""
    return Path.home() / POINTER_FILE_NAME

def _get_legacy_pointer():
    """Old location: ~/aura_video_downloader_settings/pointer.txt"""
    return Path.home() / SETTINGS_FOLDER_NAME / "pointer.txt"

def _migrate_pointer():
    """Migrate old pointer.txt → new single file in home dir."""
    new_pointer = get_pointer_file()
    if new_pointer.exists():
        return  # already migrated
    old_pointer = _get_legacy_pointer()
    if old_pointer.exists():
        try:
            content = old_pointer.read_text(encoding='utf-8').strip()
            new_pointer.write_text(content, encoding='utf-8')
            old_pointer.unlink()
            # Remove old container if now empty
            old_dir = old_pointer.parent
            if old_dir.exists() and not any(old_dir.iterdir()):
                old_dir.rmdir()
        except Exception:
            pass

def get_settings_dir():
    """Get the settings directory. ALL settings live here — nothing in home dir."""
    _migrate_pointer()
    pointer_file = get_pointer_file()
    if pointer_file.exists():
        try:
            custom_path = pointer_file.read_text(encoding='utf-8').strip()
            if custom_path and custom_path != "default":
                settings_dir = Path(custom_path) / SETTINGS_FOLDER_NAME
                if settings_dir.exists():
                    return settings_dir
            else:
                # "default" means home dir
                return Path.home() / SETTINGS_FOLDER_NAME
        except Exception:
            pass
    return Path.home() / SETTINGS_FOLDER_NAME

# In-memory only — no files created, nothing persists after exit
_DEBUG_MODE = False

def is_debug_mode():
    return _DEBUG_MODE

def get_config_path():
    return get_settings_dir() / CONFIG_FILENAME

def get_ytdlp_config_path():
    return get_settings_dir() / YTDLP_CONFIG_FILENAME

def ensure_ytdlp_config():
    if is_debug_mode():
        return None
    config_path = get_ytdlp_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if not config_path.exists():
            config_content = "# yt-dlp config (Aura)\n--js-runtimes node\n"
            config_path.write_text(config_content, encoding='utf-8')
        return config_path
    except Exception:
        return None

# Module-level aliases removed — SettingsManager resolves paths dynamically
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
SUBPROCESS_TIMEOUT = 15
PROCESS_TERMINATE_TIMEOUT = 3
MAX_CONSECUTIVE_EMPTY_RUNS = 3
LOG_MAX_LINES = 5000

def _get_subprocess_env():
    """Get environment with forced UTF-8 encoding and unbuffered output for yt-dlp.
    On Windows, yt-dlp (Python script) defaults to console codepage (cp1251/cp866),
    which produces garbled text when we read stdout as UTF-8."""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"  # Force line-by-line output from pip-installed yt-dlp
    return env

def _get_system_encoding():
    """Get the real Windows system encoding (e.g. cp1251), ignoring PYTHONUTF8.
    Used as fallback when yt-dlp.EXE (standalone PyInstaller binary) ignores
    our PYTHONUTF8/PYTHONIOENCODING env vars and outputs in the system codepage."""
    try:
        import locale
        # getpreferredencoding(False) returns the ACTUAL system encoding,
        # not affected by Python UTF-8 mode or PYTHONUTF8 env var
        return locale.getpreferredencoding(False) or 'utf-8'
    except Exception:
        return 'utf-8'

# Cache system encoding at import time (before PYTHONUTF8 takes effect)
_SYSTEM_ENCODING = _get_system_encoding()

def _fix_encoding(line):
    """Fix encoding of a text line read with errors='surrogateescape'.
    
    When yt-dlp.EXE (standalone PyInstaller) outputs in system codepage (cp1251),
    Python reads it as UTF-8 with surrogateescape — non-UTF-8 bytes become
    surrogate characters (U+DC80..U+DCFF). We detect these and re-decode
    the original bytes using the system encoding.
    
    For pip-installed yt-dlp (which respects PYTHONUTF8=1), output is valid UTF-8
    and passes through unchanged.
    """
    if not line:
        return ""
    try:
        # If the line can be encoded to UTF-8, it's already valid — no surrogates
        line.encode('utf-8')
        return line
    except UnicodeEncodeError:
        # Contains surrogate characters → original bytes weren't valid UTF-8
        # Re-encode to get original raw bytes, then decode with system encoding
        try:
            raw = line.encode('utf-8', errors='surrogateescape')
            return raw.decode(_SYSTEM_ENCODING, errors='replace')
        except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
            return line.encode('utf-8', errors='replace').decode('utf-8')

PROGRESS_REGEX = re.compile(r'[Dd]ownloading\s+(?:item|video)\s+(\d+)\s+of\s+(\d+)')
SPEED_REGEX = re.compile(r'\[download\]\s+[\d.]+%.*?at\s+~?\s*([\d.]+\S+/s)\s+ETA\s+(\S+)')
SPEED_ONLY_REGEX = re.compile(r'\[download\]\s+[\d.]+%.*?at\s+~?\s*([\d.]+\S+/s)')
PERCENT_REGEX = re.compile(r'\[download\]\s+([\d.]+)%')

# aria2c external downloader progress:
#   [#72ee7e 47MiB/3.9GiB(1%) CN:16 DL:7.8MiB ETA:8m27s]
#   [#5f5b78 512KiB/544KiB(94%) CN:1 DL:66KiB]
ARIA2C_PROGRESS_REGEX = re.compile(r'\[#\w+\s+\S+/\S+\((\d+)%\)')
ARIA2C_SPEED_REGEX = re.compile(r'DL:([\d.]+\s*[A-Za-z/]+)')
ARIA2C_ETA_REGEX = re.compile(r'ETA:(\S+?)\]')

DOWNLOAD_COMPLETE_PATTERNS = ['has already been downloaded']
DOWNLOAD_COMPLETE_100_REGEX = re.compile(r'\[download\]\s+100(?:\.0)?%')
ARCHIVE_SKIP_PATTERNS = ['has already been recorded in the archive']
# aria2c prints "Download complete:" when a file finishes
ARIA2C_COMPLETE_PATTERN = 'Download complete:'

# ══════════════════════════════════════════════════════════════════════════════
#  ЛОКАЛИЗАЦИЯ / LOCALIZATION
# ══════════════════════════════════════════════════════════════════════════════

TRANSLATIONS = {
    "ru": {
        # Заголовки
        "window_title": "🎬 Aura Video Downloader",
        "main_title": "🎬 Aura Video Downloader",
        "subtitle": "Все функции 4K Video Downloader Plus — бесплатно и навсегда",
        
        # Контекстное меню
        "ctx_cut": "Вырезать",
        "ctx_copy": "Копировать",
        "ctx_paste": "Вставить",
        "ctx_select_all": "Выделить всё",
        "ctx_clear": "Очистить",
        
        # Режимы скачивания
        "tab_download": "Загрузка",
        "tab_settings": "Настройки",
        "mode_label": "📦 Режим скачивания:",
        "mode_channel": "📺 Канал",
        "mode_playlist": "📋 Плейлист",
        "mode_video": "🎬 Один ролик",
        "mode_audio": "🎵 Только аудио",
        "mode_channel_desc": "Все видео с канала",
        "mode_playlist_desc": "Все видео из плейлиста",
        "mode_video_desc": "Одно конкретное видео",
        "mode_audio_desc": "Аудио в WAV/MP3/OGG",
        
        # Качество видео
        "video_quality_label": "🎬 Качество видео:",
        "quality_max": "Максимальное",
        "quality_8k": "8K (4320p)",
        "quality_4k": "4K (2160p)",
        "quality_1440p": "1440p (2K)",
        "quality_1080p": "1080p (Full HD)",
        "quality_720p": "720p (HD)",
        "quality_480p": "480p (SD)",
        "quality_360p": "360p",
        "quality_240p": "240p",
        "quality_144p": "144p",
        
        # Настройки аудио
        "audio_format_label": "🎵 Формат аудио:",
        "audio_bitrate_label": "📊 Битрейт:",
        "bitrate_max": "Макс. качество",
        "bitrate_320": "320 kbps",
        "bitrate_256": "256 kbps",
        "bitrate_192": "192 kbps",
        "bitrate_128": "128 kbps",
        "bitrate_96": "96 kbps",
        "bitrate_64": "64 kbps",
        
        # Язык аудиодорожки
        "audio_language_label": "🌐 Язык аудио:",
        "audio_language_hint": "(для видео с несколькими дорожками)",
        
        # Язык метаданных YouTube
        "meta_language_label": "🏷️ Язык названия (YouTube):",
        "meta_language_hint": "(⚠️ временно не работает — баг yt-dlp #13363)",
        "lang_any": "Любой (по умолчанию)",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 Английский",
        "lang_uk": "🇺🇦 Украинский",
        "lang_de": "🇩🇪 Немецкий",
        "lang_fr": "🇫🇷 Французский",
        "lang_es": "🇪🇸 Испанский",
        "lang_it": "🇮🇹 Итальянский",
        "lang_pt": "🇵🇹 Португальский",
        "lang_ja": "🇯🇵 Японский",
        "lang_ko": "🇰🇷 Корейский",
        "lang_zh": "🇨🇳 Китайский",
        "lang_ar": "🇸🇦 Арабский",
        "lang_hi": "🇮🇳 Хинди",
        "lang_bn": "🇧🇩 Бенгальский",
        "lang_tr": "🇹🇷 Турецкий",
        "lang_pl": "🇵🇱 Польский",
        "lang_nl": "🇳🇱 Нидерландский",
        "lang_sv": "🇸🇪 Шведский",
        "lang_da": "🇩🇰 Датский",
        "lang_no": "🇳🇴 Норвежский",
        "lang_fi": "🇫🇮 Финский",
        "lang_cs": "🇨🇿 Чешский",
        "lang_ro": "🇷🇴 Румынский",
        "lang_hu": "🇭🇺 Венгерский",
        "lang_el": "🇬🇷 Греческий",
        "lang_he": "🇮🇱 Иврит",
        "lang_th": "🇹🇭 Тайский",
        "lang_vi": "🇻🇳 Вьетнамский",
        "lang_id": "🇮🇩 Индонезийский",
        "lang_ms": "🇲🇾 Малайский",
        "lang_tl": "🇵🇭 Филиппинский",
        "lang_bg": "🇧🇬 Болгарский",
        "lang_hr": "🇭🇷 Хорватский",
        "lang_sk": "🇸🇰 Словацкий",
        "lang_sr": "🇷🇸 Сербский",
        "lang_lt": "🇱🇹 Литовский",
        "lang_lv": "🇱🇻 Латышский",
        "lang_et": "🇪🇪 Эстонский",
        "lang_ka": "🇬🇪 Грузинский",
        "lang_hy": "🇦🇲 Армянский",
        "lang_az": "🇦🇿 Азербайджанский",
        "lang_kk": "🇰🇿 Казахский",
        "lang_uz": "🇺🇿 Узбекский",
        "lang_be": "🇧🇾 Белорусский",
        "lang_fa": "🇮🇷 Персидский",
        "lang_ta": "🇮🇳 Тамильский",
        "lang_te": "🇮🇳 Телугу",
        "lang_mr": "🇮🇳 Маратхи",
        "lang_ur": "🇵🇰 Урду",
        "lang_sw": "🇰🇪 Суахили",
        "lang_af": "🇿🇦 Африкаанс",
        "lang_ca": "🏴 Каталанский",
        "lang_gl": "🏴 Галисийский",
        "lang_eu": "🏴 Баскский",
        
        # Прокси
        "proxy_label": "🌐 Прокси:",
        "proxy_hint": "Примеры: socks5://127.0.0.1:1080  |  http://user:pass@host:port",
        
        # Субтитры
        "subtitles": "📝 Скачивать субтитры (при наличии)",
        "subtitles_hint": "(встроенные + автосгенерированные, в формате SRT)",
        "setting_subtitles": "  📝 Субтитры:   ",
        "setting_proxy": "  🌐 Прокси:     ",
        "setting_auth": "  🔐 Авториз.:   ",
        "setting_aria2c": "  🚀 aria2c:     ",
        "sub_lang_label": "🗒️ Язык субтитров:",
        "sub_lang_all": "🌍 Все доступные",
        "sub_lang_ru": "🇷🇺 Русский",
        "sub_lang_en": "🇬🇧 Английский",
        "sub_lang_uk": "🇺🇦 Украинский",
        "sub_lang_de": "🇩🇪 Немецкий",
        "sub_lang_fr": "🇫🇷 Французский",
        "sub_lang_es": "🇪🇸 Испанский",
        "sub_lang_it": "🇮🇹 Итальянский",
        "sub_lang_pt": "🇵🇹 Португальский",
        "sub_lang_ja": "🇯🇵 Японский",
        "sub_lang_ko": "🇰🇷 Корейский",
        "sub_lang_zh": "🇨🇳 Китайский",
        "sub_lang_ar": "🇸🇦 Арабский",
        "sub_lang_hi": "🇮🇳 Хинди",
        "sub_lang_tr": "🇹🇷 Турецкий",
        "sub_lang_pl": "🇵🇱 Польский",
        "sub_lang_nl": "🇳🇱 Нидерландский",
        "sub_lang_sv": "🇸🇪 Шведский",
        "sub_lang_cs": "🇨🇿 Чешский",
        "sub_lang_ro": "🇷🇴 Румынский",
        "sub_lang_hu": "🇭🇺 Венгерский",
        "sub_lang_el": "🇬🇷 Греческий",
        "sub_lang_he": "🇮🇱 Иврит",
        "sub_lang_th": "🇹🇭 Тайский",
        "sub_lang_vi": "🇻🇳 Вьетнамский",
        "sub_lang_id": "🇮🇩 Индонезийский",
        "sub_lang_fi": "🇫🇮 Финский",
        "sub_lang_da": "🇩🇰 Датский",
        "sub_lang_no": "🇳🇴 Норвежский",
        "sub_lang_bg": "🇧🇬 Болгарский",
        "sub_lang_hr": "🇭🇷 Хорватский",
        "sub_lang_sk": "🇸🇰 Словацкий",
        "sub_lang_sr": "🇷🇸 Сербский",
        "sub_lang_lt": "🇱🇹 Литовский",
        "sub_lang_lv": "🇱🇻 Латышский",
        "sub_lang_et": "🇪🇪 Эстонский",
        "sub_lang_ka": "🇬🇪 Грузинский",
        "sub_lang_az": "🇦🇿 Азербайджанский",
        "sub_lang_kk": "🇰🇿 Казахский",
        "sub_lang_be": "🇧🇾 Белорусский",
        "sub_lang_fa": "🇮🇷 Персидский",
        
        # Скорость / ETA
        "speed_label": "⚡ Скорость:",
        "speed_idle": "—",
        
        # Авторизация
        "auth_label": "🔐 Авторизация:",
        "auth_none": "Без авторизации",
        "auth_cookies_file": "📄 Файл cookies.txt",
        "auth_chrome": "🌐 Google Chrome",
        "auth_firefox": "🦊 Mozilla Firefox",
        "auth_edge": "🔵 Microsoft Edge",
        "auth_brave": "🦁 Brave",
        "auth_opera": "🔴 Opera",
        "auth_chromium": "⚪ Chromium",
        "auth_safari": "🧭 Safari",
        "auth_hint": "Авторизация через браузер — cookies берутся автоматически",
        "auth_cookies_hint": "Для cookies.txt укажите путь в поле Cookies выше",
        "auth_private_label": "🔒 Приватные плейлисты:",
        "auth_private_hint": "Требуется авторизация через браузер",
        "private_watch_later": "🕐 Отложенные (Watch Later)",
        "private_liked": "❤️ Понравившиеся",
        "private_history": "📜 История",
        
        # Smart Mode (пресеты)
        "smart_mode_label": "⚙️ Smart Mode",
        "smart_mode_hint": "Пресеты настроек — один раз настроил, применяется всегда",
        "smart_save_btn": "💾 Сохранить пресет",
        "smart_load_btn": "📂 Загрузить пресет",
        "smart_delete_btn": "🗑️ Удалить пресет",
        "smart_name_prompt": "Название пресета:",
        "smart_saved": "✅ Пресет сохранён: ",
        "smart_loaded": "✅ Пресет загружен: ",
        "smart_deleted": "🗑️ Пресет удалён: ",
        "smart_no_presets": "Нет сохранённых пресетов",
        "smart_apply_on_start": "🔄 Применять при запуске",
        
        # SponsorBlock (YouTube only)
        "sb_label": "🛡️ SponsorBlock",
        "sb_hint": "Убирает или отмечает рекламные вставки, интро, аутро и т.д. через SponsorBlock API",
        "sb_action_label": "Действие:",
        "sb_action_mark": "📑 Отметить главами",
        "sb_action_remove": "✂️ Вырезать из видео",
        "sb_action_mark_hint": "Рекламные сегменты станут отдельными главами — вы решаете, смотреть или нет",
        "sb_action_remove_hint": "Сегменты будут физически вырезаны из файла (требуется ffmpeg)",
        "sb_cat_sponsor": "💰 Спонсор",
        "sb_cat_intro": "🎬 Интро",
        "sb_cat_outro": "🔚 Аутро",
        "sb_cat_selfpromo": "📢 Самореклама",
        "sb_cat_interaction": "👆 Взаимодействие",
        "sb_cat_preview": "👁️ Превью / анонс",
        "sb_cat_filler": "💬 Отступления",
        "sb_cat_music_offtopic": "🎵 Не по теме (музыка)",
        "sb_enabled_log": "🛡️ SponsorBlock: {action} [{cats}]",
        "sb_force_keyframes": "🔑 Точная обрезка",
        "sb_force_keyframes_hint": "Перекодирует на границах — без артефактов, но медленнее",
        "sb_reencode_warn": "⚠️ SponsorBlock + Точная обрезка\n\nЭтот режим перекодирует видео целиком.\nСкачивание займёт значительно больше времени.\n\nПродолжить?",
        
        # aria2c / Многопоточная загрузка
        "aria2c_label": "🚀 Многопоточная загрузка (aria2c)",
        "aria2c_hint": "Разбивает файл на части и скачивает параллельно",
        "aria2c_threads_label": "Потоков:",
        "concurrent_videos_label": "📥 Параллельно:",
        "concurrent_videos_hint": "Сколько видео скачивать одновременно (для плейлистов/каналов)",
        "aria2c_not_found": "⚠️ aria2c не найден. Установите: https://aria2.github.io",
        "aria2c_enabled": "🚀 aria2c включён ({threads} потоков)",
        
        # Импорт / Экспорт
        "import_export_label": "📦 Импорт / Экспорт",
        "import_btn": "📥 Импорт ссылок",
        "export_btn": "📤 Экспорт истории",
        "import_success": "✅ Импортировано ссылок: {count}",
        "import_error": "❌ Ошибка импорта: ",
        "export_success": "✅ История экспортирована: ",
        "export_empty": "⚠️ Нечего экспортировать",
        "import_formats": "Файлы ссылок",
        
        # Менеджер загрузок
        "dm_tab_all": "📋 Все",
        "dm_tab_video": "🎬 Видео",
        "dm_tab_audio": "🎵 Аудио",
        "dm_tab_playlist": "📁 Плейлисты",
        "dm_search_placeholder": "🔍 Фильтр по имени...",
        "dm_sort_date": "📅 По дате",
        "dm_sort_name": "📝 По имени",
        "dm_sort_size": "📏 По размеру",
        "dm_col_name": "Название",
        "dm_col_status": "Статус",
        "dm_col_size": "Размер",
        "dm_col_date": "Дата",
        "dm_status_done": "✅ Готово",
        "dm_status_downloading": "⬇️ Загрузка...",
        "dm_status_error": "❌ Ошибка",
        "dm_status_queued": "⏳ В очереди",
        "dm_clear_completed": "🧹 Очистить завершённые",
        
        # Дополнительные строки
        "error_title": "Ошибка",
        "nodejs_opening_browser": "Открываем страницу загрузки Node.js...",
        "reset_confirm": "Удалить ВСЕ настройки программы и закрыть?\n\nПри следующем запуске программа запустится как в первый раз.",
        "settings_reset": "✅ Все настройки удалены. Программа закрывается...",
        "reset_log_header": "🗑️ === ПОЛНЫЙ СБРОС НАСТРОЕК ===",
        "reset_cleanup_launched": "  ✅ Настройки успешно удалены",
        "settings_migrated": "  🔄 Настройки обновлены до новой версии:",
        "settings_key_added": "     + {key} = {value}",
        "settings_key_removed": "     − {key} (больше не используется)",
        "settings_up_to_date": "  ✅ Файл настроек актуален ({count} параметров)",
        "settings_file_saved": "     💾 Файл сохранён: {path}",
        "log_mode": "  Режим: {mode}",
        "log_title_lang": "  🏷️ Язык заголовков: {lang}",
        "log_ytdlp_titles_note": "  ⚠️ Перевод заголовков сейчас сломан в yt-dlp (баг #13363)",
        "log_ytdlp_titles_note2": "     Заработает автоматически когда yt-dlp починит",
        "log_parallel": "🚀 Параллельное скачивание: {n} видео одновременно",
        "log_worker_task": "  Поток {id}/{total}: --playlist-items {items}",
        "log_worker_done": "  ℹ️ Поток завершён (код {code}), ещё {remaining}...",
        "theme_restart": "Тема сохранена. Перезапустите программу для применения.",
        "theme_title": "🎨 Тема",
        "update_ytdlp_ok": "✅ yt-dlp успешно обновлён!",
        "restart_mode": "🔄 Режим перезапуска: загрузка по одному видео...",
        "smart_select_preset": "— Выберите пресет —",
        "paths_label": "📂 Пути и файлы",
        "history_label": "📜 История загрузок",
        "settings_label": "🔧 Настройки приложения",
        "log_title": "📋 Лог",
        "browse_folder_tip": "Выбрать папку",
        "browse_file_tip": "Выбрать файл",
        "open_folder_btn": "📂 Открыть папку",
        "open_folder_err": "❌ Папка не найдена",
        "stop_confirm": "Остановить загрузку?",
        "url_examples_title": "💡 Примеры URL:",
        "progress_done": "✅ Завершено",
        
        # Шутки про 4K Video Downloader
        "joke_welcome": [
            "💸 Бесплатно. Без пробного периода. Без «купите PRO за $45».",
            "🏠 Вы только что сэкономили $45. Можете поблагодарить нас позже.",
            "⚡ Работает на yt-dlp — как и 4K Video Downloader, только честно.",
            "🎭 4K VD+ берёт $45 за GUI к yt-dlp. Мы — нет. Совпадение?",
            "💎 Premium-функции бесплатно? Это не баг, это фича.",
            "🤡 4K VD+ сломался после обновления? Классика. Мы стабильны.",
            "🔥 Тот же yt-dlp, только без жадности разработчиков за $45.",
            f"💰 $45 за обёртку yt-dlp? В {datetime.datetime.now().year}? Серьёзно?",
        ],
        "joke_finish": [
            "✅ Готово! И всё это — бесплатно. Представьте, что вы заплатили $45.",
            "✅ Загрузка завершена. 4K VD+ — в шоке от бесплатных конкурентов.",
            "✅ Бесплатно скачано то, за что другие берут деньги.",
        ],
        
        # Источник аудио
        "audio_source_label": "📥 Источник:",
        "audio_source_video": "🎬 Один ролик",
        "audio_source_playlist": "📋 Плейлист",
        "audio_source_channel": "📺 Канал",
        "audio_source_video_desc": "Аудио из одного видео",
        "audio_source_playlist_desc": "Аудио из всего плейлиста",
        "audio_source_channel_desc": "Аудио со всего канала 🤯",
        "url_label_audio_video": "🔗 URL видео:",
        "url_label_audio_playlist": "🔗 URL плейлиста:",
        "url_label_audio_channel": "🔗 URL канала:",
        "url_hint_audio_video": "Примеры: youtube.com/watch?v=xxxxxx  |  youtu.be/xxxxxx",
        "url_hint_audio_playlist": "Примеры: youtube.com/playlist?list=PLxxxxxx",
        "url_hint_audio_channel": "Примеры: youtube.com/@handle  |  youtube.com/channel/UCxxxxxx",
        "warn_audio_channel": "⚠️ Аудио со всего канала...\n\n🤔 А вы задумывались, что 90% видео на YouTube\nбез картинки — это просто странные звуки\nи фраза «как вы видите на экране»?\n\nНо кто я такой, чтобы вас останавливать.\nПродолжить?",
        "folder_struct_audio_video": "название [id].{format} (без вложенных папок)",
        "folder_struct_audio_playlist": "Папка канала / Папка плейлиста / нумерация. название [id].{format}",
        "folder_struct_audio_channel": "Папка канала / нумерация. название [id].{format}",
        "folder_struct_audio_playlist_no_num": "Папка канала / Папка плейлиста / название [id].{format}",
        "folder_struct_audio_channel_no_num": "Папка канала / название [id].{format}",
        
        # Опции
        "options_label": "⚙️ Опции:",
        "restart_each_video": "🔄 Перезапускать процесс после каждого ролика",
        "restart_each_video_hint": "(помогает при долгих загрузках и ошибках соединения)",
        "notify_on_finish": "🔔 Уведомление по завершении",
        "notify_on_finish_hint": "Показать системное уведомление когда все загрузки завершены",
        "notify_title_done": "✅ Загрузка завершена",
        "notify_title_error": "⚠️ Загрузка завершена с ошибками",
        "tray_close": "Закрыть Aura Video Downloader",
        "tray_reset": "Сбросить настройки",
        "debug_banner": "РЕЖИМ ОТЛАДКИ — настройки НЕ сохраняются",
        "no_numbering": "🔢 Без нумерации файлов",
        "no_numbering_hint": "(убирает 00001. в начале имени файла)",
        "reverse_playlist": "📊 От старых к новым",
        "reverse_playlist_hint": "(если выкл — от новых к старым)",
        "use_archive": "📜 Использовать archive.txt",
        "use_archive_hint": "(пропускать уже скачанные видео)",
        
        # Поля ввода
        "url_label_channel": "🔗 URL канала:",
        "url_label_playlist": "🔗 URL плейлиста:",
        "url_label_video": "🔗 URL видео:",
        "url_hint_channel": "Примеры: youtube.com/@handle  |  youtube.com/channel/UCxxxxxx",
        "url_hint_playlist": "Примеры: youtube.com/playlist?list=PLxxxxxx  |  ссылка на видео из плейлиста",
        "url_hint_video": "Примеры: youtube.com/watch?v=xxxxxx  |  youtu.be/xxxxxx",
        "outdir_label": "📁 Папка для загрузки:",
        "cookies_label": "🍪 Файл cookies.txt:",
        "cookies_hint": "💡 Используйте расширение «Get cookies.txt LOCALLY» для экспорта cookies из браузера",
        
        # Кнопки
        "browse_folder": "📂 Выбрать через Проводник...",
        "browse_file": "📄 Выбрать через Проводник...",
        "start_btn": "▶️  НАЧАТЬ ЗАГРУЗКУ",
        "stop_btn": "⏹️  ОСТАНОВИТЬ",
        "clear_log_btn": "🗑️  Очистить лог",
        "update_ytdlp_btn": "🔄 yt-dlp → master",
        "reset_settings_btn": "🗑️ Сброс настроек",
        "change_theme_btn": "🎨 Сменить тему",
        "change_platform_btn": "🔄 Сменить платформу",
        "update_nodejs_btn": "📥 Скачать Node.js",
        "nodejs_download_title": "Скачать Node.js",
        "nodejs_download_msg": "Откроется страница загрузки Node.js.\n\nСкачайте LTS версию, установите и перезагрузите компьютер.",
        "reset_settings_confirm_title": "Подтверждение сброса",
        "reset_settings_confirm": "Вы уверены, что хотите удалить все настройки?\n\nПрограмма закроется и при следующем запуске\nпредложит выбрать папку для настроек заново.",
        "reset_settings_done": "Настройки удалены. Программа закрывается...",
        
        # Статус зависимостей
        "deps_frame": "⚙️ Статус зависимостей",
        "checking": "⏳ Проверка...",
        "installed": "✅ Установлен",
        "not_found": "❌ НЕ НАЙДЕН",
        "pywin32_ok": "✅ Установлен (полноценные диалоги)",
        "pywin32_no": "⚠️ Не установлен (диалоги через tkinter)",
        
        # Лог
        "log_frame": "📋 Лог выполнения",
        "welcome_line2": "Выбор качества • Без лишнего перекодирования",
        
        # Счётчик прогресса
        "progress_label": "📊 Прогресс:",
        "progress_format": "{downloaded} / {total}",
        "progress_idle": "—",
        "progress_scanning": "сканирование...",
        
        # Сообщения проверки
        "checking_deps": "🔍 Проверка зависимостей...",
        "ytdlp_found": "  ✅ yt-dlp: ",
        "ytdlp_not_found": "  ❌ yt-dlp: НЕ НАЙДЕН в PATH!",
        "ytdlp_install_hint": "     Установите: pip install yt-dlp",
        "ffmpeg_found": "  ✅ ffmpeg: установлен",
        "ffmpeg_not_found": "  ❌ ffmpeg: НЕ НАЙДЕН в PATH!",
        "aria2c_found": "  ✅ aria2c:     найден",
        "aria2c_missing_log": "  ℹ️ aria2c:     не найден (необязательный)",
        "optional": "необязательный",
        "ffmpeg_install_hint": "     Скачайте с ffmpeg.org и добавьте в PATH",
        "pywin32_found": "  ✅ pywin32: установлен (диалоги через COM API)",
        "pywin32_not_found": "  ⚠️ pywin32: не установлен",
        "pywin32_install_hint": "     Для лучших диалогов: pip install pywin32",
        "nodejs_found": "  ✅ Node.js: ",
        "nodejs_not_found": "  ⚠️ Node.js: НЕ НАЙДЕН",
        "nodejs_warning": "     ⚠️ Cookies не будут работать без Node.js!",
        "nodejs_install_hint": "     Скачайте LTS с nodejs.org и перезагрузите ПК",
        "settings_folder": "  📁 Папка настроек: ",
        "ytdlp_config_created": "  📄 Конфиг yt-dlp: ",
        
        # Обновление yt-dlp
        "updating_ytdlp": "🔄 Обновление yt-dlp до master...",
        "updating_cmd": "   Выполняется: yt-dlp -U --update-to master",
        "update_done": "✅ Обновление завершено!",
        "update_error": "❌ Ошибка обновления: ",
        
        # Диалоги выбора
        "select_folder_title": "Выберите папку для сохранения видео",
        "select_file_title": "Выберите cookies.txt",
        "folder_selected": "📁 Выбрана папка: ",
        "file_selected": "🍪 Выбран файл: ",
        
        # Ошибки валидации
        "error": "Ошибка",
        "error_input": "Ошибка ввода",
        "warning": "Предупреждение",
        "error_no_url": "❌ Введите URL!\n\nПримеры:\n• youtube.com/@channelname\n• youtube.com/watch?v=xxxxxx",
        "error_invalid_url": "❌ Некорректный формат URL!\n\nURL должен содержать адрес сайта.\n\nПримеры:\n• https://youtube.com/@channelname\n• youtube.com/watch?v=xxxxxx",
        "warn_not_youtube": "URL не похож на YouTube-ссылку.\n\nПродолжить всё равно?",
        "error_no_outdir": "❌ Выберите папку для загрузки!\n\nНажмите кнопку «Выбрать через Проводник...»",
        "error_create_folder": "❌ Не удалось создать папку:\n\n{path}\n\nОшибка: {error}",
        "error_no_cookies": "❌ Выберите файл cookies.txt!\n\nИспользуйте расширение браузера для экспорта cookies.",
        "error_cookies_not_found": "❌ Файл cookies не найден:\n\n{path}",
        
        # Загрузка
        "folder_created": "📁 Создана папка: ",
        "url_videos_added": "ℹ️ Автоматически добавлено /videos к URL",
        "starting_download": "▶️  Запуск загрузки...",
        "stopping_download": "⏹️  Остановка загрузки...",
        "stop_hint": "   При следующем запуске загрузка продолжится с того же места",
        "download_success": "✅ ЗАГРУЗКА УСПЕШНО ЗАВЕРШЕНА!",
        "download_exit_code": "⚠️ Процесс завершился с кодом: ",
        "download_exit_hint": "   Это может быть нормально если часть видео уже была скачана",
        "download_error": "❌ Ошибка выполнения: ",
        "download_started": "▶ Загрузка начата",
        "download_complete": "Загрузка завершена",
        "download_stopped": "Загрузка остановлена",
        "restarting_process": "🔄 Перезапуск процесса (скачано {count})...",
        "all_videos_downloaded": "✅ Все видео скачаны!",
        
        # Сводка настроек
        "settings_summary": "📋 СВОДКА НАСТРОЕК",
        "setting_mode": "  📦 Режим:      ",
        "setting_url": "  🔗 URL:        ",
        "setting_folder": "  📁 Папка:      ",
        "setting_cookies": "  🍪 Cookies:    ",
        "setting_archive": "  📜 Архив:      archive.txt",
        "setting_no_archive": "  📜 Архив:      не применимо (один файл)",
        "setting_archive_disabled": "  📜 Архив:      отключён пользователем",
        "setting_quality": "  🎬 Качество:   ",
        "setting_audio_lang": "  🌐 Язык аудио: ",
        "setting_format": "  🎬 Формат:     ",
        "setting_audio_format": "  🎵 Аудио:      ",
        "setting_bitrate": "  📊 Битрейт:    ",
        "setting_order": "  📊 Порядок:    старые → новые (playlist_reverse)",
        "setting_order_newest": "  📊 Порядок:    новые → старые",
        "setting_order_single": "  📊 Порядок:    не применимо (один файл)",
        "setting_retries": "  🔄 Ретраи:     infinite (пауза 5 сек между попытками)",
        "setting_restart": "  🔁 Рестарт:    после каждого ролика",
        "setting_no_restart": "  🔁 Рестарт:    выключен (один процесс)",
        "audio_no_compression": " (без сжатия)",
        
        # Структура папок
        "folder_structure": "  📂 Структура:  ",
        "folder_struct_channel": "Папка канала / нумерация. название [id].ext",
        "folder_struct_playlist": "Папка канала / Папка плейлиста / нумерация. название [id].ext",
        "folder_struct_video": "название [id].ext (без вложенных папок)",
        "folder_struct_channel_no_num": "Папка канала / название [id].ext",
        "folder_struct_playlist_no_num": "Папка канала / Папка плейлиста / название [id].ext",
        
        # Сохранение настроек
        "settings_saved": "💾 Настройки сохранены",
        "settings_loaded": "📂 Настройки загружены",
        
        # === ВЫБОР ПЛАТФОРМЫ ===
        "platform_title": "Выберите платформу",
        "platform_youtube": "▶️ YouTube",
        "platform_vk": "📹 VK Video",
        
        # === VK VIDEO ===
        "vk_window_title": "📹 VK Video Downloader",
        "vk_main_title": "📹 VK Video Downloader",
        "vk_subtitle": "Скачивание VK Video в выбранном качестве",
        "vk_mode_channel": "👥 Сообщество",
        "vk_mode_channel_desc": "Все видео сообщества/пользователя",
        "vk_url_label_channel": "🔗 URL страницы с видео:",
        "vk_url_hint_channel": "Примеры: vk.com/videos-123456  |  vk.com/video/@group  |  vkvideo.ru/@user/videos",
        "vk_url_label_playlist": "🔗 URL плейлиста VK:",
        "vk_url_hint_playlist": "Примеры: vk.com/video/playlist/-123456_1  |  vkvideo.ru/playlist/-123456_1",
        "vk_url_label_video": "🔗 URL видео VK:",
        "vk_url_hint_video": "Примеры: vk.com/video-123456_789  |  vk.com/clip-123456_789  |  vkvideo.ru/video-123456_789",
        "vk_audio_source_channel": "📺 Сообщество",
        "vk_audio_source_channel_desc": "Аудио со всех видео сообщества/пользователя 🤯",
        "vk_url_label_audio_video": "🔗 URL видео VK:",
        "vk_url_hint_audio_video": "Примеры: vk.com/video-123456_789  |  vkvideo.ru/video-123456_789",
        "vk_url_label_audio_playlist": "🔗 URL плейлиста VK:",
        "vk_url_hint_audio_playlist": "Примеры: vk.com/video/playlist/-123456_1  |  vkvideo.ru/playlist/-123456_1",
        "vk_url_label_audio_channel": "🔗 URL страницы с видео:",
        "vk_url_hint_audio_channel": "Примеры: vk.com/videos-123456  |  vkvideo.ru/@user/videos",
        "vk_warn_audio_channel": "⚠️ Аудио со всех видео сообщества...\n\nЭто может занять ОЧЕНЬ много времени.\nПродолжить?",
        "vk_warn_not_platform": "URL не похож на VK-ссылку.\n\nПродолжить всё равно?",
        "vk_cookies_hint": "💡 Используйте расширение «Get cookies.txt LOCALLY» для экспорта cookies из VK",
        "vk_nodejs_not_needed": "  ℹ️ Node.js: не требуется для VK Video",
    },
    
    "en": {
        # Headers
        "window_title": "🎬 Aura Video Downloader",
        "main_title": "🎬 Aura Video Downloader",
        "subtitle": "All features of 4K Video Downloader Plus — free forever",
        
        # Context menu
        "ctx_cut": "Cut",
        "ctx_copy": "Copy",
        "ctx_paste": "Paste",
        "ctx_select_all": "Select All",
        "ctx_clear": "Clear",
        
        # Download modes
        "tab_download": "Download",
        "tab_settings": "Settings",
        "mode_label": "📦 Download mode:",
        "mode_channel": "📺 Channel",
        "mode_playlist": "📋 Playlist",
        "mode_video": "🎬 Single video",
        "mode_audio": "🎵 Audio only",
        "mode_channel_desc": "All videos from channel",
        "mode_playlist_desc": "All videos from playlist",
        "mode_video_desc": "One specific video",
        "mode_audio_desc": "Audio as WAV/MP3/OGG",
        
        # Video quality
        "video_quality_label": "🎬 Video quality:",
        "quality_max": "Maximum",
        "quality_8k": "8K (4320p)",
        "quality_4k": "4K (2160p)",
        "quality_1440p": "1440p (2K)",
        "quality_1080p": "1080p (Full HD)",
        "quality_720p": "720p (HD)",
        "quality_480p": "480p (SD)",
        "quality_360p": "360p",
        "quality_240p": "240p",
        "quality_144p": "144p",
        
        # Audio settings
        "audio_format_label": "🎵 Audio format:",
        "audio_bitrate_label": "📊 Bitrate:",
        "bitrate_max": "Max quality",
        "bitrate_320": "320 kbps",
        "bitrate_256": "256 kbps",
        "bitrate_192": "192 kbps",
        "bitrate_128": "128 kbps",
        "bitrate_96": "96 kbps",
        "bitrate_64": "64 kbps",
        
        # Audio language
        "audio_language_label": "🌐 Audio language:",
        "audio_language_hint": "(for videos with multiple audio tracks)",
        
        # YouTube metadata language
        "meta_language_label": "🏷️ Title language (YouTube):",
        "meta_language_hint": "(⚠️ temporarily broken — yt-dlp bug #13363)",
        "lang_any": "Any (default)",
        "lang_ru": "🇷🇺 Russian",
        "lang_en": "🇬🇧 English",
        "lang_uk": "🇺🇦 Ukrainian",
        "lang_de": "🇩🇪 German",
        "lang_fr": "🇫🇷 French",
        "lang_es": "🇪🇸 Spanish",
        "lang_it": "🇮🇹 Italian",
        "lang_pt": "🇵🇹 Portuguese",
        "lang_ja": "🇯🇵 Japanese",
        "lang_ko": "🇰🇷 Korean",
        "lang_zh": "🇨🇳 Chinese",
        "lang_ar": "🇸🇦 Arabic",
        "lang_hi": "🇮🇳 Hindi",
        "lang_bn": "🇧🇩 Bengali",
        "lang_tr": "🇹🇷 Turkish",
        "lang_pl": "🇵🇱 Polish",
        "lang_nl": "🇳🇱 Dutch",
        "lang_sv": "🇸🇪 Swedish",
        "lang_da": "🇩🇰 Danish",
        "lang_no": "🇳🇴 Norwegian",
        "lang_fi": "🇫🇮 Finnish",
        "lang_cs": "🇨🇿 Czech",
        "lang_ro": "🇷🇴 Romanian",
        "lang_hu": "🇭🇺 Hungarian",
        "lang_el": "🇬🇷 Greek",
        "lang_he": "🇮🇱 Hebrew",
        "lang_th": "🇹🇭 Thai",
        "lang_vi": "🇻🇳 Vietnamese",
        "lang_id": "🇮🇩 Indonesian",
        "lang_ms": "🇲🇾 Malay",
        "lang_tl": "🇵🇭 Filipino",
        "lang_bg": "🇧🇬 Bulgarian",
        "lang_hr": "🇭🇷 Croatian",
        "lang_sk": "🇸🇰 Slovak",
        "lang_sr": "🇷🇸 Serbian",
        "lang_lt": "🇱🇹 Lithuanian",
        "lang_lv": "🇱🇻 Latvian",
        "lang_et": "🇪🇪 Estonian",
        "lang_ka": "🇬🇪 Georgian",
        "lang_hy": "🇦🇲 Armenian",
        "lang_az": "🇦🇿 Azerbaijani",
        "lang_kk": "🇰🇿 Kazakh",
        "lang_uz": "🇺🇿 Uzbek",
        "lang_be": "🇧🇾 Belarusian",
        "lang_fa": "🇮🇷 Persian",
        "lang_ta": "🇮🇳 Tamil",
        "lang_te": "🇮🇳 Telugu",
        "lang_mr": "🇮🇳 Marathi",
        "lang_ur": "🇵🇰 Urdu",
        "lang_sw": "🇰🇪 Swahili",
        "lang_af": "🇿🇦 Afrikaans",
        "lang_ca": "🏴 Catalan",
        "lang_gl": "🏴 Galician",
        "lang_eu": "🏴 Basque",
        
        # Proxy
        "proxy_label": "🌐 Proxy:",
        "proxy_hint": "Examples: socks5://127.0.0.1:1080  |  http://user:pass@host:port",
        
        # Subtitles
        "subtitles": "📝 Download subtitles (if available)",
        "subtitles_hint": "(embedded + auto-generated, SRT format)",
        "setting_subtitles": "  📝 Subtitles:  ",
        "setting_proxy": "  🌐 Proxy:      ",
        "setting_auth": "  🔐 Auth:       ",
        "setting_aria2c": "  🚀 aria2c:     ",
        "sub_lang_label": "🗒️ Subtitle language:",
        "sub_lang_all": "🌍 All available",
        "sub_lang_ru": "🇷🇺 Russian",
        "sub_lang_en": "🇬🇧 English",
        "sub_lang_uk": "🇺🇦 Ukrainian",
        "sub_lang_de": "🇩🇪 German",
        "sub_lang_fr": "🇫🇷 French",
        "sub_lang_es": "🇪🇸 Spanish",
        "sub_lang_it": "🇮🇹 Italian",
        "sub_lang_pt": "🇵🇹 Portuguese",
        "sub_lang_ja": "🇯🇵 Japanese",
        "sub_lang_ko": "🇰🇷 Korean",
        "sub_lang_zh": "🇨🇳 Chinese",
        "sub_lang_ar": "🇸🇦 Arabic",
        "sub_lang_hi": "🇮🇳 Hindi",
        "sub_lang_tr": "🇹🇷 Turkish",
        "sub_lang_pl": "🇵🇱 Polish",
        "sub_lang_nl": "🇳🇱 Dutch",
        "sub_lang_sv": "🇸🇪 Swedish",
        "sub_lang_cs": "🇨🇿 Czech",
        "sub_lang_ro": "🇷🇴 Romanian",
        "sub_lang_hu": "🇭🇺 Hungarian",
        "sub_lang_el": "🇬🇷 Greek",
        "sub_lang_he": "🇮🇱 Hebrew",
        "sub_lang_th": "🇹🇭 Thai",
        "sub_lang_vi": "🇻🇳 Vietnamese",
        "sub_lang_id": "🇮🇩 Indonesian",
        "sub_lang_fi": "🇫🇮 Finnish",
        "sub_lang_da": "🇩🇰 Danish",
        "sub_lang_no": "🇳🇴 Norwegian",
        "sub_lang_bg": "🇧🇬 Bulgarian",
        "sub_lang_hr": "🇭🇷 Croatian",
        "sub_lang_sk": "🇸🇰 Slovak",
        "sub_lang_sr": "🇷🇸 Serbian",
        "sub_lang_lt": "🇱🇹 Lithuanian",
        "sub_lang_lv": "🇱🇻 Latvian",
        "sub_lang_et": "🇪🇪 Estonian",
        "sub_lang_ka": "🇬🇪 Georgian",
        "sub_lang_az": "🇦🇿 Azerbaijani",
        "sub_lang_kk": "🇰🇿 Kazakh",
        "sub_lang_be": "🇧🇾 Belarusian",
        "sub_lang_fa": "🇮🇷 Persian",
        
        # Speed / ETA
        "speed_label": "⚡ Speed:",
        "speed_idle": "—",
        
        # Authorization
        "auth_label": "🔐 Authorization:",
        "auth_none": "No authorization",
        "auth_cookies_file": "📄 Cookies.txt file",
        "auth_chrome": "🌐 Google Chrome",
        "auth_firefox": "🦊 Mozilla Firefox",
        "auth_edge": "🔵 Microsoft Edge",
        "auth_brave": "🦁 Brave",
        "auth_opera": "🔴 Opera",
        "auth_chromium": "⚪ Chromium",
        "auth_safari": "🧭 Safari",
        "auth_hint": "Auth via browser — cookies are extracted automatically",
        "auth_cookies_hint": "For cookies.txt specify the path in Cookies field above",
        "auth_private_label": "🔒 Private playlists:",
        "auth_private_hint": "Requires browser authorization",
        "private_watch_later": "🕐 Watch Later",
        "private_liked": "❤️ Liked Videos",
        "private_history": "📜 History",
        
        # Smart Mode (presets)
        "smart_mode_label": "⚙️ Smart Mode",
        "smart_mode_hint": "Setting presets — configure once, apply always",
        "smart_save_btn": "💾 Save preset",
        "smart_load_btn": "📂 Load preset",
        "smart_delete_btn": "🗑️ Delete preset",
        "smart_name_prompt": "Preset name:",
        "smart_saved": "✅ Preset saved: ",
        "smart_loaded": "✅ Preset loaded: ",
        "smart_deleted": "🗑️ Preset deleted: ",
        "smart_no_presets": "No saved presets",
        "smart_apply_on_start": "🔄 Apply on startup",
        
        # SponsorBlock (YouTube only)
        "sb_label": "🛡️ SponsorBlock",
        "sb_hint": "Mark or remove sponsor segments, intros, outros, etc. via SponsorBlock API",
        "sb_action_label": "Action:",
        "sb_action_mark": "📑 Mark as chapters",
        "sb_action_remove": "✂️ Remove from video",
        "sb_action_mark_hint": "Sponsor segments become separate chapters — you decide whether to watch",
        "sb_action_remove_hint": "Segments are physically cut from file (requires ffmpeg)",
        "sb_cat_sponsor": "💰 Sponsor",
        "sb_cat_intro": "🎬 Intro",
        "sb_cat_outro": "🔚 Outro",
        "sb_cat_selfpromo": "📢 Self-promo",
        "sb_cat_interaction": "👆 Interaction",
        "sb_cat_preview": "👁️ Preview",
        "sb_cat_filler": "💬 Filler / tangent",
        "sb_cat_music_offtopic": "🎵 Off-topic music",
        "sb_enabled_log": "🛡️ SponsorBlock: {action} [{cats}]",
        "sb_force_keyframes": "🔑 Precise cuts",
        "sb_force_keyframes_hint": "Re-encodes at boundaries — no artifacts, but slower",
        "sb_reencode_warn": "⚠️ SponsorBlock + Precise cuts\n\nThis mode will re-encode the entire video.\nDownloading will take significantly longer.\n\nContinue?",
        
        # aria2c / Multi-threaded download
        "aria2c_label": "🚀 Multi-threaded download (aria2c)",
        "aria2c_hint": "Splits file into parts and downloads in parallel",
        "aria2c_threads_label": "Threads:",
        "concurrent_videos_label": "📥 Parallel:",
        "concurrent_videos_hint": "How many videos to download simultaneously (for playlists/channels)",
        "aria2c_not_found": "⚠️ aria2c not found. Install: https://aria2.github.io",
        "aria2c_enabled": "🚀 aria2c enabled ({threads} threads)",
        
        # Import / Export
        "import_export_label": "📦 Import / Export",
        "import_btn": "📥 Import links",
        "export_btn": "📤 Export history",
        "import_success": "✅ Links imported: {count}",
        "import_error": "❌ Import error: ",
        "export_success": "✅ History exported: ",
        "export_empty": "⚠️ Nothing to export",
        "import_formats": "Link files",
        
        # Download Manager
        "dm_tab_all": "📋 All",
        "dm_tab_video": "🎬 Video",
        "dm_tab_audio": "🎵 Audio",
        "dm_tab_playlist": "📁 Playlists",
        "dm_search_placeholder": "🔍 Filter by name...",
        "dm_sort_date": "📅 By date",
        "dm_sort_name": "📝 By name",
        "dm_sort_size": "📏 By size",
        "dm_col_name": "Name",
        "dm_col_status": "Status",
        "dm_col_size": "Size",
        "dm_col_date": "Date",
        "dm_status_done": "✅ Done",
        "dm_status_downloading": "⬇️ Downloading...",
        "dm_status_error": "❌ Error",
        "dm_status_queued": "⏳ Queued",
        "dm_clear_completed": "🧹 Clear completed",
        
        # Additional strings
        "error_title": "Error",
        "nodejs_opening_browser": "Opening Node.js download page...",
        "reset_confirm": "Delete ALL program settings and close?\n\nOn next launch the program will start fresh.",
        "settings_reset": "✅ All settings deleted. Closing...",
        "reset_log_header": "🗑️ === FULL SETTINGS RESET ===",
        "reset_cleanup_launched": "  ✅ Settings deleted successfully",
        "settings_migrated": "  🔄 Settings updated to new version:",
        "settings_key_added": "     + {key} = {value}",
        "settings_key_removed": "     − {key} (no longer used)",
        "settings_up_to_date": "  ✅ Settings file is up to date ({count} keys)",
        "settings_file_saved": "     💾 File saved: {path}",
        "log_mode": "  Mode: {mode}",
        "log_title_lang": "  🏷️ Title language: {lang}",
        "log_ytdlp_titles_note": "  ⚠️ Note: translated titles are currently broken in yt-dlp (bug #13363)",
        "log_ytdlp_titles_note2": "     Will work automatically when yt-dlp fixes it",
        "log_parallel": "🚀 Parallel download: {n} videos at once",
        "log_worker_task": "  Worker {id}/{total}: --playlist-items {items}",
        "log_worker_done": "  ℹ️ Worker finished (code {code}), {remaining} still running...",
        "theme_restart": "Theme saved. Restart the app to apply.",
        "theme_title": "🎨 Theme",
        "update_ytdlp_ok": "✅ yt-dlp updated successfully!",
        "restart_mode": "🔄 Restart mode: downloading one at a time...",
        "smart_select_preset": "— Select preset —",
        "paths_label": "📂 Paths & Files",
        "history_label": "📜 Download History",
        "settings_label": "🔧 App Settings",
        "log_title": "📋 Log",
        "browse_folder_tip": "Select folder",
        "browse_file_tip": "Select file",
        "open_folder_btn": "📂 Open folder",
        "open_folder_err": "❌ Folder not found",
        "stop_confirm": "Stop download?",
        "url_examples_title": "💡 URL examples:",
        "progress_done": "✅ Complete",
        "joke_welcome": [
            "💸 Free. No trial. No \"buy PRO for $45\" popups.",
            "🏠 You just saved $45. You're welcome.",
            "⚡ Powered by yt-dlp — just like 4K Video Downloader, but honest.",
            "🎭 4K VD+ charges $45 for a yt-dlp GUI. We don't. Coincidence?",
            "💎 Premium features for free? Not a bug, it's a feature.",
            "🤡 4K VD+ broke after an update? Classic. We're stable.",
            "🔥 Same yt-dlp, zero developer greed at $45.",
            f"💰 $45 for a yt-dlp wrapper? In {datetime.datetime.now().year}? Really?",
        ],
        "joke_finish": [
            "✅ Done! And all of this — for free. Imagine paying $45.",
            "✅ Download complete. 4K VD+ in shambles seeing free competitors.",
            "✅ Downloaded for free what others charge money for.",
        ],
        
        # Audio source
        "audio_source_label": "📥 Source:",
        "audio_source_video": "🎬 Single video",
        "audio_source_playlist": "📋 Playlist",
        "audio_source_channel": "📺 Channel",
        "audio_source_video_desc": "Audio from one video",
        "audio_source_playlist_desc": "Audio from entire playlist",
        "audio_source_channel_desc": "Audio from entire channel 🤯",
        "url_label_audio_video": "🔗 Video URL:",
        "url_label_audio_playlist": "🔗 Playlist URL:",
        "url_label_audio_channel": "🔗 Channel URL:",
        "url_hint_audio_video": "Examples: youtube.com/watch?v=xxxxxx  |  youtu.be/xxxxxx",
        "url_hint_audio_playlist": "Examples: youtube.com/playlist?list=PLxxxxxx",
        "url_hint_audio_channel": "Examples: youtube.com/@handle  |  youtube.com/channel/UCxxxxxx",
        "warn_audio_channel": "⚠️ Audio from the entire channel...\n\n🤔 Have you considered that 90% of YouTube videos\nwithout the picture are just weird sounds\nand the phrase \"as you can see on the screen\"?\n\nBut who am I to stop you.\nContinue?",
        "folder_struct_audio_video": "title [id].{format} (no subfolders)",
        "folder_struct_audio_playlist": "Channel folder / Playlist folder / number. title [id].{format}",
        "folder_struct_audio_channel": "Channel folder / number. title [id].{format}",
        "folder_struct_audio_playlist_no_num": "Channel folder / Playlist folder / title [id].{format}",
        "folder_struct_audio_channel_no_num": "Channel folder / title [id].{format}",
        
        # Options
        "options_label": "⚙️ Options:",
        "restart_each_video": "🔄 Restart process after each video",
        "restart_each_video_hint": "(helps with long downloads and connection errors)",
        "notify_on_finish": "🔔 Notify on finish",
        "notify_on_finish_hint": "Show system notification when all downloads are complete",
        "notify_title_done": "✅ Download complete",
        "notify_title_error": "⚠️ Download finished with errors",
        "tray_close": "Close Aura Video Downloader",
        "tray_reset": "Reset settings",
        "debug_banner": "DEBUG MODE — settings will NOT be saved",
        "no_numbering": "🔢 No file numbering",
        "no_numbering_hint": "(removes 00001. from the beginning of filename)",
        "reverse_playlist": "📊 Oldest to newest",
        "reverse_playlist_hint": "(if off — newest to oldest)",
        "use_archive": "📜 Use archive.txt",
        "use_archive_hint": "(skip already downloaded videos)",
        
        # Input fields
        "url_label_channel": "🔗 Channel URL:",
        "url_label_playlist": "🔗 Playlist URL:",
        "url_label_video": "🔗 Video URL:",
        "url_hint_channel": "Examples: youtube.com/@handle  |  youtube.com/channel/UCxxxxxx",
        "url_hint_playlist": "Examples: youtube.com/playlist?list=PLxxxxxx  |  video link from playlist",
        "url_hint_video": "Examples: youtube.com/watch?v=xxxxxx  |  youtu.be/xxxxxx",
        "outdir_label": "📁 Download folder:",
        "cookies_label": "🍪 cookies.txt file:",
        "cookies_hint": "💡 Use the «Get cookies.txt LOCALLY» extension to export cookies from your browser",
        
        # Buttons
        "browse_folder": "📂 Browse with Explorer...",
        "browse_file": "📄 Browse with Explorer...",
        "start_btn": "▶️  START DOWNLOAD",
        "stop_btn": "⏹️  STOP",
        "clear_log_btn": "🗑️  Clear log",
        "update_ytdlp_btn": "🔄 yt-dlp → master",
        "reset_settings_btn": "🗑️ Reset settings",
        "change_theme_btn": "🎨 Change theme",
        "change_platform_btn": "🔄 Change platform",
        "update_nodejs_btn": "📥 Get Node.js",
        "nodejs_download_title": "Download Node.js",
        "nodejs_download_msg": "This will open the Node.js download page.\n\nDownload the LTS version, install it and restart your computer.",
        "reset_settings_confirm_title": "Confirm Reset",
        "reset_settings_confirm": "Are you sure you want to delete all settings?\n\nThe program will close and on next launch\nwill ask to choose a settings folder again.",
        "reset_settings_done": "Settings deleted. Closing program...",
        
        # Dependencies status
        "deps_frame": "⚙️ Dependencies status",
        "checking": "⏳ Checking...",
        "installed": "✅ Installed",
        "not_found": "❌ NOT FOUND",
        "pywin32_ok": "✅ Installed (full dialogs)",
        "pywin32_no": "⚠️ Not installed (tkinter dialogs)",
        
        # Log
        "log_frame": "📋 Execution log",
        "welcome_line2": "Quality selection • No unnecessary re-encoding",
        
        # Progress counter
        "progress_label": "📊 Progress:",
        "progress_format": "{downloaded} / {total}",
        "progress_idle": "—",
        "progress_scanning": "scanning...",
        
        # Check messages
        "checking_deps": "🔍 Checking dependencies...",
        "ytdlp_found": "  ✅ yt-dlp: ",
        "ytdlp_not_found": "  ❌ yt-dlp: NOT FOUND in PATH!",
        "ytdlp_install_hint": "     Install: pip install yt-dlp",
        "ffmpeg_found": "  ✅ ffmpeg: installed",
        "ffmpeg_not_found": "  ❌ ffmpeg: NOT FOUND in PATH!",
        "aria2c_found": "  ✅ aria2c:     found",
        "aria2c_missing_log": "  ℹ️ aria2c:     not found (optional)",
        "optional": "optional",
        "ffmpeg_install_hint": "     Download from ffmpeg.org and add to PATH",
        "pywin32_found": "  ✅ pywin32: installed (COM API dialogs)",
        "pywin32_not_found": "  ⚠️ pywin32: not installed",
        "pywin32_install_hint": "     For better dialogs: pip install pywin32",
        "nodejs_found": "  ✅ Node.js: ",
        "nodejs_not_found": "  ⚠️ Node.js: NOT FOUND",
        "nodejs_warning": "     ⚠️ Cookies won't work without Node.js!",
        "nodejs_install_hint": "     Download LTS from nodejs.org and restart PC",
        "settings_folder": "  📁 Settings folder: ",
        "ytdlp_config_created": "  📄 yt-dlp config: ",
        
        # yt-dlp update
        "updating_ytdlp": "🔄 Updating yt-dlp to master...",
        "updating_cmd": "   Running: yt-dlp -U --update-to master",
        "update_done": "✅ Update complete!",
        "update_error": "❌ Update error: ",
        
        # Selection dialogs
        "select_folder_title": "Select folder for saving videos",
        "select_file_title": "Select cookies.txt",
        "folder_selected": "📁 Folder selected: ",
        "file_selected": "🍪 File selected: ",
        
        # Validation errors
        "error": "Error",
        "error_input": "Input error",
        "warning": "Warning",
        "error_no_url": "❌ Enter URL!\n\nExamples:\n• youtube.com/@channelname\n• youtube.com/watch?v=xxxxxx",
        "error_invalid_url": "❌ Invalid URL format!\n\nURL must contain a website address.\n\nExamples:\n• https://youtube.com/@channelname\n• youtube.com/watch?v=xxxxxx",
        "warn_not_youtube": "URL doesn't look like a YouTube link.\n\nContinue anyway?",
        "error_no_outdir": "❌ Select download folder!\n\nClick «Browse with Explorer...» button",
        "error_create_folder": "❌ Failed to create folder:\n\n{path}\n\nError: {error}",
        "error_no_cookies": "❌ Select cookies.txt file!\n\nUse browser extension to export cookies.",
        "error_cookies_not_found": "❌ Cookies file not found:\n\n{path}",
        
        # Download
        "folder_created": "📁 Folder created: ",
        "url_videos_added": "ℹ️ Automatically added /videos to URL",
        "starting_download": "▶️  Starting download...",
        "stopping_download": "⏹️  Stopping download...",
        "stop_hint": "   Next run will continue from where it stopped",
        "download_success": "✅ DOWNLOAD COMPLETED SUCCESSFULLY!",
        "download_exit_code": "⚠️ Process finished with code: ",
        "download_exit_hint": "   This may be normal if some videos were already downloaded",
        "download_error": "❌ Execution error: ",
        "download_started": "▶ Download started",
        "download_complete": "Download complete",
        "download_stopped": "Download stopped",
        "restarting_process": "🔄 Restarting process (downloaded {count})...",
        "all_videos_downloaded": "✅ All videos downloaded!",
        
        # Settings summary
        "settings_summary": "📋 SETTINGS SUMMARY",
        "setting_mode": "  📦 Mode:       ",
        "setting_url": "  🔗 URL:        ",
        "setting_folder": "  📁 Folder:     ",
        "setting_cookies": "  🍪 Cookies:    ",
        "setting_archive": "  📜 Archive:    archive.txt",
        "setting_no_archive": "  📜 Archive:    not applicable (single file)",
        "setting_archive_disabled": "  📜 Archive:    disabled by user",
        "setting_quality": "  🎬 Quality:    ",
        "setting_audio_lang": "  🌐 Audio lang: ",
        "setting_format": "  🎬 Format:     ",
        "setting_audio_format": "  🎵 Audio:      ",
        "setting_bitrate": "  📊 Bitrate:    ",
        "setting_order": "  📊 Order:      oldest → newest (playlist_reverse)",
        "setting_order_newest": "  📊 Order:      newest → oldest",
        "setting_order_single": "  📊 Order:      not applicable (single file)",
        "setting_retries": "  🔄 Retries:    infinite (5 sec pause between attempts)",
        "setting_restart": "  🔁 Restart:    after each video",
        "setting_no_restart": "  🔁 Restart:    disabled (single process)",
        "audio_no_compression": " (no compression)",
        
        # Folder structure
        "folder_structure": "  📂 Structure:  ",
        "folder_struct_channel": "Channel folder / number. title [id].ext",
        "folder_struct_playlist": "Channel folder / Playlist folder / number. title [id].ext",
        "folder_struct_video": "title [id].ext (no subfolders)",
        "folder_struct_channel_no_num": "Channel folder / title [id].ext",
        "folder_struct_playlist_no_num": "Channel folder / Playlist folder / title [id].ext",
        
        # Settings save/load
        "settings_saved": "💾 Settings saved",
        "settings_loaded": "📂 Settings loaded",
        
        # === PLATFORM SELECTION ===
        "platform_title": "Choose platform",
        "platform_youtube": "▶️ YouTube",
        "platform_vk": "📹 VK Video",
        
        # === VK VIDEO ===
        "vk_window_title": "📹 VK Video Downloader",
        "vk_main_title": "📹 VK Video Downloader",
        "vk_subtitle": "Download VK Video in selected quality",
        "vk_mode_channel": "👥 Community",
        "vk_mode_channel_desc": "All videos from community/user",
        "vk_url_label_channel": "🔗 Video page URL:",
        "vk_url_hint_channel": "Examples: vk.com/videos-123456  |  vk.com/video/@group  |  vkvideo.ru/@user/videos",
        "vk_url_label_playlist": "🔗 VK Playlist URL:",
        "vk_url_hint_playlist": "Examples: vk.com/video/playlist/-123456_1  |  vkvideo.ru/playlist/-123456_1",
        "vk_url_label_video": "🔗 VK Video URL:",
        "vk_url_hint_video": "Examples: vk.com/video-123456_789  |  vk.com/clip-123456_789  |  vkvideo.ru/video-123456_789",
        "vk_audio_source_channel": "📺 Community",
        "vk_audio_source_channel_desc": "Audio from all community/user videos 🤯",
        "vk_url_label_audio_video": "🔗 VK Video URL:",
        "vk_url_hint_audio_video": "Examples: vk.com/video-123456_789  |  vkvideo.ru/video-123456_789",
        "vk_url_label_audio_playlist": "🔗 VK Playlist URL:",
        "vk_url_hint_audio_playlist": "Examples: vk.com/video/playlist/-123456_1  |  vkvideo.ru/playlist/-123456_1",
        "vk_url_label_audio_channel": "🔗 Video page URL:",
        "vk_url_hint_audio_channel": "Examples: vk.com/videos-123456  |  vkvideo.ru/@user/videos",
        "vk_warn_audio_channel": "⚠️ Audio from all community videos...\n\nThis may take a VERY long time.\nContinue?",
        "vk_warn_not_platform": "URL doesn't look like a VK link.\n\nContinue anyway?",
        "vk_cookies_hint": "💡 Use the «Get cookies.txt LOCALLY» extension to export cookies from VK",
        "vk_nodejs_not_needed": "  ℹ️ Node.js: not required for VK Video",
    }
}


# ══════════════════════════════════════════════════════════════════════════════
#  КОНСТАНТЫ КАЧЕСТВА И ФОРМАТОВ
# ══════════════════════════════════════════════════════════════════════════════

VIDEO_QUALITIES = [
    ("max", "quality_max", None),
    ("8k", "quality_8k", 4320),
    ("4k", "quality_4k", 2160),
    ("1440p", "quality_1440p", 1440),
    ("1080p", "quality_1080p", 1080),
    ("720p", "quality_720p", 720),
    ("480p", "quality_480p", 480),
    ("360p", "quality_360p", 360),
    ("240p", "quality_240p", 240),
    ("144p", "quality_144p", 144),
]

AUDIO_FORMATS = ["wav", "mp3", "ogg"]

AUDIO_BITRATES = [
    ("max", "bitrate_max", 0),
    ("320", "bitrate_320", 320),
    ("256", "bitrate_256", 256),
    ("192", "bitrate_192", 192),
    ("128", "bitrate_128", 128),
    ("96", "bitrate_96", 96),
    ("64", "bitrate_64", 64),
]

# Методы авторизации
AUTH_METHODS = [
    ("none", "auth_none"),
    ("cookies_file", "auth_cookies_file"),
    ("chrome", "auth_chrome"),
    ("firefox", "auth_firefox"),
    ("edge", "auth_edge"),
    ("brave", "auth_brave"),
    ("opera", "auth_opera"),
    ("chromium", "auth_chromium"),
    ("safari", "auth_safari"),
]

# Приватные плейлисты YouTube (требуют авторизации)
YOUTUBE_PRIVATE_PLAYLISTS = [
    ("watch_later", ":ytwatchlater", "🕐 Watch Later"),
    ("liked", "https://www.youtube.com/playlist?list=LL", "❤️ Liked Videos"),
    ("history", "https://www.youtube.com/feed/history", "📜 History"),
]

# SponsorBlock categories: (id, translation_key, default_enabled)
SPONSORBLOCK_CATEGORIES = [
    ("sponsor",        "sb_cat_sponsor",        True),
    ("intro",          "sb_cat_intro",          True),
    ("outro",          "sb_cat_outro",          True),
    ("selfpromo",      "sb_cat_selfpromo",      True),
    ("interaction",    "sb_cat_interaction",    False),
    ("preview",        "sb_cat_preview",        False),
    ("filler",         "sb_cat_filler",         False),
    ("music_offtopic", "sb_cat_music_offtopic", False),
]

# Языки аудиодорожек (код ISO 639-1, ключ локализации)
AUDIO_LANGUAGES = [
    ("any", "lang_any"),
    ("ru", "lang_ru"),
    ("en", "lang_en"),
    ("uk", "lang_uk"),
    ("de", "lang_de"),
    ("fr", "lang_fr"),
    ("es", "lang_es"),
    ("it", "lang_it"),
    ("pt", "lang_pt"),
    ("ja", "lang_ja"),
    ("ko", "lang_ko"),
    ("zh", "lang_zh"),
    ("ar", "lang_ar"),
    ("hi", "lang_hi"),
    ("bn", "lang_bn"),
    ("tr", "lang_tr"),
    ("pl", "lang_pl"),
    ("nl", "lang_nl"),
    ("sv", "lang_sv"),
    ("da", "lang_da"),
    ("no", "lang_no"),
    ("fi", "lang_fi"),
    ("cs", "lang_cs"),
    ("ro", "lang_ro"),
    ("hu", "lang_hu"),
    ("el", "lang_el"),
    ("he", "lang_he"),
    ("th", "lang_th"),
    ("vi", "lang_vi"),
    ("id", "lang_id"),
    ("ms", "lang_ms"),
    ("tl", "lang_tl"),
    ("bg", "lang_bg"),
    ("hr", "lang_hr"),
    ("sk", "lang_sk"),
    ("sr", "lang_sr"),
    ("lt", "lang_lt"),
    ("lv", "lang_lv"),
    ("et", "lang_et"),
    ("ka", "lang_ka"),
    ("hy", "lang_hy"),
    ("az", "lang_az"),
    ("kk", "lang_kk"),
    ("uz", "lang_uz"),
    ("be", "lang_be"),
    ("fa", "lang_fa"),
    ("ta", "lang_ta"),
    ("te", "lang_te"),
    ("mr", "lang_mr"),
    ("ur", "lang_ur"),
    ("sw", "lang_sw"),
    ("af", "lang_af"),
    ("ca", "lang_ca"),
    ("gl", "lang_gl"),
    ("eu", "lang_eu"),
]

# Языки субтитров (код ISO 639-1 → ключ перевода)
# "all" = скачать все доступные
SUBTITLE_LANGUAGES = [
    ("all", "sub_lang_all"),
    ("ru", "sub_lang_ru"),
    ("en", "sub_lang_en"),
    ("uk", "sub_lang_uk"),
    ("de", "sub_lang_de"),
    ("fr", "sub_lang_fr"),
    ("es", "sub_lang_es"),
    ("it", "sub_lang_it"),
    ("pt", "sub_lang_pt"),
    ("ja", "sub_lang_ja"),
    ("ko", "sub_lang_ko"),
    ("zh", "sub_lang_zh"),
    ("ar", "sub_lang_ar"),
    ("hi", "sub_lang_hi"),
    ("tr", "sub_lang_tr"),
    ("pl", "sub_lang_pl"),
    ("nl", "sub_lang_nl"),
    ("sv", "sub_lang_sv"),
    ("cs", "sub_lang_cs"),
    ("ro", "sub_lang_ro"),
    ("hu", "sub_lang_hu"),
    ("el", "sub_lang_el"),
    ("he", "sub_lang_he"),
    ("th", "sub_lang_th"),
    ("vi", "sub_lang_vi"),
    ("id", "sub_lang_id"),
    ("fi", "sub_lang_fi"),
    ("da", "sub_lang_da"),
    ("no", "sub_lang_no"),
    ("bg", "sub_lang_bg"),
    ("hr", "sub_lang_hr"),
    ("sk", "sub_lang_sk"),
    ("sr", "sub_lang_sr"),
    ("lt", "sub_lang_lt"),
    ("lv", "sub_lang_lv"),
    ("et", "sub_lang_et"),
    ("ka", "sub_lang_ka"),
    ("az", "sub_lang_az"),
    ("kk", "sub_lang_kk"),
    ("be", "sub_lang_be"),
    ("fa", "sub_lang_fa"),
]
# ══════════════════════════════════════════════════════════════════════════════
class SettingsManager:
    """Менеджер сохранения и загрузки настроек (per-platform).
    
    Smart migration: when the app adds new settings (or removes old ones),
    the config file on disk is automatically updated on next load.
    User's existing values are NEVER overwritten — only missing keys
    get their defaults, and stale keys are cleaned up.
    """
    
    DEFAULT_SETTINGS = {
        "mode": "video",
        "url": "",
        "outdir": "",
        "cookies": "",
        "proxy": "",
        "video_quality": "max",
        "audio_format": "wav",
        "audio_bitrate": "max",
        "audio_source": "audio_video",
        "audio_language": "any",
        "meta_language": "any",
        "restart_each_video": False,
        "notify_on_finish": True,
        "no_numbering": False,
        "reverse_playlist": True,
        "use_archive": True,
        "download_subtitles": False,
        "subtitle_language": "all",
        "auth_method": "none",
        "use_aria2c": False,
        "aria2c_threads": "8",
        "concurrent_videos": "1",
        "smart_auto_apply": False,
        "smart_auto_preset": "",
        "sb_enabled": False,
        "sb_action": "mark",
        "sb_categories": ["sponsor", "intro", "outro", "selfpromo"],
        "sb_force_keyframes": False,
    }
    
    def __init__(self, platform="youtube"):
        # Per-platform config: config_youtube.json, config_vk.json, etc.
        # Always resolve dynamically — settings dir may change after config location dialog
        self.platform = platform
        self.last_migration = None  # Set by load() if migration occurred
        self._resolve_path()
    
    def _resolve_path(self):
        settings_dir = get_settings_dir()
        settings_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = settings_dir / f"config_{self.platform}.json"
    
    def load(self):
        """Load settings from file with automatic migration.
        
        - Keys present in DEFAULT but missing from file → added with default value
        - Keys present in file but missing from DEFAULT → removed (stale)
        - If any changes → file is re-saved immediately
        - Migration report stored in self.last_migration
        """
        self.last_migration = None
        saved = {}
        is_new_file = True
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                is_new_file = False
        except Exception:
            saved = {}
        
        if is_new_file:
            # First run for this platform — no migration needed
            return self.DEFAULT_SETTINGS.copy()
        
        # Detect differences
        default_keys = set(self.DEFAULT_SETTINGS.keys())
        saved_keys = set(saved.keys())
        
        added_keys = default_keys - saved_keys    # New settings not in file
        removed_keys = saved_keys - default_keys  # Stale settings no longer used
        
        # Build merged result: defaults + saved values for known keys
        settings = self.DEFAULT_SETTINGS.copy()
        for key in default_keys:
            if key in saved:
                settings[key] = saved[key]
        
        # If something changed — save the clean, complete file
        if added_keys or removed_keys:
            self.last_migration = {
                "added": {k: self.DEFAULT_SETTINGS[k] for k in sorted(added_keys)},
                "removed": sorted(removed_keys),
            }
            # Re-save so the file on disk is always complete and clean
            if not is_debug_mode():
                self.save(settings)
        
        return settings
    
    def save(self, settings):
        """Сохранить настройки в файл (atomic write — crash-safe)."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Write to temp file first, then atomically replace.
            # Protects against data loss if app is killed mid-write (e.g., Windows "End Task").
            tmp_path = self.config_path.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            # os.replace is atomic on same filesystem (Windows NTFS + Linux ext4)
            os.replace(str(tmp_path), str(self.config_path))
            return True
        except Exception:
            return False


# Категории платформ
CAT_VIDEO = "video"
CAT_SOCIAL = "social"
CAT_ADULT = "adult"

CATEGORY_INFO = {
    CAT_VIDEO:     {"icon": "🎬", "name_ru": "Видеоплатформы",   "name_en": "Video Platforms"},
    CAT_SOCIAL:    {"icon": "📱", "name_ru": "Социальные сети",  "name_en": "Social Media"},
    CAT_ADULT:     {"icon": "🔞", "name_ru": "Для взрослых",     "name_en": "Adult"},
}

# Порядок категорий в селекторе
CATEGORY_ORDER = [CAT_VIDEO, CAT_SOCIAL, CAT_ADULT]

PLATFORM_CONFIGS = {
    # ── VIDEO ─────────────────────────────────────────────────────────────
    "youtube": {
        "name": "YouTube", "icon": "▶️", "color": "#FF0000", "hover": "#CC0000",
        "category": CAT_VIDEO,
        "domains": ["youtube.com", "youtu.be", "m.youtube.com"],
        "has_channels": True, "has_playlists": True,
        "has_audio_lang": True, "needs_nodejs": True,
        "use_ytdlp_config": True, "normalize_channel_url": True,
        "no_cookies_args": ["--extractor-args", "youtube:player_client=android,web"],
        "channel_label":  {"ru": "📺 Канал",              "en": "📺 Channel"},
        "channel_desc":   {"ru": "Все видео с канала",     "en": "All videos from channel"},
        "url_label_channel": {"ru": "🔗 URL канала:",      "en": "🔗 Channel URL:"},
        "url_examples": {
            "channel":  "youtube.com/@handle  |  youtube.com/channel/UCxxxxxx",
            "playlist": "youtube.com/playlist?list=PLxxxxxx",
            "video":    "youtube.com/watch?v=xxxxxx  |  youtu.be/xxxxxx",
        },
        "warn_mass_audio": {
            "ru": "⚠️ Аудио со всего канала...\n\n🤔 А вы задумывались, что 90% видео на YouTube\nбез картинки — это просто странные звуки\nи фраза «как вы видите на экране»?\n\nНо кто я такой, чтобы вас останавливать.\nПродолжить?",
            "en": "⚠️ Audio from the entire channel...\n\n🤔 Have you considered that 90% of YouTube videos\nwithout the picture are just weird sounds\nand the phrase \"as you can see on the screen\"?\n\nBut who am I to stop you.\nContinue?",
        },
    },
    "vk": {
        "name": "VK Video", "icon": "📹", "color": "#0077FF", "hover": "#0059CC",
        "category": CAT_VIDEO,
        "domains": ["vk.com", "vkvideo.ru", "vk.ru", "m.vk.com"],
        "has_channels": True, "has_playlists": True,
        "channel_label":  {"ru": "👥 Сообщество",                        "en": "👥 Community"},
        "channel_desc":   {"ru": "Все видео сообщества / пользователя",  "en": "All videos from community / user"},
        "url_label_channel": {"ru": "🔗 URL страницы с видео:",          "en": "🔗 Video page URL:"},
        "url_examples": {
            "channel":  "vk.com/videos-123456  |  vkvideo.ru/@user/videos",
            "playlist": "vk.com/video/playlist/-123456_1  |  vkvideo.ru/playlist/-123456_1",
            "video":    "vk.com/video-123456_789  |  vk.com/clip-123456_789",
        },
    },
    "rutube": {
        "name": "Rutube", "icon": "🔴", "color": "#1B1F3B", "hover": "#2B2F5B",
        "category": CAT_VIDEO,
        "domains": ["rutube.ru"],
        "has_channels": True, "has_playlists": True,
        "channel_label": {"ru": "📺 Канал",            "en": "📺 Channel"},
        "channel_desc":  {"ru": "Все видео с канала",   "en": "All videos from channel"},
        "url_examples": {
            "channel":  "rutube.ru/channel/123456/videos/",
            "playlist": "rutube.ru/plst/123456/",
            "video":    "rutube.ru/video/xxxxxxxxxxxxxxxx/",
        },
    },
    "twitch": {
        "name": "Twitch", "icon": "🟣", "color": "#9146FF", "hover": "#7B2FFF",
        "category": CAT_VIDEO,
        "domains": ["twitch.tv"],
        "has_channels": True, "has_playlists": True,
        "channel_label": {"ru": "📺 Канал",             "en": "📺 Channel"},
        "channel_desc":  {"ru": "Все VOD записи канала", "en": "All VODs from channel"},
        "url_examples": {
            "channel":  "twitch.tv/username/videos",
            "playlist": "twitch.tv/collections/xxxxxxxx",
            "video":    "twitch.tv/videos/123456789",
        },
    },
    "dailymotion": {
        "name": "Dailymotion", "icon": "🎬", "color": "#00A2E8", "hover": "#0082C8",
        "category": CAT_VIDEO,
        "domains": ["dailymotion.com", "dai.ly"],
        "has_channels": True, "has_playlists": True,
        "channel_label": {"ru": "📺 Канал",           "en": "📺 Channel"},
        "channel_desc":  {"ru": "Все видео с канала",  "en": "All videos from channel"},
        "url_examples": {
            "channel":  "dailymotion.com/username",
            "playlist": "dailymotion.com/playlist/xxxxxx",
            "video":    "dailymotion.com/video/xxxxxx  |  dai.ly/xxxxxx",
        },
    },
    "vimeo": {
        "name": "Vimeo", "icon": "🎥", "color": "#1AB7EA", "hover": "#0EA0D0",
        "category": CAT_VIDEO,
        "domains": ["vimeo.com"],
        "has_channels": True, "has_playlists": True,
        "channel_label": {"ru": "📺 Пользователь",        "en": "📺 User"},
        "channel_desc":  {"ru": "Все видео пользователя",  "en": "All user videos"},
        "url_examples": {
            "channel":  "vimeo.com/user123456",
            "playlist": "vimeo.com/album/123456  |  vimeo.com/showcase/123456",
            "video":    "vimeo.com/123456789",
        },
    },
    "bilibili": {
        "name": "Bilibili", "icon": "📺", "color": "#00A1D6", "hover": "#0081B6",
        "category": CAT_VIDEO,
        "domains": ["bilibili.com", "b23.tv"],
        "has_channels": True, "has_playlists": True,
        "channel_label": {"ru": "👤 Пользователь",        "en": "👤 User"},
        "channel_desc":  {"ru": "Все видео пользователя",  "en": "All user videos"},
        "url_examples": {
            "channel":  "space.bilibili.com/123456",
            "playlist": "bilibili.com/medialist/detail/ml123456",
            "video":    "bilibili.com/video/BVxxxxxx",
        },
    },
    "ok": {
        "name": "OK.ru", "icon": "🟠", "color": "#EE8208", "hover": "#CC6A00",
        "category": CAT_VIDEO,
        "domains": ["ok.ru"],
        "has_channels": True, "has_playlists": True,
        "channel_label": {"ru": "👤 Профиль",                   "en": "👤 Profile"},
        "channel_desc":  {"ru": "Все видео профиля / группы",   "en": "All videos from profile / group"},
        "url_examples": {
            "channel":  "ok.ru/video/c123456",
            "playlist": "ok.ru/video/c123456/album/123456",
            "video":    "ok.ru/video/123456789",
        },
    },
    "dzen": {
        "name": "Дзен", "icon": "🔍", "color": "#FC3F1D", "hover": "#DC2F0D",
        "category": CAT_VIDEO,
        "domains": ["dzen.ru", "zen.yandex.ru"],
        "has_channels": True, "has_playlists": False,
        "channel_label": {"ru": "📺 Канал",                "en": "📺 Channel"},
        "channel_desc":  {"ru": "Все видео с канала Дзен",  "en": "All Dzen channel videos"},
        "url_examples": {
            "channel": "dzen.ru/id/xxxxxx  |  dzen.ru/username",
            "video":   "dzen.ru/video/watch/xxxxxx",
        },
    },
    # ── SOCIAL ────────────────────────────────────────────────────────────
    "tiktok": {
        "name": "TikTok", "icon": "🎵", "color": "#111111", "hover": "#333333",
        "category": CAT_SOCIAL,
        "domains": ["tiktok.com"],
        "has_channels": True, "has_playlists": False,
        "channel_label": {"ru": "👤 Пользователь",        "en": "👤 User"},
        "channel_desc":  {"ru": "Все видео пользователя",  "en": "All user videos"},
        "url_examples": {
            "channel": "tiktok.com/@username",
            "video":   "tiktok.com/@user/video/123456789",
        },
    },
    "instagram": {
        "name": "Instagram", "icon": "📸", "color": "#E1306C", "hover": "#C1104C",
        "category": CAT_SOCIAL,
        "domains": ["instagram.com"],
        "has_channels": True, "has_playlists": False,
        "needs_cookies_recommended": True,
        "channel_label": {"ru": "👤 Профиль",           "en": "👤 Profile"},
        "channel_desc":  {"ru": "Все видео профиля",     "en": "All profile videos"},
        "url_examples": {
            "channel": "instagram.com/username/reels/",
            "video":   "instagram.com/reel/xxxxxx  |  instagram.com/p/xxxxxx",
        },
    },
    "twitter": {
        "name": "Twitter / X", "icon": "🐦", "color": "#1DA1F2", "hover": "#0D91E2",
        "category": CAT_SOCIAL,
        "domains": ["twitter.com", "x.com"],
        "has_channels": False, "has_playlists": False,
        "url_examples": {
            "video": "x.com/user/status/123456  |  twitter.com/user/status/123456",
        },
    },
    "facebook": {
        "name": "Facebook", "icon": "📘", "color": "#1877F2", "hover": "#0857D2",
        "category": CAT_SOCIAL,
        "domains": ["facebook.com", "fb.watch", "fb.com"],
        "has_channels": True, "has_playlists": True,
        "needs_cookies_recommended": True,
        "channel_label": {"ru": "📄 Страница",               "en": "📄 Page"},
        "channel_desc":  {"ru": "Все видео со страницы",      "en": "All videos from page"},
        "url_examples": {
            "channel":  "facebook.com/pagename/videos/",
            "playlist": "facebook.com/watch/123456789/",
            "video":    "facebook.com/watch?v=123456  |  fb.watch/xxxxx",
        },
    },
    "reddit": {
        "name": "Reddit", "icon": "🤖", "color": "#FF4500", "hover": "#DD3500",
        "category": CAT_SOCIAL,
        "domains": ["reddit.com", "old.reddit.com"],
        "has_channels": True, "has_playlists": False,
        "channel_label": {"ru": "📋 Subreddit",              "en": "📋 Subreddit"},
        "channel_desc":  {"ru": "Все видео из сабреддита",    "en": "All videos from subreddit"},
        "url_examples": {
            "channel": "reddit.com/r/subreddit/",
            "video":   "reddit.com/r/sub/comments/xxxxx/title/",
        },
    },
    # ── ADULT ─────────────────────────────────────────────────────────────
    "pornhub": {
        "name": "Pornhub", "icon": "🔞", "color": "#FFA31A", "hover": "#DD8300",
        "category": CAT_ADULT,
        "domains": ["pornhub.com"],
        "has_channels": True, "has_playlists": True,
        "channel_label": {"ru": "👤 Модель / Канал",        "en": "👤 Model / Channel"},
        "channel_desc":  {"ru": "Все видео канала / модели", "en": "All channel / model videos"},
        "url_examples": {
            "channel":  "pornhub.com/model/name  |  pornhub.com/channels/name",
            "playlist": "pornhub.com/playlist/123456",
            "video":    "pornhub.com/view_video.php?viewkey=xxxxxx",
        },
    },
    "xvideos": {
        "name": "XVideos", "icon": "🔞", "color": "#C80000", "hover": "#A00000",
        "category": CAT_ADULT,
        "domains": ["xvideos.com"],
        "has_channels": True, "has_playlists": False,
        "channel_label": {"ru": "👤 Профиль",            "en": "👤 Profile"},
        "channel_desc":  {"ru": "Все видео профиля",      "en": "All profile videos"},
        "url_examples": {
            "channel": "xvideos.com/profiles/username",
            "video":   "xvideos.com/video.xxxxx/title",
        },
    },
    "xhamster": {
        "name": "xHamster", "icon": "🔞", "color": "#F05922", "hover": "#D04912",
        "category": CAT_ADULT,
        "domains": ["xhamster.com", "xhamster2.com", "xhamster3.com", "xhamster.desi"],
        "has_channels": True, "has_playlists": True,
        "channel_label": {"ru": "👤 Пользователь",        "en": "👤 User"},
        "channel_desc":  {"ru": "Все видео пользователя",  "en": "All user videos"},
        "url_examples": {
            "channel":  "xhamster.com/users/username",
            "playlist": "xhamster.com/my/favorites/videos/123456",
            "video":    "xhamster.com/videos/title-123456",
        },
    },
    # ── UNIVERSAL removed — each platform has its own template ──────────
}

# Archive suffix per platform
for _pid, _pc in PLATFORM_CONFIGS.items():
    if "archive_suffix" not in _pc:
        _pc["archive_suffix"] = _pid  # archive_youtube.txt, archive_vk.txt, etc.

def get_platform_name(platform_id, lang="en"):
    """Получить отображаемое имя платформы с учётом языка."""
    pc = PLATFORM_CONFIGS[platform_id]
    if lang == "ru" and "name_ru" in pc:
        return pc["name_ru"]
    if lang == "en" and "name_en" in pc:
        return pc["name_en"]
    return pc["name"]

def get_all_domains():
    """Собрать все известные домены из всех платформ."""
    domains = set()
    for pc in PLATFORM_CONFIGS.values():
        domains.update(pc.get("domains", []))
    return domains

THEMES = {
    "dark": {
        "name_ru": "🌙 Тёмная", "name_en": "🌙 Dark",
        "btn_color": "#1a1a2e", "btn_hover": "#252540",
        "selector_bg": "#0f0f1a", "selector_fg": "#e0e0ee",
        "colors": {
            'bg_deep':     '#0f0f1a',
            'bg_main':     '#161625',
            'bg_card':     '#1c1c30',
            'bg_entry':    '#12121f',
            'bg_button':   '#252540',
            'bg_hover':    '#2f2f50',
            'accent':      '#6c5ce7',
            'accent2':     '#00cec9',
            'green':       '#00b894',
            'green_hover': '#00a381',
            'red':         '#d63031',
            'red_hover':   '#c02021',
            'text':        '#e0e0ee',
            'text_dim':    '#8888aa',
            'text_hint':   '#5c5c7a',
            'border':      '#2a2a44',
            'select':      '#3d3d5c',
            'log_bg':      '#0a0a14',
            'log_fg':      '#c8c8e0',
        },
    },
    "gray": {
        "name_ru": "🌫️ Серая", "name_en": "🌫️ Gray",
        "btn_color": "#4a4a5a", "btn_hover": "#5a5a6a",
        "selector_bg": "#2d2d3d", "selector_fg": "#f0f0f8",
        "colors": {
            'bg_deep':     '#2d2d3d',
            'bg_main':     '#3a3a4a',
            'bg_card':     '#424252',
            'bg_entry':    '#333343',
            'bg_button':   '#505060',
            'bg_hover':    '#606070',
            'accent':      '#7c6cf7',
            'accent2':     '#20ded9',
            'green':       '#10c8a4',
            'green_hover': '#00b894',
            'red':         '#e64040',
            'red_hover':   '#d63031',
            'text':        '#f0f0f8',
            'text_dim':    '#a0a0b8',
            'text_hint':   '#808098',
            'border':      '#555568',
            'select':      '#5858a0',
            'log_bg':      '#262636',
            'log_fg':      '#d8d8ec',
        },
    },
    "light": {
        "name_ru": "☀️ Светлая (4K VD+)", "name_en": "☀️ Light (4K VD+)",
        "btn_color": "#e8e8e8", "btn_hover": "#d0d0d0",
        "selector_bg": "#f0f0f0", "selector_fg": "#333333",
        "colors": {
            'bg_deep':     '#f0f0f0',
            'bg_main':     '#fafafa',
            'bg_card':     '#ffffff',
            'bg_entry':    '#ffffff',
            'bg_button':   '#e8e8e8',
            'bg_hover':    '#d5d5d5',
            'accent':      '#4CAF50',
            'accent2':     '#43A047',
            'green':       '#4CAF50',
            'green_hover': '#43A047',
            'red':         '#e53935',
            'red_hover':   '#c62828',
            'text':        '#333333',
            'text_dim':    '#757575',
            'text_hint':   '#9e9e9e',
            'border':      '#e0e0e0',
            'select':      '#c8e6c9',
            'log_bg':      '#fafafa',
            'log_fg':      '#333333',
        },
    },
}

DEFAULT_THEME = "light"

def get_theme_config():
    """Загрузить сохранённую тему из общего конфига."""
    try:
        general_config = get_settings_dir() / "general.json"
        if general_config.exists():
            data = json.loads(general_config.read_text(encoding='utf-8'))
            theme = data.get("theme", DEFAULT_THEME)
            if theme in THEMES:
                return theme
    except Exception:
        pass
    return DEFAULT_THEME

def save_theme_config(theme_id):
    """Сохранить выбранную тему в общий конфиг."""
    if is_debug_mode():
        return
    try:
        general_config = get_settings_dir() / "general.json"
        general_config.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if general_config.exists():
            try:
                data = json.loads(general_config.read_text(encoding='utf-8'))
            except Exception:
                pass
        data["theme"] = theme_id
        general_config.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  QSS СТИЛИ (как CSS)
# ══════════════════════════════════════════════════════════════════════════════

def build_qss(C):
    """Генерирует Qt Style Sheet из словаря цветов темы."""
    return f"""
    /* ── Global ─────────────────────────────────────────── */
    QMainWindow, QDialog {{
        background-color: {C['bg_main']};
        color: {C['text']};
    }}
    QWidget {{
        color: {C['text']};
        font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
        font-size: 10pt;
    }}

    /* ── Toolbar ────────────────────────────────────────── */
    QToolBar {{
        background-color: {C['bg_card']};
        border-bottom: 1px solid {C['border']};
        padding: 6px 8px;
        spacing: 6px;
    }}
    QToolBar QLabel {{
        font-weight: bold;
        font-size: 11pt;
        color: {C['accent']};
    }}
    QToolBar QLineEdit {{
        background: {C['bg_entry']};
        border: 1px solid {C['border']};
        border-radius: 4px;
        padding: 6px 10px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 10pt;
        color: {C['text']};
    }}
    QToolBar QLineEdit:focus {{
        border-color: {C['accent']};
    }}

    /* ── Buttons ────────────────────────────────────────── */
    QPushButton {{
        background-color: {C['bg_button']};
        color: {C['text']};
        border: 1px solid {C['border']};
        border-radius: 4px;
        padding: 7px 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {C['bg_hover']};
    }}
    QPushButton:pressed {{
        background-color: {C['accent']};
        color: white;
    }}
    QPushButton:disabled {{
        background-color: {C['bg_deep']};
        color: {C['text_hint']};
        border-color: {C['bg_deep']};
    }}
    QPushButton#startBtn {{
        background-color: {C['green']};
        color: white;
        font-weight: bold;
        font-size: 11pt;
        padding: 8px 22px;
        border: none;
        border-radius: 5px;
    }}
    QPushButton#startBtn:hover {{
        background-color: {C['green_hover']};
    }}
    QPushButton#startBtn:disabled {{
        background-color: {C['text_hint']};
    }}
    QPushButton#stopBtn {{
        background-color: {C['red']};
        color: white;
        font-weight: bold;
        padding: 8px 16px;
        border: none;
        border-radius: 5px;
    }}
    QPushButton#stopBtn:hover {{
        background-color: {C['red_hover']};
    }}
    QPushButton#stopBtn:disabled {{
        background-color: {C['text_hint']};
    }}
    QPushButton#accentBtn {{
        background-color: {C['accent']};
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: bold;
    }}
    QPushButton#accentBtn:hover {{
        background-color: {C['green']};
    }}

    /* ── Inputs ─────────────────────────────────────────── */
    QLineEdit {{
        background: {C['bg_entry']};
        border: 1px solid {C['border']};
        border-radius: 4px;
        padding: 6px 8px;
        color: {C['text']};
    }}
    QLineEdit:focus {{
        border-color: {C['accent']};
    }}
    QComboBox {{
        background: {C['bg_entry']};
        border: 1px solid {C['border']};
        border-radius: 4px;
        padding: 5px 28px 5px 8px;
        color: {C['text']};
        min-height: 20px;
    }}
    QComboBox:focus {{
        border-color: {C['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
        subcontrol-position: center right;
        subcontrol-origin: padding;
    }}
    QComboBox::down-arrow {{
        width: 10px;
        height: 10px;
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {C['text_dim']};
    }}
    QComboBox QAbstractItemView {{
        background: {C['bg_card']};
        color: {C['text']};
        selection-background-color: {C['accent']};
        selection-color: white;
        border: 1px solid {C['border']};
    }}

    /* ── Radio / Check ──────────────────────────────────── */
    QRadioButton, QCheckBox {{
        spacing: 6px;
        color: {C['text']};
        padding: 2px 0;
    }}
    QRadioButton::indicator, QCheckBox::indicator {{
        width: 16px;
        height: 16px;
    }}
    QRadioButton:hover, QCheckBox:hover {{
        color: {C['accent']};
    }}

    /* ── GroupBox ────────────────────────────────────────── */
    QGroupBox {{
        background: {C['bg_card']};
        border: 1px solid {C['border']};
        border-radius: 6px;
        margin-top: 14px;
        padding: 20px 12px 10px 12px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {C['accent']};
    }}

    /* ── Log ────────────────────────────────────────────── */
    QPlainTextEdit {{
        background: {C['log_bg']};
        color: {C['log_fg']};
        border: none;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 10pt;
        selection-background-color: {C['select']};
    }}

    /* ── Tree (History) ──────────────────────────────────── */
    QTreeWidget {{
        background: {C['bg_entry']};
        alternate-background-color: {C['bg_main']};
        border: 1px solid {C['border']};
        border-radius: 4px;
        color: {C['text']};
    }}
    QTreeWidget::item {{
        padding: 4px 8px;
    }}
    QTreeWidget::item:selected {{
        background: {C['accent']};
        color: white;
    }}
    QHeaderView::section {{
        background: {C['bg_button']};
        color: {C['accent']};
        padding: 6px 8px;
        border: none;
        border-right: 1px solid {C['border']};
        font-weight: bold;
    }}

    /* ── Progress Bar ───────────────────────────────────── */
    QProgressBar {{
        background: {C['bg_deep']};
        border: none;
        border-radius: 3px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {C['green']}, stop:1 {C['accent']});
        border-radius: 3px;
    }}

    /* ── Status Bar ─────────────────────────────────────── */
    QStatusBar {{
        background: {C['bg_card']};
        border-top: 1px solid {C['border']};
        color: {C['text_dim']};
        font-size: 9pt;
    }}

    /* ── Splitter Handle ────────────────────────────────── */
    QSplitter::handle:vertical {{
        background: {C['border']};
        height: 3px;
        margin: 2px 40px;
        border-radius: 1px;
    }}
    QSplitter::handle:vertical:hover {{
        background: {C['accent']};
    }}

    /* ── ScrollBars ─────────────────────────────────────── */
    QScrollBar:vertical {{
        background: {C['bg_deep']};
        width: 10px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {C['bg_button']};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: {C['bg_deep']};
        height: 10px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {C['bg_button']};
        border-radius: 5px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {C['accent']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ── Tooltips ───────────────────────────────────────── */
    QToolTip {{
        background: {C['bg_card']};
        color: {C['text']};
        border: 1px solid {C['accent']};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 9pt;
    }}

    /* ── Labels ─────────────────────────────────────────── */
    QLabel#sectionLabel {{
        font-size: 11pt;
        font-weight: bold;
        color: {C['accent']};
    }}
    QLabel#hintLabel {{
        color: {C['text_hint']};
        font-size: 9pt;
    }}
    QLabel#statusLabel {{
        color: {C['accent']};
        font-family: 'Consolas', monospace;
        font-weight: bold;
    }}

    /* ── Frame ──────────────────────────────────────────── */
    QFrame#separator {{
        background: {C['border']};
        max-height: 1px;
    }}
    """



# ══════════════════════════════════════════════════════════════════════════════
#  ДИАЛОГИ (Qt)
# ══════════════════════════════════════════════════════════════════════════════

class LanguageSelector(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✦ AURA ✦")
        self.setFixedSize(340, 160)
        self.result = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        title = QLabel("✦ AURA VIDEO DOWNLOADER ✦")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50;")
        layout.addWidget(title)
        
        sub = QLabel("Выберите язык / Choose language")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(sub)
        
        btn_layout = QHBoxLayout()
        for lang_id, label in [("ru", "🇷🇺 Русский"), ("en", "🇬🇧 English")]:
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, l=lang_id: self._select(l))
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
    
    def _select(self, lang):
        self.result = lang
        self.accept()
    
    def run(self):
        self.exec()
        return self.result


class ThemeSelector(QDialog):
    def __init__(self, lang="en", parent=None):
        super().__init__(parent)
        self.setWindowTitle("✦ AURA ✦ — " + ("Тема" if lang == "ru" else "Theme"))
        self.setFixedSize(440, 180)
        self.result = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        title = QLabel("✦ AURA VIDEO DOWNLOADER ✦")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50;")
        layout.addWidget(title)
        
        sub = QLabel("Выберите тему / Choose theme" if lang == "ru" else "Choose theme / Выберите тему")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(sub)
        
        btn_layout = QHBoxLayout()
        
        for theme_id, theme_data in THEMES.items():
            name = theme_data[f"name_{lang}"]
            btn = QPushButton(name)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
            c = theme_data["colors"]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c['bg_button']}; color: {c['text']};
                    border: 2px solid {c['accent']}; border-radius: 6px;
                    font-weight: bold; padding: 8px 16px; font-size: 10pt;
                }}
                QPushButton:hover {{ background: {c['accent']}; color: white; }}
            """)
            btn.clicked.connect(lambda checked, t=theme_id: self._select(t))
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
    
    def _select(self, theme_id):
        save_theme_config(theme_id)
        self.result = theme_id
        self.accept()
    
    def run(self):
        self.exec()
        return self.result


class PlatformSelector(QDialog):
    def __init__(self, lang="en", theme_id="light", parent=None):
        super().__init__(parent)
        self.lang = lang
        C = THEMES.get(theme_id, THEMES["light"])["colors"]
        
        self.setWindowTitle("✦ AURA ✦ — " + ("Платформа" if lang == "ru" else "Platform"))
        self.setMinimumSize(520, 480)
        self.result = None
        
        self.setStyleSheet(f"""
            QDialog {{ background: {C['bg_main']}; }}
            QWidget {{ background: {C['bg_main']}; }}
            QPushButton {{
                background: {C['bg_card']}; color: {C['text']};
                border: 1px solid {C['border']}; border-radius: 6px;
                padding: 10px; font-size: 11pt; text-align: left;
            }}
            QPushButton:hover {{
                background: {C['accent']}; color: white; border-color: {C['accent']};
            }}
            QLabel {{ color: {C['text']}; }}
            QScrollArea {{ border: none; }}
            QScrollBar:vertical {{
                background: {C['bg_deep']}; width: 8px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C['bg_button']}; border-radius: 4px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {C['accent']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        title = QLabel("✦ AURA VIDEO DOWNLOADER ✦")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {C['accent']};")
        layout.addWidget(title)
        
        # Scroll area for platforms
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_widget = QWidget()
        grid = QGridLayout(scroll_widget)
        grid.setSpacing(8)
        
        cat_names = {
            "video": "🎬 " + ("Видеохостинги" if lang == "ru" else "Video Platforms"),
            "social": "📱 " + ("Соцсети" if lang == "ru" else "Social Media"),
            "adult": "🔞 " + ("Взрослый контент" if lang == "ru" else "Adult Content"),
        }
        
        row = 0
        current_cat = None
        col = 0
        
        for pid, pc in PLATFORM_CONFIGS.items():
            cat = pc.get("category", "video")
            if cat != current_cat:
                if current_cat is not None:
                    row += 1
                    col = 0
                current_cat = cat
                cat_label = QLabel(cat_names.get(cat, cat))
                cat_label.setStyleSheet(f"font-weight: bold; font-size: 11pt; color: {C['accent']};")
                grid.addWidget(cat_label, row, 0, 1, 3)
                row += 1
                col = 0
            
            display_name = get_platform_name(pid, lang)
            btn = QPushButton(f"  {display_name}")
            btn.setFixedHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, p=pid: self._select(p))
            grid.addWidget(btn, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
    
    def _select(self, platform_id):
        self.result = platform_id
        self.accept()
    
    def run(self):
        self.exec()
        return self.result


# ══════════════════════════════════════════════════════════════════════════════
#  DOWNLOAD WORKER (QThread)
# ══════════════════════════════════════════════════════════════════════════════

class DownloadWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(str)  # raw line for parsing
    finished_signal = Signal(int)  # return code
    
    def __init__(self, cmd, stop_event):
        super().__init__()
        self.cmd = cmd
        self.stop_event = stop_event
        self.process = None
    
    def run(self):
        try:
            # text=True + bufsize=1 gives REAL-TIME line-by-line output.
            # encoding='utf-8' + errors='surrogateescape' preserves raw bytes
            # when yt-dlp.EXE outputs in system codepage (cp1251) instead of UTF-8.
            # We detect and fix these lines in _fix_encoding() below.
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='surrogateescape',
                creationflags=SUBPROCESS_FLAGS,
                env=_get_subprocess_env(),
                bufsize=1,
            )
            
            for line in self.process.stdout:
                if self.stop_event.is_set():
                    self.process.terminate()
                    break
                line = _fix_encoding(line.rstrip('\n\r'))
                if line:
                    self.log_signal.emit(line)
                    self.progress_signal.emit(line)
            
            self.process.wait()
            rc = self.process.returncode or 0
            self.finished_signal.emit(rc)
            
        except FileNotFoundError:
            self.log_signal.emit(f"❌ yt-dlp not found! Install: pip install yt-dlp")
            self.log_signal.emit(f"   Command: {self.cmd[0]}")
            self.finished_signal.emit(1)
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {e}")
            self.finished_signal.emit(1)
    
    def stop(self):
        self.stop_event.set()
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass


class DepsWorker(QThread):
    """Background dependency checker — finds binaries in system PATH."""
    results_ready = Signal(dict)
    
    def __init__(self, platform_config):
        super().__init__()
        self.pc = platform_config
    
    def run(self):
        results = {}
        
        # yt-dlp: prefer system PATH binary
        ytdlp_path = shutil.which("yt-dlp")
        if ytdlp_path:
            try:
                r = subprocess.run([ytdlp_path, "--version"], capture_output=True, text=True,
                                    creationflags=SUBPROCESS_FLAGS, timeout=SUBPROCESS_TIMEOUT)
                results['ytdlp'] = ('ok', r.stdout.strip(), ytdlp_path)
            except Exception as e:
                results['ytdlp'] = ('error', str(e), ytdlp_path)
        else:
            results['ytdlp'] = ('missing', '', '')
        
        # ffmpeg: prefer system PATH binary
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            results['ffmpeg'] = ('ok', '', ffmpeg_path)
        else:
            results['ffmpeg'] = ('missing', '', '')
        
        # Node.js
        if not self.pc.get("needs_nodejs", False):
            results['nodejs'] = ('notneeded', '', '')
        else:
            node_path = shutil.which("node")
            if node_path:
                try:
                    r = subprocess.run([node_path, "--version"], capture_output=True, text=True,
                                        creationflags=SUBPROCESS_FLAGS, timeout=SUBPROCESS_TIMEOUT)
                    results['nodejs'] = ('ok', r.stdout.strip(), node_path)
                except Exception as e:
                    results['nodejs'] = ('error', str(e), node_path)
            else:
                results['nodejs'] = ('missing', '', '')
        
        # aria2c (optional download accelerator)
        aria2c_path = shutil.which("aria2c")
        if aria2c_path:
            try:
                r = subprocess.run([aria2c_path, "--version"], capture_output=True, text=True,
                                    creationflags=SUBPROCESS_FLAGS, timeout=SUBPROCESS_TIMEOUT)
                ver = r.stdout.split('\n')[0].strip() if r.stdout else ""
                results['aria2c'] = ('ok', ver, aria2c_path)
            except Exception as e:
                results['aria2c'] = ('error', str(e), aria2c_path)
        else:
            results['aria2c'] = ('missing', '', '')
        
        self.results_ready.emit(results)




# ══════════════════════════════════════════════════════════════════════════════
#  ГЛАВНОЕ ОКНО
# ══════════════════════════════════════════════════════════════════════════════

class AuraDownloader(QMainWindow):
    MODE_CHANNEL = "channel"
    MODE_PLAYLIST = "playlist"
    MODE_VIDEO = "video"
    MODE_AUDIO = "audio"
    AUDIO_SOURCE_VIDEO = "audio_video"
    AUDIO_SOURCE_PLAYLIST = "audio_playlist"
    AUDIO_SOURCE_CHANNEL = "audio_channel"
    
    # Cross-thread signals
    _sig_log = Signal(str)
    _sig_progress = Signal(str)
    _sig_finished = Signal(int)
    
    def __init__(self, lang="en", platform="youtube", theme_id="light"):
        super().__init__()
        self.lang = lang
        self.platform = platform
        self.theme_id = theme_id
        self.COLORS = THEMES.get(theme_id, THEMES["light"])["colors"]
        self.t = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
        self.pc = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["youtube"])
        self.settings_manager = SettingsManager(platform=platform)
        
        # State
        self.stop_event = threading.Event()
        self.worker = None
        self._download_generation = 0      # Incremented each start — prevents stale callbacks
        self._restart_process = None        # Active subprocess in restart mode (for cleanup)
        self._restart_thread = None         # Active restart thread reference
        self.total_videos = 0
        self.downloaded_videos = 0
        self._last_destination = ""
        self._pending_history = False
        self.current_speed = ""
        self.current_eta = ""
        self.download_history = []
        
        # Settings vars (plain Python, not tkinter StringVar)
        self._mode = self.MODE_VIDEO
        self._quality = "max"
        self._audio_format = "wav"
        self._audio_bitrate = "max"
        self._audio_source = self.AUDIO_SOURCE_VIDEO
        self._audio_language = "any"
        self._meta_language = "any"
        self._reverse_playlist = True
        self._use_archive = True
        self._no_numbering = False
        self._restart_each = False
        self._notify_on_finish = True
        self._download_subs = False
        self._sub_language = "all"
        self._auth_method = "none"
        self._use_aria2c = False
        self._aria2c_threads = "16"
        self._concurrent_videos = "1"
        self._smart_auto = False
        self._sb_enabled = False
        self._sb_action = "mark"
        self._sb_categories = ["sponsor", "intro", "outro", "selfpromo"]
        self._sb_force_keyframes = False
        
        platform_name = get_platform_name(platform, lang)
        self.setWindowTitle(f"✦ AURA VIDEO DOWNLOADER ✦ — {platform_name}")
        self.setMinimumSize(900, 650)
        self.resize(980, 720)
        
        self.setStyleSheet(build_qss(self.COLORS))
        
        # Connect cross-thread signals
        self._sig_log.connect(self.log)
        self._sig_progress.connect(self._handle_progress_line)
        self._sig_finished.connect(self._download_finished)
        
        self._create_ui()
        self._load_settings()
        self._show_welcome()
        
        # System tray icon — persistent while app is running
        self._setup_tray_icon()
        
        # Check dependencies in background
        QTimer.singleShot(300, self._check_dependencies_bg)
    
    # ══════════════════════════════════════════════════════════════════════════
    #  UI CREATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def _create_ui(self):
        C = self.COLORS
        t = self.t
        
        # ─── TOOLBAR ─────────────────────────────────────────────────────
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)
        
        platform_name = get_platform_name(self.platform, self.lang)
        lbl = QLabel(f"  ✦ {platform_name}  ")
        toolbar.addWidget(lbl)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self._pc_url_hint(self.MODE_CHANNEL))
        self.url_input.setMinimumWidth(300)
        self.url_input.returnPressed.connect(self.start_download)
        toolbar.addWidget(self.url_input)
        
        toolbar.addSeparator()
        
        self.start_btn = QPushButton(f"▶ {t['start_btn']}")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setToolTip("Ctrl+Enter")
        self.start_btn.setShortcut("Ctrl+Return")
        self.start_btn.clicked.connect(self.start_download)
        toolbar.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton(f"⏹ {t['stop_btn']}")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setToolTip("Ctrl+Q")
        self.stop_btn.setShortcut("Ctrl+Q")
        self.stop_btn.clicked.connect(self.stop_download)
        toolbar.addWidget(self.stop_btn)
        
        clear_btn = QPushButton("🗑")
        clear_btn.setFixedWidth(36)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setToolTip(t.get("clear_log_btn", "Clear log") + "  (Ctrl+L)")
        clear_btn.setShortcut("Ctrl+L")
        clear_btn.clicked.connect(self.clear_log)
        toolbar.addWidget(clear_btn)
        
        # ─── MAIN AREA: Splitter (settings + log) ────────────────────────
        splitter = QSplitter(Qt.Vertical)
        self.setCentralWidget(splitter)
        
        # Top: scrollable settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 12, 16, 12)
        
        self._build_all_sections(layout, t)
        
        scroll.setWidget(content)
        splitter.addWidget(scroll)
        
        # Bottom: log with title
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)
        
        log_header = QLabel(f"  {t.get('log_title', '📋 Log')}")
        log_header.setFixedHeight(24)
        log_header.setStyleSheet(f"""
            background: {C['bg_card']};
            color: {C['accent']};
            font-weight: bold;
            font-size: 9pt;
            padding-left: 8px;
            border-top: 2px solid {C['accent']};
        """)
        log_layout.addWidget(log_header)
        
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.log_text.setMaximumBlockCount(10000)  # Prevent unbounded memory growth
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_container)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 200])
        
        # ─── STATUS BAR ──────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(12, 4, 12, 4)
        status_layout.setSpacing(2)
        status_layout.addWidget(self.progress_bar)
        
        info_layout = QHBoxLayout()
        self.progress_label = QLabel(t["progress_idle"])
        self.progress_label.setObjectName("statusLabel")
        self.speed_label = QLabel(t["speed_idle"])
        self.speed_label.setObjectName("statusLabel")
        
        info_layout.addWidget(QLabel(t["progress_label"]))
        info_layout.addWidget(self.progress_label)
        info_layout.addStretch()
        
        version_lbl = QLabel(f"v{APP_VERSION}")
        version_lbl.setStyleSheet(f"color: {C['text_hint']}; font-size: 8pt;")
        info_layout.addWidget(version_lbl)
        info_layout.addStretch()
        
        info_layout.addWidget(QLabel(t["speed_label"]))
        info_layout.addWidget(self.speed_label)
        status_layout.addLayout(info_layout)
        
        self.statusBar().addPermanentWidget(status_widget, 1)
    
    def _build_all_sections(self, layout, t):
        """Build all settings in a single scrollable page."""
        C = self.COLORS
        
        def _btn(text, slot, accent=False, tip=None):
            """Helper: create a button with hand cursor."""
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            if accent:
                b.setObjectName("accentBtn")
            if tip:
                b.setToolTip(tip)
            return b
        
        def _sep():
            """Thin horizontal separator."""
            s = QFrame()
            s.setFrameShape(QFrame.HLine)
            s.setObjectName("separator")
            return s
        
        # ═══ 1. MODE ══════════════════════════════════════════════════════
        mode_group = QGroupBox(t["mode_label"])
        mode_layout = QHBoxLayout(mode_group)
        self.mode_buttons = QButtonGroup(self)
        
        modes = [
            (self.MODE_CHANNEL, "mode_channel"),
            (self.MODE_PLAYLIST, "mode_playlist"),
            (self.MODE_VIDEO, "mode_video"),
            (self.MODE_AUDIO, "mode_audio"),
        ]
        
        # Filter modes by platform capabilities
        available_modes = []
        for mval, mkey in modes:
            if mval == self.MODE_CHANNEL and not self.pc.get("has_channels", True):
                continue
            if mval == self.MODE_PLAYLIST and not self.pc.get("has_playlists", True):
                continue
            available_modes.append((mval, mkey))
        
        # Validate saved mode against available options
        available_vals = [m[0] for m in available_modes]
        effective_mode = self._mode if self._mode in available_vals else self.MODE_VIDEO
        
        for mval, mkey in available_modes:
            rb = QRadioButton(t[mkey])
            rb.setProperty("mode_value", mval)
            self.mode_buttons.addButton(rb)
            mode_layout.addWidget(rb)
            if mval == effective_mode:
                rb.setChecked(True)
        
        self.mode_buttons.buttonClicked.connect(self._on_mode_change)
        mode_layout.addStretch()
        layout.addWidget(mode_group)
        
        # ═══ 2. URL EXAMPLES (visible hint) ═══════════════════════════════
        self.url_examples_label = QLabel()
        self.url_examples_label.setObjectName("hintLabel")
        self.url_examples_label.setWordWrap(True)
        self._update_url_examples()
        layout.addWidget(self.url_examples_label)
        
        # ═══ 3. QUALITY (grid layout — shown in video modes) ═════════════
        self.quality_group = QGroupBox(t["video_quality_label"])
        q_grid = QGridLayout(self.quality_group)
        q_grid.setSpacing(6)
        self.quality_buttons = QButtonGroup(self)
        
        num_cols = 5
        for idx, (q_val, q_key, _) in enumerate(VIDEO_QUALITIES):
            rb = QRadioButton(t[q_key])
            rb.setProperty("q_value", q_val)
            self.quality_buttons.addButton(rb)
            q_grid.addWidget(rb, idx // num_cols, idx % num_cols)
            if q_val == self._quality:
                rb.setChecked(True)
        
        layout.addWidget(self.quality_group)
        
        # ═══ 3b. AUDIO SETTINGS (shown only in audio mode) ═══════════════
        self.audio_group = QGroupBox(t.get("audio_format_label", "🎵 Audio"))
        a_layout = QVBoxLayout(self.audio_group)
        
        # Format row (horizontal)
        fmt_row = QHBoxLayout()
        self.format_buttons = QButtonGroup(self)
        for fmt in AUDIO_FORMATS:
            rb = QRadioButton(fmt.upper())
            rb.setProperty("fmt_value", fmt)
            self.format_buttons.addButton(rb)
            fmt_row.addWidget(rb)
            if fmt == self._audio_format:
                rb.setChecked(True)
        self.format_buttons.buttonClicked.connect(self._on_format_change)
        fmt_row.addStretch()
        a_layout.addLayout(fmt_row)
        
        # Bitrate row (label + buttons in one container)
        self.bitrate_label = QLabel(t["audio_bitrate_label"])
        a_layout.addWidget(self.bitrate_label)
        self.bitrate_buttons = QButtonGroup(self)
        self.bitrate_widget = QWidget()
        br_layout = QHBoxLayout(self.bitrate_widget)
        br_layout.setContentsMargins(0, 0, 0, 0)
        br_layout.setSpacing(8)
        for b_val, b_key, _ in AUDIO_BITRATES:
            rb = QRadioButton(t[b_key])
            rb.setProperty("br_value", b_val)
            self.bitrate_buttons.addButton(rb)
            br_layout.addWidget(rb)
            if b_val == self._audio_bitrate:
                rb.setChecked(True)
        br_layout.addStretch()
        a_layout.addWidget(self.bitrate_widget)
        
        # Audio language
        if self.pc.get("has_audio_lang", False):
            self.audio_lang_combo = QComboBox()
            self.audio_lang_combo.setFixedWidth(180)
            for code, lkey in AUDIO_LANGUAGES:
                self.audio_lang_combo.addItem(t.get(lkey, lkey), code)
            self.audio_lang_combo.currentIndexChanged.connect(self._on_audio_lang_change)
        else:
            self.audio_lang_combo = None
        
        # Audio source (horizontal row)
        a_layout.addWidget(_sep())
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel(t.get("audio_source_label", "📥 Source:")))
        self.source_buttons = QButtonGroup(self)
        
        # Only show audio sources that the platform actually supports
        audio_sources = [(self.AUDIO_SOURCE_VIDEO, "audio_source_video")]
        if self.pc.get("has_playlists", False):
            audio_sources.append((self.AUDIO_SOURCE_PLAYLIST, "audio_source_playlist"))
        if self.pc.get("has_channels", False):
            audio_sources.append((self.AUDIO_SOURCE_CHANNEL, "audio_source_channel"))
        
        # Validate saved source against available options
        available_vals = [s[0] for s in audio_sources]
        effective_source = self._audio_source if self._audio_source in available_vals else self.AUDIO_SOURCE_VIDEO
        
        for src_val, src_key in audio_sources:
            rb = QRadioButton(t.get(src_key, src_key))
            rb.setProperty("src_value", src_val)
            self.source_buttons.addButton(rb)
            src_row.addWidget(rb)
            if src_val == effective_source:
                rb.setChecked(True)
        self.source_buttons.buttonClicked.connect(self._on_source_change)
        src_row.addStretch()
        a_layout.addLayout(src_row)
        
        layout.addWidget(self.audio_group)
        
        # ═══ 3c. AUDIO LANGUAGE (visible in ALL modes when platform supports it) ═══
        if self.audio_lang_combo:
            self.audio_lang_row = QWidget()
            alr_layout = QHBoxLayout(self.audio_lang_row)
            alr_layout.setContentsMargins(4, 2, 4, 2)
            alr_layout.addWidget(QLabel(t["audio_language_label"]))
            alr_layout.addWidget(self.audio_lang_combo)
            audio_lang_hint = QLabel(t.get("audio_language_hint", ""))
            audio_lang_hint.setObjectName("hintLabel")
            alr_layout.addWidget(audio_lang_hint)
            alr_layout.addStretch()
            layout.addWidget(self.audio_lang_row)
        
        # ═══ 3d. METADATA LANGUAGE (YouTube only, visible in ALL modes) ═══
        if self.platform == "youtube":
            self.meta_lang_combo = QComboBox()
            self.meta_lang_combo.setFixedWidth(180)
            for code, lkey in AUDIO_LANGUAGES:
                self.meta_lang_combo.addItem(t.get(lkey, lkey), code)
            self.meta_lang_row = QWidget()
            mlr_layout = QHBoxLayout(self.meta_lang_row)
            mlr_layout.setContentsMargins(4, 2, 4, 2)
            mlr_layout.addWidget(QLabel(t.get("meta_language_label", "🏷️ Title language (YouTube):")))
            mlr_layout.addWidget(self.meta_lang_combo)
            meta_lang_hint = QLabel(t.get("meta_language_hint", ""))
            meta_lang_hint.setObjectName("hintLabel")
            mlr_layout.addWidget(meta_lang_hint)
            mlr_layout.addStretch()
            layout.addWidget(self.meta_lang_row)
        else:
            self.meta_lang_combo = None
        
        # ═══ 4. OPTIONS ══════════════════════════════════════════════════
        opts = QGroupBox(t.get("options_label", "⚙️ Options"))
        opts_layout = QVBoxLayout(opts)
        
        # Row 1: main checkboxes
        row1 = QHBoxLayout()
        self.chk_reverse = QCheckBox(t["reverse_playlist"])
        self.chk_reverse.setChecked(self._reverse_playlist)
        self.chk_reverse.setToolTip(t.get("reverse_playlist_hint", ""))
        row1.addWidget(self.chk_reverse)
        
        self.chk_archive = QCheckBox(t["use_archive"])
        self.chk_archive.setChecked(self._use_archive)
        self.chk_archive.setToolTip(t.get("use_archive_hint", ""))
        row1.addWidget(self.chk_archive)
        
        self.chk_nonumber = QCheckBox(t["no_numbering"])
        self.chk_nonumber.setChecked(self._no_numbering)
        self.chk_nonumber.setToolTip(t.get("no_numbering_hint", ""))
        row1.addWidget(self.chk_nonumber)
        
        self.chk_restart = QCheckBox(t["restart_each_video"])
        self.chk_restart.setChecked(self._restart_each)
        self.chk_restart.setToolTip(t.get("restart_each_video_hint", ""))
        row1.addWidget(self.chk_restart)
        
        self.chk_notify = QCheckBox(t["notify_on_finish"])
        self.chk_notify.setChecked(self._notify_on_finish)
        self.chk_notify.setToolTip(t.get("notify_on_finish_hint", ""))
        row1.addWidget(self.chk_notify)
        row1.addStretch()
        opts_layout.addLayout(row1)
        
        # Row 2: Subtitles + aria2c
        row2 = QHBoxLayout()
        self.chk_subs = QCheckBox(t["subtitles"])
        self.chk_subs.setChecked(self._download_subs)
        self.chk_subs.stateChanged.connect(self._on_subs_toggle)
        row2.addWidget(self.chk_subs)
        
        self.sub_lang_combo = QComboBox()
        for code, lkey in SUBTITLE_LANGUAGES:
            self.sub_lang_combo.addItem(t.get(lkey, lkey), code)
        self.sub_lang_combo.setVisible(self._download_subs)
        self.sub_lang_combo.setFixedWidth(180)
        row2.addWidget(self.sub_lang_combo)
        
        row2.addSpacing(20)
        self.chk_aria2c = QCheckBox(t.get("aria2c_label", "🚀 aria2c"))
        self.chk_aria2c.setChecked(self._use_aria2c)
        self.chk_aria2c.setToolTip(t.get("aria2c_hint", ""))
        self.chk_aria2c.stateChanged.connect(self._on_aria2c_toggle)
        row2.addWidget(self.chk_aria2c)
        
        self.aria2c_threads_lbl = QLabel(t.get("aria2c_threads_label", "Threads:"))
        self.aria2c_threads_lbl.setVisible(self._use_aria2c)
        row2.addWidget(self.aria2c_threads_lbl)
        
        self.aria2c_threads_combo = QComboBox()
        self.aria2c_threads_combo.addItems(["4", "8", "16"])
        self.aria2c_threads_combo.setCurrentText(min(self._aria2c_threads, "16") if self._aria2c_threads in ["4","8","16"] else "16")
        self.aria2c_threads_combo.setFixedWidth(80)
        self.aria2c_threads_combo.setVisible(self._use_aria2c)
        row2.addWidget(self.aria2c_threads_combo)
        
        row2.addSpacing(20)
        self.concurrent_lbl = QLabel(t.get("concurrent_videos_label", "📥 Parallel:"))
        row2.addWidget(self.concurrent_lbl)
        
        self.concurrent_combo = QComboBox()
        self.concurrent_combo.addItems(["1", "2", "3", "4", "5"])
        self.concurrent_combo.setCurrentText(self._concurrent_videos)
        self.concurrent_combo.setFixedWidth(80)
        self.concurrent_combo.setToolTip(t.get("concurrent_videos_hint", ""))
        row2.addWidget(self.concurrent_combo)
        
        row2.addStretch()
        opts_layout.addLayout(row2)
        
        # Row 3: Auth
        row3 = QHBoxLayout()
        row3.addWidget(QLabel(t["auth_label"]))
        self.auth_combo = QComboBox()
        for am_id, am_key in AUTH_METHODS:
            self.auth_combo.addItem(t.get(am_key, am_key), am_id)
        self.auth_combo.setFixedWidth(200)
        row3.addWidget(self.auth_combo)
        
        if self.platform == "youtube":
            for pid, purl, pname in YOUTUBE_PRIVATE_PLAYLISTS:
                btn = QPushButton(pname)
                btn.setFixedHeight(28)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked, u=purl: self._set_private_url(u))
                row3.addWidget(btn)
        
        row3.addStretch()
        opts_layout.addLayout(row3)
        
        # Row 4: SponsorBlock (YouTube only)
        if self.platform == "youtube":
            row4 = QHBoxLayout()
            self.chk_sb = QCheckBox(t["sb_label"])
            self.chk_sb.setChecked(self._sb_enabled)
            self.chk_sb.setToolTip(t.get("sb_hint", ""))
            self.chk_sb.stateChanged.connect(self._on_sb_toggle)
            row4.addWidget(self.chk_sb)
            
            self.sb_action_lbl = QLabel(t.get("sb_action_label", "Action:"))
            self.sb_action_lbl.setVisible(self._sb_enabled)
            row4.addWidget(self.sb_action_lbl)
            
            self.sb_action_combo = QComboBox()
            self.sb_action_combo.addItem(t["sb_action_mark"], "mark")
            self.sb_action_combo.addItem(t["sb_action_remove"], "remove")
            self.sb_action_combo.setFixedWidth(230)
            self.sb_action_combo.setVisible(self._sb_enabled)
            self.sb_action_combo.currentIndexChanged.connect(self._on_sb_action_change)
            if self._sb_action == "remove":
                self.sb_action_combo.setCurrentIndex(1)
            row4.addWidget(self.sb_action_combo)
            
            row4.addSpacing(10)
            self.chk_sb_keyframes = QCheckBox(t.get("sb_force_keyframes", "🔑 Precise cuts"))
            self.chk_sb_keyframes.setChecked(self._sb_force_keyframes)
            self.chk_sb_keyframes.setToolTip(t.get("sb_force_keyframes_hint", ""))
            self.chk_sb_keyframes.setVisible(self._sb_enabled and self._sb_action == "remove")
            row4.addWidget(self.chk_sb_keyframes)
            
            row4.addStretch()
            opts_layout.addLayout(row4)
            
            # Row 4b: SponsorBlock category checkboxes
            self.sb_cats_row = QWidget()
            sb_cats_layout = QHBoxLayout(self.sb_cats_row)
            sb_cats_layout.setContentsMargins(24, 0, 4, 2)
            self.sb_cat_checks = {}
            for cat_id, cat_key, _ in SPONSORBLOCK_CATEGORIES:
                chk = QCheckBox(t.get(cat_key, cat_id))
                chk.setChecked(cat_id in self._sb_categories)
                self.sb_cat_checks[cat_id] = chk
                sb_cats_layout.addWidget(chk)
            sb_cats_layout.addStretch()
            self.sb_cats_row.setVisible(self._sb_enabled)
            opts_layout.addWidget(self.sb_cats_row)
        else:
            self.chk_sb = None
        
        layout.addWidget(opts)
        
        # ═══ 5. PATHS ════════════════════════════════════════════════════
        paths = QGroupBox(t.get("paths_label", "📂 Paths & Files"))
        pl = QVBoxLayout(paths)
        
        # Output dir (no duplicate label — GroupBox title is enough)
        folder_row = QHBoxLayout()
        self.outdir_input = QLineEdit(str(self._get_default_outdir()))
        self.outdir_input.setPlaceholderText(t["outdir_label"])
        folder_row.addWidget(self.outdir_input)
        btn_browse = QPushButton("📁")
        btn_browse.setFixedSize(36, 32)
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setToolTip(t.get("browse_folder_tip", "Select folder"))
        btn_browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(btn_browse)
        btn_open = QPushButton("📂")
        btn_open.setFixedSize(36, 32)
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setToolTip(t.get("open_folder_btn", "Open folder"))
        btn_open.clicked.connect(self._open_download_folder)
        folder_row.addWidget(btn_open)
        pl.addLayout(folder_row)
        
        # Cookies
        cookies_row = QHBoxLayout()
        cookies_row.addWidget(QLabel(t["cookies_label"]))
        self.cookies_input = QLineEdit()
        self.cookies_input.setPlaceholderText("cookies.txt")
        cookies_row.addWidget(self.cookies_input)
        btn_cookies = QPushButton("📁")
        btn_cookies.setFixedSize(36, 32)
        btn_cookies.setCursor(Qt.PointingHandCursor)
        btn_cookies.setToolTip(t.get("browse_file_tip", "Select file"))
        btn_cookies.clicked.connect(self._browse_cookies)
        cookies_row.addWidget(btn_cookies)
        pl.addLayout(cookies_row)
        
        # Cookies hint (compact)
        hint = QLabel(t["cookies_hint"])
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        pl.addWidget(hint)
        
        # Proxy
        proxy_row = QHBoxLayout()
        proxy_row.addWidget(QLabel(t["proxy_label"]))
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText(t.get("proxy_hint", "socks5://127.0.0.1:1080"))
        proxy_row.addWidget(self.proxy_input)
        pl.addLayout(proxy_row)
        layout.addWidget(paths)
        
        # ═══ 6. SMART MODE + IMPORT/EXPORT ═══════════════════════════════
        smart = QGroupBox(t["smart_mode_label"])
        smart.setToolTip(t.get("smart_mode_hint", ""))
        sl = QVBoxLayout(smart)
        
        # Presets row
        preset_row = QHBoxLayout()
        self.smart_combo = QComboBox()
        self.smart_combo.setMinimumWidth(180)
        self._refresh_smart_presets()
        if self.smart_combo.count() == 0:
            self.smart_combo.setPlaceholderText(t.get("smart_select_preset", "—"))
        preset_row.addWidget(self.smart_combo)
        
        for text, slot in [(t["smart_save_btn"], self._smart_save),
                           (t["smart_load_btn"], self._smart_load),
                           (t["smart_delete_btn"], self._smart_delete)]:
            preset_row.addWidget(_btn(text, slot))
        
        self.chk_smart_auto = QCheckBox(t["smart_apply_on_start"])
        self.chk_smart_auto.setChecked(self._smart_auto)
        preset_row.addWidget(self.chk_smart_auto)
        preset_row.addStretch()
        sl.addLayout(preset_row)
        
        # Import/Export row (logically belongs with Smart Mode)
        ie_row = QHBoxLayout()
        ie_row.addWidget(_btn(t["import_btn"], self._import_links))
        ie_row.addWidget(_btn(t["export_btn"], self._export_history))
        ie_row.addStretch()
        sl.addLayout(ie_row)
        layout.addWidget(smart)
        
        # ═══ 7. DEPENDENCIES ══════════════════════════════════════════════
        deps = QGroupBox(t["deps_frame"])
        deps_layout = QHBoxLayout(deps)
        
        # Status grid
        status_grid = QGridLayout()
        for i, (name, attr) in enumerate([
            ("yt-dlp", "ytdlp_status_label"),
            ("ffmpeg", "ffmpeg_status_label"),
            ("aria2c", "aria2c_status_label"),
            ("Node.js", "nodejs_status_label"),
        ]):
            status_grid.addWidget(QLabel(f"<b>{name}:</b>"), i, 0)
            lbl = QLabel(t["checking"])
            setattr(self, attr, lbl)
            status_grid.addWidget(lbl, i, 1)
        deps_layout.addLayout(status_grid)
        deps_layout.addStretch()
        
        # Dep action buttons only
        deps_layout.addWidget(_btn(t["update_ytdlp_btn"], self._update_ytdlp))
        deps_layout.addWidget(_btn(t.get("update_nodejs_btn", "Node.js"), self._download_nodejs))
        layout.addWidget(deps)
        
        # ═══ 8. APP SETTINGS (separate from dependencies) ════════════════
        app_settings = QGroupBox(t.get("settings_label", "🔧 App Settings"))
        as_layout = QHBoxLayout(app_settings)
        as_layout.addWidget(_btn(t.get("change_platform_btn", "🔄 Platform"), self._change_platform))
        as_layout.addWidget(_btn(t.get("change_theme_btn", "🎨 Theme"), self._change_theme))
        as_layout.addWidget(_btn(t.get("reset_settings_btn", "🗑️ Reset"), self._reset_settings))
        as_layout.addStretch()
        layout.addWidget(app_settings)
        
        # ═══ 9. HISTORY ══════════════════════════════════════════════════
        hist = QGroupBox(t.get("history_label", "📜 Download History"))
        hist_layout = QVBoxLayout(hist)
        
        # Filter toolbar
        filter_row = QHBoxLayout()
        self.dm_filter_group = QButtonGroup(self)
        for fval, ftext in [("all", t["dm_tab_all"]), ("video", t["dm_tab_video"]),
                            ("audio", t["dm_tab_audio"]), ("playlist", t["dm_tab_playlist"])]:
            rb = QRadioButton(ftext)
            rb.setProperty("filter", fval)
            self.dm_filter_group.addButton(rb)
            filter_row.addWidget(rb)
            if fval == "all":
                rb.setChecked(True)
        self.dm_filter_group.buttonClicked.connect(self._dm_apply_filter)
        
        filter_row.addSpacing(12)
        self.dm_search = QLineEdit()
        self.dm_search.setPlaceholderText("🔍 ...")
        self.dm_search.setFixedWidth(180)
        self.dm_search.textChanged.connect(self._dm_apply_filter)
        filter_row.addWidget(self.dm_search)
        
        for text, slot in [(t["dm_sort_date"], lambda: self._dm_sort("date")),
                           (t["dm_sort_name"], lambda: self._dm_sort("name"))]:
            filter_row.addWidget(_btn(text, slot))
        
        filter_row.addStretch()
        filter_row.addWidget(_btn(t["dm_clear_completed"], self._dm_clear_completed))
        hist_layout.addLayout(filter_row)
        
        # Tree (with constrained height)
        self.dm_tree = QTreeWidget()
        self.dm_tree.setAlternatingRowColors(True)
        self.dm_tree.setRootIsDecorated(False)
        self.dm_tree.setMinimumHeight(80)
        self.dm_tree.setMaximumHeight(200)
        self.dm_tree.setHeaderLabels([t["dm_col_status"], t["dm_col_name"],
                                      t["dm_col_size"], t["dm_col_date"]])
        header = self.dm_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hist_layout.addWidget(self.dm_tree)
        layout.addWidget(hist)
        
        self._load_download_history()
        
        # Initial visibility
        self._update_mode_visibility()

    # ══════════════════════════════════════════════════════════════════════════
    #  PLATFORM HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _pc_get(self, key, default=None):
        return self.pc.get(key, default)
    
    def _pc_label(self, key, default=""):
        val = self.pc.get(key, {})
        if isinstance(val, dict):
            return val.get(self.lang, val.get("en", default))
        return val if val else default
    
    def _pc_channel_label(self):
        return self._pc_label("channel_label", "📺 Channel" if self.lang == "en" else "📺 Канал")
    
    def _pc_channel_desc(self):
        return self._pc_label("channel_desc", "All videos" if self.lang == "en" else "Все видео")
    
    def _pc_url_label(self, mode):
        if mode == self.MODE_CHANNEL:
            custom = self._pc_label("url_label_channel")
            if custom:
                return custom
            ch_name = self._pc_channel_label()
            name_only = ch_name.split(" ", 1)[-1] if " " in ch_name else ch_name
            return f"🔗 URL ({name_only}):" if self.lang == "ru" else f"🔗 {name_only} URL:"
        elif mode == self.MODE_PLAYLIST:
            return self.t.get("url_label_playlist", "🔗 Playlist URL:")
        return self.t.get("url_label_video", "🔗 Video URL:")
    
    def _pc_url_hint(self, mode):
        examples = self.pc.get("url_examples", {})
        key_map = {self.MODE_CHANNEL: "channel", self.MODE_PLAYLIST: "playlist", self.MODE_VIDEO: "video"}
        example = examples.get(key_map.get(mode, "video"), "")
        return example if example else ""
    
    def _pc_audio_url_label(self, source):
        mapping = {self.AUDIO_SOURCE_VIDEO: self.MODE_VIDEO,
                   self.AUDIO_SOURCE_PLAYLIST: self.MODE_PLAYLIST,
                   self.AUDIO_SOURCE_CHANNEL: self.MODE_CHANNEL}
        return self._pc_url_label(mapping.get(source, self.MODE_VIDEO))
    
    def _pc_audio_url_hint(self, source):
        mapping = {self.AUDIO_SOURCE_VIDEO: self.MODE_VIDEO,
                   self.AUDIO_SOURCE_PLAYLIST: self.MODE_PLAYLIST,
                   self.AUDIO_SOURCE_CHANNEL: self.MODE_CHANNEL}
        return self._pc_url_hint(mapping.get(source, self.MODE_VIDEO))
    
    # ══════════════════════════════════════════════════════════════════════════
    #  GETTERS (read from widgets)
    # ══════════════════════════════════════════════════════════════════════════
    
    def _get_mode(self):
        btn = self.mode_buttons.checkedButton()
        return btn.property("mode_value") if btn else self.MODE_VIDEO
    
    def _get_quality(self):
        btn = self.quality_buttons.checkedButton()
        return btn.property("q_value") if btn else "max"
    
    def _get_audio_format(self):
        btn = self.format_buttons.checkedButton()
        return btn.property("fmt_value") if btn else "wav"
    
    def _get_audio_bitrate(self):
        btn = self.bitrate_buttons.checkedButton()
        return btn.property("br_value") if btn else "max"
    
    def _get_audio_source(self):
        btn = self.source_buttons.checkedButton()
        return btn.property("src_value") if btn else self.AUDIO_SOURCE_VIDEO
    
    def _get_audio_language(self):
        if self.audio_lang_combo:
            return self.audio_lang_combo.currentData() or "any"
        return "any"
    
    def _get_meta_language(self):
        if self.meta_lang_combo:
            return self.meta_lang_combo.currentData() or "any"
        return "any"
    
    def _get_sub_language(self):
        return self.sub_lang_combo.currentData() or "all"
    
    def _get_auth_method(self):
        return self.auth_combo.currentData() or "none"
    
    def _get_sb_categories(self):
        """Get list of selected SponsorBlock category IDs."""
        if not self.chk_sb or not hasattr(self, 'sb_cat_checks'):
            return []
        return [cat_id for cat_id, chk in self.sb_cat_checks.items() if chk.isChecked()]
    
    def _get_sb_action(self):
        """Get current SponsorBlock action: 'mark' or 'remove'."""
        if not self.chk_sb:
            return "mark"
        return self.sb_action_combo.currentData() or "mark"
    
    # ══════════════════════════════════════════════════════════════════════════
    #  SETTERS (write to widgets)
    # ══════════════════════════════════════════════════════════════════════════
    
    def _set_radio_group(self, group, prop_name, value):
        for btn in group.buttons():
            if btn.property(prop_name) == value:
                btn.setChecked(True)
                return
    
    def _set_combo_by_data(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
    
    # ══════════════════════════════════════════════════════════════════════════
    #  SETTINGS LOAD / SAVE
    # ══════════════════════════════════════════════════════════════════════════
    
    def _load_settings(self):
        try:
            self._load_settings_impl()
        except Exception as e:
            import traceback
            self.log(f"\n⚠️ ERROR in _load_settings:\n{traceback.format_exc()}")
    
    def _load_settings_impl(self):
        settings = self.settings_manager.load()
        
        # Log migration report (new/removed settings detected)
        migration = self.settings_manager.last_migration
        if migration:
            self.log(self.t.get("settings_migrated", "  🔄 Settings migrated:"))
            for key, value in migration["added"].items():
                display_val = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
                self.log(self.t.get("settings_key_added", "     + {key} = {value}").format(
                    key=key, value=display_val))
            for key in migration["removed"]:
                self.log(self.t.get("settings_key_removed", "     − {key}").format(key=key))
            self.log(self.t.get("settings_file_saved", "     💾 {path}").format(
                path=self.settings_manager.config_path))
            self.log("")
        
        valid_modes = [self.MODE_CHANNEL, self.MODE_PLAYLIST, self.MODE_VIDEO, self.MODE_AUDIO]
        if settings.get("mode") in valid_modes:
            self._set_radio_group(self.mode_buttons, "mode_value", settings["mode"])
        
        if settings.get("url"):
            self.url_input.setText(settings["url"])
        if settings.get("outdir"):
            self.outdir_input.setText(settings["outdir"])
        if settings.get("cookies"):
            self.cookies_input.setText(settings["cookies"])
        if settings.get("proxy"):
            self.proxy_input.setText(settings["proxy"])
        
        valid_qualities = [q[0] for q in VIDEO_QUALITIES]
        if settings.get("video_quality") in valid_qualities:
            self._set_radio_group(self.quality_buttons, "q_value", settings["video_quality"])
        
        if settings.get("audio_format") in AUDIO_FORMATS:
            self._set_radio_group(self.format_buttons, "fmt_value", settings["audio_format"])
        
        valid_bitrates = [b[0] for b in AUDIO_BITRATES]
        if settings.get("audio_bitrate") in valid_bitrates:
            self._set_radio_group(self.bitrate_buttons, "br_value", settings["audio_bitrate"])
        
        valid_sources = [self.AUDIO_SOURCE_VIDEO, self.AUDIO_SOURCE_PLAYLIST, self.AUDIO_SOURCE_CHANNEL]
        if settings.get("audio_source") in valid_sources:
            self._set_radio_group(self.source_buttons, "src_value", settings["audio_source"])
        
        valid_langs = [lang[0] for lang in AUDIO_LANGUAGES]
        if settings.get("audio_language") in valid_langs and self.audio_lang_combo:
            self._set_combo_by_data(self.audio_lang_combo, settings["audio_language"])
        if settings.get("meta_language") in valid_langs and self.meta_lang_combo:
            self._set_combo_by_data(self.meta_lang_combo, settings["meta_language"])
        
        self.chk_restart.setChecked(settings.get("restart_each_video", False))
        self.chk_notify.setChecked(settings.get("notify_on_finish", True))
        self.chk_nonumber.setChecked(settings.get("no_numbering", False))
        self.chk_reverse.setChecked(settings.get("reverse_playlist", True))
        self.chk_archive.setChecked(settings.get("use_archive", True))
        self.chk_subs.setChecked(settings.get("download_subtitles", False))
        
        valid_sub = [c for c, _ in SUBTITLE_LANGUAGES]
        if settings.get("subtitle_language") in valid_sub:
            self._set_combo_by_data(self.sub_lang_combo, settings["subtitle_language"])
        self.sub_lang_combo.setVisible(settings.get("download_subtitles", False))
        
        auth = settings.get("auth_method", "none")
        valid_auths = [am[0] for am in AUTH_METHODS]
        if auth in valid_auths:
            self._set_combo_by_data(self.auth_combo, auth)
        
        self.chk_aria2c.setChecked(settings.get("use_aria2c", False))
        threads = settings.get("aria2c_threads", "16")
        if threads in ["4", "8", "16"]:
            self.aria2c_threads_combo.setCurrentText(threads)
        conc = settings.get("concurrent_videos", "1")
        if conc in ["1", "2", "3", "4", "5"]:
            self.concurrent_combo.setCurrentText(conc)
        
        self.chk_smart_auto.setChecked(settings.get("smart_auto_apply", False))
        if settings.get("smart_auto_apply", False):
            auto_preset = settings.get("smart_auto_preset", "")
            if auto_preset:
                presets = self._load_all_presets()
                if auto_preset in presets:
                    self._apply_preset_data(presets[auto_preset])
                    self.smart_combo.setCurrentText(auto_preset)
        
        # SponsorBlock (YouTube only)
        if self.chk_sb:
            self.chk_sb.setChecked(settings.get("sb_enabled", False))
            action = settings.get("sb_action", "mark")
            if action in ("mark", "remove"):
                self._set_combo_by_data(self.sb_action_combo, action)
            cats = settings.get("sb_categories", ["sponsor", "intro", "outro", "selfpromo"])
            valid_cats = [c for c, _, _ in SPONSORBLOCK_CATEGORIES]
            for cat_id, chk in self.sb_cat_checks.items():
                chk.setChecked(cat_id in cats and cat_id in valid_cats)
            self.chk_sb_keyframes.setChecked(settings.get("sb_force_keyframes", False))
            self._on_sb_toggle()
        
        self._update_mode_visibility()
        self._on_format_change()
        self._update_url_examples()
    
    def _save_settings(self):
        if is_debug_mode():
            return
        try:
            self._save_settings_impl()
        except Exception as e:
            import traceback
            self.log(f"\n⚠️ ERROR in _save_settings:\n{traceback.format_exc()}")
    
    def _save_settings_impl(self):
        settings = {
            "mode": self._get_mode(),
            "url": self.url_input.text().strip(),
            "outdir": self.outdir_input.text().strip(),
            "cookies": self.cookies_input.text().strip(),
            "proxy": self.proxy_input.text().strip(),
            "video_quality": self._get_quality(),
            "audio_format": self._get_audio_format(),
            "audio_bitrate": self._get_audio_bitrate(),
            "audio_source": self._get_audio_source(),
            "audio_language": self._get_audio_language(),
            "meta_language": self._get_meta_language(),
            "restart_each_video": self.chk_restart.isChecked(),
            "notify_on_finish": self.chk_notify.isChecked(),
            "no_numbering": self.chk_nonumber.isChecked(),
            "reverse_playlist": self.chk_reverse.isChecked(),
            "use_archive": self.chk_archive.isChecked(),
            "download_subtitles": self.chk_subs.isChecked(),
            "subtitle_language": self._get_sub_language(),
            "auth_method": self._get_auth_method(),
            "use_aria2c": self.chk_aria2c.isChecked(),
            "aria2c_threads": self.aria2c_threads_combo.currentText(),
            "concurrent_videos": self.concurrent_combo.currentText(),
            "smart_auto_apply": self.chk_smart_auto.isChecked(),
            "smart_auto_preset": self.smart_combo.currentText(),
            "sb_enabled": self.chk_sb.isChecked() if self.chk_sb else False,
            "sb_action": self._get_sb_action(),
            "sb_categories": self._get_sb_categories(),
            "sb_force_keyframes": self.chk_sb_keyframes.isChecked() if self.chk_sb else False,
        }
        self.settings_manager.save(settings)
    
    # ══════════════════════════════════════════════════════════════════════════
    #  SYSTEM TRAY
    # ══════════════════════════════════════════════════════════════════════════
    
    def _setup_tray_icon(self):
        """Create persistent system tray icon with context menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        app_icon = QApplication.instance().windowIcon()
        if app_icon.isNull():
            pxm = QPixmap(64, 64)
            pxm.fill(QColor("#4CAF50"))
            painter = QPainter(pxm)
            painter.setPen(QColor("white"))
            f = painter.font()
            f.setPixelSize(48)
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(pxm.rect(), Qt.AlignCenter, "A")
            painter.end()
            app_icon = QIcon(pxm)
        
        self._tray_icon = QSystemTrayIcon(app_icon, self)
        
        # Context menu (right-click)
        tray_menu = QMenu(self)
        act_reset = tray_menu.addAction(self.t.get("tray_reset", "Reset settings"))
        act_reset.triggered.connect(self._reset_settings)
        tray_menu.addSeparator()
        act_close = tray_menu.addAction(self.t.get("tray_close", "Close Aura Video Downloader"))
        act_close.triggered.connect(self.close)
        self._tray_icon.setContextMenu(tray_menu)
        
        # Left-click — show and focus window
        self._tray_icon.activated.connect(self._on_tray_activated)
        
        self._tray_icon.setToolTip("Aura Video Downloader")
        self._tray_icon.show()
    
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # Left-click
            self.showNormal()
            self.activateWindow()
            self.raise_()
    
    def closeEvent(self, event):
        # Don't re-save settings if we're in the middle of a full reset
        if not getattr(self, '_resetting', False):
            self._save_settings()
            self._save_download_history()
        # Hide tray icon before exit
        if hasattr(self, '_tray_icon'):
            self._tray_icon.hide()
        self.stop_event.set()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        for w in getattr(self, '_parallel_workers', []):
            w.stop()
            w.wait(3000)
            if w.isRunning():
                try:
                    w.terminate()
                except Exception:
                    pass
        # Kill restart mode subprocess (prevents orphan yt-dlp processes)
        if self._restart_process:
            try:
                self._restart_process.terminate()
                self._restart_process.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
            except Exception:
                try:
                    self._restart_process.kill()
                except Exception:
                    pass
        event.accept()
    
    # ══════════════════════════════════════════════════════════════════════════
    #  UI EVENT HANDLERS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _on_mode_change(self, btn=None):
        try:
            mode = self._get_mode()
            self._update_mode_visibility()
            self._update_url_examples()
            if mode == self.MODE_AUDIO:
                src = self._get_audio_source()
                hint = self._pc_audio_url_hint(src)
            else:
                hint = self._pc_url_hint(mode)
            self.url_input.setPlaceholderText(hint)
        except Exception as e:
            import traceback
            self.log(f"\n⚠️ ERROR in _on_mode_change:\n{traceback.format_exc()}")
    
    def _update_url_examples(self):
        """Update visible URL examples label based on current mode."""
        mode = self._get_mode()
        examples = self.pc.get("url_examples", {})
        if mode == self.MODE_AUDIO:
            src = self._get_audio_source()
            if src == self.AUDIO_SOURCE_PLAYLIST:
                ex = examples.get("playlist", "")
            elif src == self.AUDIO_SOURCE_CHANNEL:
                ex = examples.get("channel", "")
            else:
                ex = examples.get("video", "")
        else:
            ex = examples.get(mode, "")
        
        if ex:
            title = self.t.get("url_examples_title", "💡 URL examples:")
            self.url_examples_label.setText(f"{title}  {ex}")
            self.url_examples_label.setVisible(True)
        else:
            self.url_examples_label.setVisible(False)
    
    def _update_mode_visibility(self):
        mode = self._get_mode()
        is_audio = (mode == self.MODE_AUDIO)
        self.quality_group.setVisible(not is_audio)
        self.audio_group.setVisible(is_audio)
    
    def _on_source_change(self, btn=None):
        src = self._get_audio_source()
        self.url_input.setPlaceholderText(self._pc_audio_url_hint(src))
        self._update_url_examples()
    
    def _on_format_change(self, btn=None):
        fmt = self._get_audio_format()
        is_lossless = fmt in ("wav", "flac")
        self.bitrate_widget.setVisible(not is_lossless)
        self.bitrate_label.setVisible(not is_lossless)
    
    def _on_subs_toggle(self, state):
        self.sub_lang_combo.setVisible(self.chk_subs.isChecked())
    
    def _on_aria2c_toggle(self, state):
        visible = self.chk_aria2c.isChecked()
        self.aria2c_threads_combo.setVisible(visible)
        self.aria2c_threads_lbl.setVisible(visible)
    
    def _on_sb_toggle(self, state=None):
        """Show/hide SponsorBlock controls (YouTube only)."""
        if not self.chk_sb:
            return
        visible = self.chk_sb.isChecked()
        self.sb_action_lbl.setVisible(visible)
        self.sb_action_combo.setVisible(visible)
        self.sb_cats_row.setVisible(visible)
        is_remove = self.sb_action_combo.currentData() == "remove"
        self.chk_sb_keyframes.setVisible(visible and is_remove)
    
    def _on_sb_action_change(self, index=None):
        """Show/hide force-keyframes checkbox depending on action type."""
        if not self.chk_sb:
            return
        is_remove = self.sb_action_combo.currentData() == "remove"
        self.chk_sb_keyframes.setVisible(self.chk_sb.isChecked() and is_remove)
    
    def _on_audio_lang_change(self, index):
        pass  # Just stored by combo
    
    def _set_private_url(self, url):
        self.url_input.setText(url)
        self.log(f"🔒 {url}")
    
    # ══════════════════════════════════════════════════════════════════════════
    #  LOG
    # ══════════════════════════════════════════════════════════════════════════
    
    def log(self, message):
        self.log_text.appendPlainText(message)
        # Trim if too long
        if self.log_text.blockCount() > LOG_MAX_LINES:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 500)
            cursor.removeSelectedText()
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        self.log_text.clear()
        self._show_welcome()
    
    def _show_welcome(self):
        platform_name = get_platform_name(self.platform, self.lang)
        self.log("")
        self.log("  ═══════════════════════════════════════════════════")
        self.log("            ✦  AURA VIDEO DOWNLOADER  ✦")
        self.log(f"            {platform_name}")
        self.log("  ═══════════════════════════════════════════════════")
        self.log("")
        self.log(f"  {self.t['welcome_line2']}")
        self.log("")
        jokes = self.t.get("joke_welcome", [])
        if jokes:
            self.log(f"  {random.choice(jokes)}")
            self.log("")
        if is_debug_mode():
            self.log(f"  🐛 {self.t.get('debug_banner', 'DEBUG MODE — settings will NOT be saved')}")
            self.log("")
    
    # ══════════════════════════════════════════════════════════════════════════
    #  PROGRESS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _reset_progress(self):
        self.total_videos = 0
        self.downloaded_videos = 0
        self._last_destination = ""
        self._pending_history = False  # Deferred: True when 100% seen, flushed on Merger/next video/finish
        self.current_speed = ""
        self.current_eta = ""
        self._parallel_state = {}  # worker_id -> {total, downloaded, pct, speed, eta}
        self._is_parallel_mode = False
        self.progress_label.setText(self.t["progress_idle"])
        self.speed_label.setText(self.t["speed_idle"])
        self.progress_bar.setValue(0)
    
    def _update_progress_display(self):
        if self.total_videos > 0:
            text = self.t["progress_format"].format(downloaded=self.downloaded_videos, total=self.total_videos)
            self.progress_label.setText(text)
            # Update progress bar for playlists when video count changes
            if self.total_videos > 1:
                overall = int(self.downloaded_videos * 100 / self.total_videos)
                self.progress_bar.setValue(overall)
        else:
            self.progress_label.setText(self.t["progress_scanning"])
    
    def _update_speed_display(self):
        if self.current_speed:
            text = f"{self.current_speed}  ETA {self.current_eta}" if self.current_eta else self.current_speed
            self.speed_label.setText(text)
        else:
            self.speed_label.setText(self.t["speed_idle"])
    
    def _handle_progress_line(self, line):
        """Called from worker signal for each output line — runs on main thread."""
        try:
            self._handle_progress_line_impl(line)
        except Exception:
            pass  # Never crash on progress parsing
    
    def _handle_progress_line_impl(self, line):
        # ── Speed & ETA (native yt-dlp) ──
        speed_match = SPEED_REGEX.search(line)
        if speed_match:
            self.current_speed = speed_match.group(1)
            self.current_eta = speed_match.group(2)
            self._update_speed_display()
        else:
            speed_only = SPEED_ONLY_REGEX.search(line)
            if speed_only:
                self.current_speed = speed_only.group(1)
                self.current_eta = ""
                self._update_speed_display()
            else:
                # ── Speed & ETA (aria2c) ──
                aria_speed = ARIA2C_SPEED_REGEX.search(line)
                if aria_speed:
                    raw = aria_speed.group(1).strip()
                    # aria2c omits "/s" — add it for display consistency
                    self.current_speed = raw if '/s' in raw else f"{raw}/s"
                    aria_eta = ARIA2C_ETA_REGEX.search(line)
                    self.current_eta = aria_eta.group(1) if aria_eta else ""
                    self._update_speed_display()
        
        # ── Percent bar (native yt-dlp) ──
        current_file_pct = None
        pct_match = PERCENT_REGEX.search(line)
        if pct_match:
            try:
                current_file_pct = float(pct_match.group(1))
            except (ValueError, TypeError):
                pass
        else:
            # ── Percent bar (aria2c) ──
            aria_pct = ARIA2C_PROGRESS_REGEX.search(line)
            if aria_pct:
                try:
                    current_file_pct = float(aria_pct.group(1))
                except (ValueError, TypeError):
                    pass
        
        if current_file_pct is not None:
            if self.total_videos > 1:
                # Playlist: weighted overall progress
                overall = (self.downloaded_videos * 100 + current_file_pct) / self.total_videos
                self.progress_bar.setValue(int(overall))
            else:
                self.progress_bar.setValue(int(current_file_pct))
        
        # ── Video counter ("Downloading item X of Y") ──
        match = PROGRESS_REGEX.search(line)
        if match:
            # Flush previous video's pending history before starting new one
            self._flush_pending_history()
            self.total_videos = int(match.group(2))
            self.downloaded_videos = min(int(match.group(1)) - 1, self.total_videos)
            self._update_progress_display()
        
        # ── Track destinations ──
        if '[download] Destination:' in line:
            dest = line.split('Destination:', 1)[-1].strip()
            self._last_destination = Path(dest).stem if dest else ""
            # Reset bar for new file part (e.g. video→audio of same video)
            if self.total_videos <= 1:
                self.progress_bar.setValue(0)
        elif '[Merger] Merging formats into' in line:
            # Merger = final product. Update name to merged file, then flush.
            m = re.search(r'Merging formats into ["\'](.+?)["\']', line)
            if m:
                try:
                    self._last_destination = Path(m.group(1)).stem
                except (ValueError, TypeError):
                    pass
            self._pending_history = True
            self._flush_pending_history()
            return  # Already flushed, skip duplicate check below
        
        # Download 100% — mark pending (may be intermediate format, not final)
        if self._is_download_complete_line(line):
            self._pending_history = True
        
        # Archive skip — video is done for sure, flush immediately
        if self._is_archive_skip_line(line):
            self._pending_history = True
            self._flush_pending_history()
    
    def _flush_pending_history(self):
        """Flush pending history entry. Called when we're sure one video is fully done:
        after [Merger], when next video starts, on archive skip, or on download finish."""
        if not self._pending_history:
            return
        self._pending_history = False
        
        # Increment video counter
        if self.total_videos > 0 and self.downloaded_videos < self.total_videos:
            self.downloaded_videos = min(self.downloaded_videos + 1, self.total_videos)
            self._update_progress_display()
        
        name = self._last_destination or "Unknown"
        dtype = "audio" if self._get_mode() == self.MODE_AUDIO else "video"
        self._add_to_history(name, "done", "", dtype)
    
    def _is_download_complete_line(self, line):
        return (DOWNLOAD_COMPLETE_100_REGEX.search(line) is not None or 
                any(p in line for p in DOWNLOAD_COMPLETE_PATTERNS) or
                ARIA2C_COMPLETE_PATTERN in line)
    
    def _is_archive_skip_line(self, line):
        return any(p in line for p in ARCHIVE_SKIP_PATTERNS)
    
    def _handle_parallel_progress(self, worker_id, line):
        """Handle progress from one parallel worker — aggregates across all workers."""
        try:
            state = self._parallel_state.get(worker_id)
            if not state:
                return
            
            # Per-worker speed/ETA (native yt-dlp)
            speed_match = SPEED_REGEX.search(line)
            if speed_match:
                state['speed'] = speed_match.group(1)
                state['eta'] = speed_match.group(2)
            else:
                speed_only = SPEED_ONLY_REGEX.search(line)
                if speed_only:
                    state['speed'] = speed_only.group(1)
                    state['eta'] = ''
                else:
                    # aria2c speed/ETA
                    aria_speed = ARIA2C_SPEED_REGEX.search(line)
                    if aria_speed:
                        raw = aria_speed.group(1).strip()
                        state['speed'] = raw if '/s' in raw else f"{raw}/s"
                        aria_eta = ARIA2C_ETA_REGEX.search(line)
                        state['eta'] = aria_eta.group(1) if aria_eta else ''
            
            # Per-worker percent (native yt-dlp)
            pct_match = PERCENT_REGEX.search(line)
            if pct_match:
                try:
                    state['pct'] = float(pct_match.group(1))
                except (ValueError, TypeError):
                    pass
            else:
                # aria2c percent
                aria_pct = ARIA2C_PROGRESS_REGEX.search(line)
                if aria_pct:
                    try:
                        state['pct'] = float(aria_pct.group(1))
                    except (ValueError, TypeError):
                        pass
            
            # Per-worker video counter — new video starting, flush previous
            match = PROGRESS_REGEX.search(line)
            if match:
                self._flush_parallel_pending(state)
                state['total'] = int(match.group(2))
                state['downloaded'] = min(int(match.group(1)) - 1, state['total'])
            
            # Track destinations
            if '[download] Destination:' in line:
                dest = line.split('Destination:', 1)[-1].strip()
                state['last_dest'] = Path(dest).stem if dest else ''
                state['pct'] = 0  # Reset for new file part
            elif '[Merger] Merging formats into' in line:
                m = re.search(r'Merging formats into ["\'](.+?)["\']', line)
                if m:
                    try:
                        state['last_dest'] = Path(m.group(1)).stem
                    except (ValueError, TypeError):
                        pass
                state['pending'] = True
                self._flush_parallel_pending(state)
            elif self._is_download_complete_line(line):
                state['pending'] = True
            elif self._is_archive_skip_line(line):
                state['pending'] = True
                self._flush_parallel_pending(state)
            
            # Aggregate and display
            self._update_parallel_display()
        except Exception:
            pass
    
    def _flush_parallel_pending(self, state):
        """Flush pending history for one parallel worker."""
        if not state.get('pending'):
            return
        state['pending'] = False
        
        if state['total'] > 0 and state['downloaded'] < state['total']:
            state['downloaded'] = min(state['downloaded'] + 1, state['total'])
        
        dest = state.get('last_dest', '') or 'Unknown'
        dtype = "audio" if self._get_mode() == self.MODE_AUDIO else "video"
        self._add_to_history(dest, "done", "", dtype)
    
    def _update_parallel_display(self):
        """Aggregate all parallel workers' progress into unified display."""
        try:
            self._update_parallel_display_impl()
        except Exception:
            pass  # Never crash on progress display
    
    def _update_parallel_display_impl(self):
        states = self._parallel_state.values()
        if not states:
            return
        
        # Video counter: sum across workers
        total = sum(s['total'] for s in states)
        downloaded = sum(s['downloaded'] for s in states)
        
        if total > 0:
            text = self.t["progress_format"].format(downloaded=downloaded, total=total)
            self.progress_label.setText(text)
            # Weighted overall progress: completed videos + current files across workers
            avg_pct = 0
            active_workers = [s for s in states if s['pct'] > 0 and s['downloaded'] < s['total']]
            if active_workers:
                avg_pct = sum(s['pct'] for s in active_workers) / len(active_workers)
            overall = (downloaded * 100 + avg_pct) / total
            self.progress_bar.setValue(int(min(overall, 100)))
        else:
            # No totals yet — average current file percentages across workers
            pcts = [s['pct'] for s in states if s['pct'] > 0]
            if pcts:
                self.progress_bar.setValue(int(sum(pcts) / len(pcts)))
            self.progress_label.setText(self.t["progress_scanning"])
        
        # Speed: show sum of all workers' speeds
        total_speed = self._aggregate_speeds(states)
        if total_speed:
            self.speed_label.setText(total_speed)
    
    @staticmethod
    def _aggregate_speeds(states):
        """Sum speeds across workers, e.g. '1.5MiB/s' + '800KiB/s' → '2.3MiB/s'."""
        total_bytes = 0.0
        for s in states:
            raw = s.get('speed', '')
            if not raw:
                continue
            try:
                # Parse: "1.5MiB/s", "800KiB/s", "2.3GiB/s"
                num_str = ''
                unit = ''
                for j, c in enumerate(raw):
                    if c.isdigit() or c == '.':
                        num_str += c
                    else:
                        unit = raw[j:].split('/')[0].strip()
                        break
                val = float(num_str) if num_str else 0
                multipliers = {'B': 1, 'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3,
                               'KB': 1000, 'MB': 1000**2, 'GB': 1000**3,
                               'K': 1024, 'M': 1024**2, 'G': 1024**3}
                total_bytes += val * multipliers.get(unit, 1)
            except (ValueError, IndexError):
                continue
        
        if total_bytes <= 0:
            return ''
        
        # Format back to human-readable
        if total_bytes >= 1024**3:
            return f"⚡ {total_bytes / (1024**3):.1f}GiB/s"
        elif total_bytes >= 1024**2:
            return f"⚡ {total_bytes / (1024**2):.1f}MiB/s"
        elif total_bytes >= 1024:
            return f"⚡ {total_bytes / 1024:.0f}KiB/s"
        else:
            return f"⚡ {total_bytes:.0f}B/s"
    
    # ══════════════════════════════════════════════════════════════════════════
    #  BROWSE / DEPS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t.get("select_folder_title", "Select folder"),
                                                   self.outdir_input.text() or str(Path.home()))
        if folder:
            self.outdir_input.setText(folder)
            self.log(f"{self.t.get('folder_selected', 'Folder: ')}{folder}")
    
    def _browse_cookies(self):
        f, _ = QFileDialog.getOpenFileName(self, self.t.get("select_file_title", "Select file"),
                                            str(Path.home()), "Text files (*.txt);;All (*)")
        if f:
            self.cookies_input.setText(f)
            self.log(f"{self.t.get('file_selected', 'File: ')}{f}")
    
    def _open_download_folder(self):
        """Open the download folder in system file manager."""
        folder = self.outdir_input.text().strip()
        if folder and Path(folder).is_dir():
            if sys.platform == 'win32':
                os.startfile(folder)  # Reliable Explorer opening on Windows
            else:
                webbrowser.open(folder)
        else:
            self.log(self.t.get("open_folder_err", "❌ Folder not found"))
    
    def _get_default_outdir(self):
        """Get default output directory, ensuring it exists."""
        # On Windows, user may have moved Downloads via Settings → use shell API
        if sys.platform == 'win32':
            try:
                import ctypes
                from ctypes import wintypes
                GUID = ctypes.c_char_p(
                    b'\xe3\x9c\x45\x37\x4d\xd1\xd0\x42\xba\x46\x98\x65\xc6\xb4\x48\x40')
                SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
                SHGetKnownFolderPath.argtypes = [ctypes.c_char_p, ctypes.c_uint32,
                                                   ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
                path_ptr = ctypes.c_wchar_p()
                if SHGetKnownFolderPath(GUID, 0, None, ctypes.byref(path_ptr)) == 0:
                    result = Path(path_ptr.value)
                    ctypes.windll.ole32.CoTaskMemFree(path_ptr)
                    if result.is_dir():
                        return result
            except Exception:
                pass  # Fallback below
        downloads = Path.home() / "Downloads"
        if downloads.is_dir():
            return downloads
        return Path.home()
    
    def _check_dependencies_bg(self):
        """Check dependencies using proper QThread + Signal."""
        self.deps_worker = DepsWorker(self.pc)
        self.deps_worker.results_ready.connect(self._apply_dep_results)
        self.deps_worker.start()
    
    def _apply_dep_results(self, results):
        self.log(self.t["checking_deps"])
        self.log("")
        
        # Store resolved binary paths for later use
        s, v, p = results.get('ytdlp', ('error', '', ''))
        self._ytdlp_bin = p if p else "yt-dlp"
        if s == 'ok':
            self.ytdlp_status_label.setText(f"✅ {v}")
            self.ytdlp_status_label.setStyleSheet("color: #228B22;")
            self.log(f"{self.t['ytdlp_found']}{v}")
            self.log(f"    PATH: {p}")
        else:
            self.ytdlp_status_label.setText(self.t["not_found"])
            self.ytdlp_status_label.setStyleSheet("color: #DC143C;")
            self.log(self.t["ytdlp_not_found"])
        
        s, v, p = results.get('ffmpeg', ('error', '', ''))
        self._ffmpeg_bin = p if p else "ffmpeg"
        if s == 'ok':
            self.ffmpeg_status_label.setText(self.t["installed"])
            self.ffmpeg_status_label.setStyleSheet("color: #228B22;")
            self.log(self.t["ffmpeg_found"])
            self.log(f"    PATH: {p}")
        else:
            self.ffmpeg_status_label.setText(self.t["not_found"])
            self.ffmpeg_status_label.setStyleSheet("color: #DC143C;")
            self.log(self.t["ffmpeg_not_found"])
        
        s, v, p = results.get('nodejs', ('error', '', ''))
        if s == 'ok':
            self.nodejs_status_label.setText(f"✅ {v}")
            self.nodejs_status_label.setStyleSheet("color: #228B22;")
        elif s == 'notneeded':
            lbl = "не требуется" if self.lang == "ru" else "not required"
            self.nodejs_status_label.setText(f"ℹ️ {lbl}")
            self.nodejs_status_label.setStyleSheet("color: #888;")
        else:
            self.nodejs_status_label.setText(self.t["not_found"])
            self.nodejs_status_label.setStyleSheet("color: #FF8C00;")
        
        s, v, p = results.get('aria2c', ('error', '', ''))
        self._aria2c_bin = p if p else "aria2c"
        if s == 'ok':
            self.aria2c_status_label.setText(f"✅ {v}")
            self.aria2c_status_label.setStyleSheet("color: #228B22;")
            self.log(self.t.get("aria2c_found", "  ✅ aria2c:     found"))
            self.log(f"    PATH: {p}")
        else:
            opt = self.t.get("optional", "optional")
            self.aria2c_status_label.setText(f"ℹ️ {self.t['not_found']} ({opt})")
            self.aria2c_status_label.setStyleSheet("color: #888;")
            self.log(self.t.get("aria2c_missing_log", "  ℹ️ aria2c:     not found (optional)"))
        
        if self.pc.get("use_ytdlp_config", False):
            ensure_ytdlp_config()
        
        self.log("")
        self.log("-" * 50)
        self.log("")
    
    def _update_ytdlp(self):
        self.log(self.t["updating_ytdlp"])
        ytdlp_bin = getattr(self, '_ytdlp_bin', find_binary("yt-dlp"))
        self.log(f"   {self.t['updating_cmd']}")
        def _run():
            try:
                # Use yt-dlp's own self-update (system PATH binary, not pip)
                r = subprocess.run([ytdlp_bin, "-U", "--update-to", "master"],
                                    capture_output=True, text=True,
                                    encoding='utf-8', errors='surrogateescape',
                                    env=_get_subprocess_env(),
                                    creationflags=SUBPROCESS_FLAGS, timeout=120)
                output = _fix_encoding((r.stdout or '') + (r.stderr or '')).strip()
                if output:
                    self._sig_log.emit(output)
                if r.returncode == 0:
                    self._sig_log.emit(self.t.get("update_ytdlp_ok", "✅ yt-dlp updated"))
                else:
                    self._sig_log.emit(f"⚠️ Exit code: {r.returncode}")
            except Exception as e:
                self._sig_log.emit(f"❌ {e}")
        threading.Thread(target=_run, daemon=True).start()
    
    def _download_nodejs(self):
        webbrowser.open("https://nodejs.org/")
        self.log(self.t.get("nodejs_opening_browser", "Opening Node.js download page..."))
    
    def _reset_settings(self):
        reply = QMessageBox.question(self, self.t["error_title"],
                                      self.t["reset_confirm"],
                                      QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Set flag FIRST — prevents closeEvent from re-saving settings
            self._resetting = True
            
            # Stop any active download before deleting files
            self.stop_event.set()
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait(3000)
            for w in getattr(self, '_parallel_workers', []):
                w.stop()
                w.wait(3000)
                if w.isRunning():
                    try:
                        w.terminate()
                    except Exception:
                        pass
            # Kill restart mode subprocess
            if self._restart_process:
                try:
                    self._restart_process.terminate()
                    self._restart_process.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
                except Exception:
                    try:
                        self._restart_process.kill()
                    except Exception:
                        pass
            
            self.log(self.t.get("reset_log_header", "🗑️ === FULL SETTINGS RESET ==="))
            
            # Collect ALL directories and files to nuke
            dirs_to_nuke = set()
            files_to_nuke = set()
            
            try:
                dirs_to_nuke.add(get_settings_dir())
            except Exception:
                pass
            dirs_to_nuke.add(Path.home() / SETTINGS_FOLDER_NAME)
            
            # Pointer and legacy files
            files_to_nuke.add(get_pointer_file())
            files_to_nuke.add(_get_legacy_pointer())
            
            # Delete everything directly — no external script needed
            for d in dirs_to_nuke:
                self.log(f"  🗑️ → {d}")
                try:
                    if d.exists():
                        shutil.rmtree(d, ignore_errors=True)
                except Exception as e:
                    self.log(f"    ⚠️ {e}")
            
            for f in files_to_nuke:
                self.log(f"  🗑️ → {f}")
                try:
                    if f.exists():
                        f.unlink()
                except Exception as e:
                    self.log(f"    ⚠️ {e}")
            
            self.log("")
            self.log(self.t["settings_reset"])
            
            # Exit app
            QTimer.singleShot(500, lambda: QApplication.instance().quit())
    
    def _change_theme(self):
        dlg = ThemeSelector(self.lang, self)
        result = dlg.run()
        if result:
            QMessageBox.information(self, self.t.get("theme_title", "🎨"),
                self.t.get("theme_restart", "Theme saved. Restart app to apply."))
    
    def _change_platform(self):
        """Save current settings, show platform picker, restart with new platform."""
        # Save settings for current platform FIRST
        self._save_settings()
        self._save_download_history()
        
        dlg = PlatformSelector(self.lang, self.theme_id, self)
        new_platform = dlg.run()
        if new_platform and new_platform != self.platform:
            self._next_platform = new_platform
            self.close()
    
    # ══════════════════════════════════════════════════════════════════════════
    #  AUTH
    # ══════════════════════════════════════════════════════════════════════════
    
    def _get_auth_args(self):
        method = self._get_auth_method()
        if method == "none":
            return []
        if method == "cookies_file":
            cookies = self.cookies_input.text().strip()
            return ["--cookies", cookies] if cookies else []
        return ["--cookies-from-browser", method]
    
    # ══════════════════════════════════════════════════════════════════════════
    #  SMART MODE PRESETS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _get_presets_file(self):
        return get_settings_dir() / f"presets_{self.platform}.json"
    
    def _load_all_presets(self):
        try:
            f = self._get_presets_file()
            if f.exists():
                return json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            pass
        return {}
    
    def _save_all_presets(self, presets):
        if is_debug_mode():
            return
        try:
            f = self._get_presets_file()
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            self.log(f"❌ {e}")
    
    def _refresh_smart_presets(self):
        presets = self._load_all_presets()
        self.smart_combo.clear()
        self.smart_combo.addItems(sorted(presets.keys()))
    
    def _get_current_preset_data(self):
        data = {
            "mode": self._get_mode(),
            "quality": self._get_quality(),
            "audio_format": self._get_audio_format(),
            "audio_bitrate": self._get_audio_bitrate(),
            "use_archive": self.chk_archive.isChecked(),
            "download_subtitles": self.chk_subs.isChecked(),
            "subtitle_language": self._get_sub_language(),
            "use_aria2c": self.chk_aria2c.isChecked(),
            "aria2c_threads": self.aria2c_threads_combo.currentText(),
            "concurrent_videos": self.concurrent_combo.currentText(),
            "auth_method": self._get_auth_method(),
            "proxy": self.proxy_input.text(),
        }
        # SponsorBlock (YouTube only)
        if self.chk_sb:
            data["sb_enabled"] = self.chk_sb.isChecked()
            data["sb_action"] = self._get_sb_action()
            data["sb_categories"] = self._get_sb_categories()
            data["sb_force_keyframes"] = self.chk_sb_keyframes.isChecked()
        return data
    
    def _apply_preset_data(self, data):
        if "mode" in data:
            self._set_radio_group(self.mode_buttons, "mode_value", data["mode"])
        if "quality" in data:
            self._set_radio_group(self.quality_buttons, "q_value", data["quality"])
        if "audio_format" in data:
            self._set_radio_group(self.format_buttons, "fmt_value", data["audio_format"])
        if "audio_bitrate" in data:
            self._set_radio_group(self.bitrate_buttons, "br_value", data["audio_bitrate"])
        if "use_archive" in data:
            self.chk_archive.setChecked(data["use_archive"])
        if "download_subtitles" in data:
            self.chk_subs.setChecked(data["download_subtitles"])
        if "subtitle_language" in data:
            self._set_combo_by_data(self.sub_lang_combo, data["subtitle_language"])
        if "use_aria2c" in data:
            self.chk_aria2c.setChecked(data["use_aria2c"])
        if "aria2c_threads" in data:
            self.aria2c_threads_combo.setCurrentText(data["aria2c_threads"])
        if "concurrent_videos" in data:
            self.concurrent_combo.setCurrentText(data["concurrent_videos"])
        if "auth_method" in data:
            self._set_combo_by_data(self.auth_combo, data["auth_method"])
        if "proxy" in data:
            self.proxy_input.setText(data["proxy"])
        # SponsorBlock (YouTube only)
        if self.chk_sb:
            if "sb_enabled" in data:
                self.chk_sb.setChecked(data["sb_enabled"])
            if "sb_action" in data and data["sb_action"] in ("mark", "remove"):
                self._set_combo_by_data(self.sb_action_combo, data["sb_action"])
            if "sb_categories" in data:
                for cat_id, chk in self.sb_cat_checks.items():
                    chk.setChecked(cat_id in data["sb_categories"])
            if "sb_force_keyframes" in data:
                self.chk_sb_keyframes.setChecked(data["sb_force_keyframes"])
            self._on_sb_toggle()
        self._update_mode_visibility()
        self._on_format_change()
        self._update_url_examples()
    
    def _smart_save(self):
        name, ok = QInputDialog.getText(self, self.t["smart_mode_label"],
                                         self.t["smart_name_prompt"])
        if ok and name.strip():
            presets = self._load_all_presets()
            presets[name.strip()] = self._get_current_preset_data()
            self._save_all_presets(presets)
            self._refresh_smart_presets()
            self.smart_combo.setCurrentText(name.strip())
            self.log(f"{self.t['smart_saved']} '{name.strip()}'")
    
    def _smart_load(self):
        name = self.smart_combo.currentText()
        if not name:
            return
        presets = self._load_all_presets()
        if name in presets:
            self._apply_preset_data(presets[name])
            self.log(f"{self.t['smart_loaded']} '{name}'")
    
    def _smart_delete(self):
        name = self.smart_combo.currentText()
        if not name:
            return
        presets = self._load_all_presets()
        if name in presets:
            del presets[name]
            self._save_all_presets(presets)
            self._refresh_smart_presets()
            self.log(f"{self.t['smart_deleted']} '{name}'")
    
    # ══════════════════════════════════════════════════════════════════════════
    #  IMPORT / EXPORT
    # ══════════════════════════════════════════════════════════════════════════
    
    def _import_links(self):
        f, _ = QFileDialog.getOpenFileName(self, self.t.get("import_btn", "Import"),
                                            str(Path.home()),
                                            "JSON/CSV/TXT (*.json *.csv *.txt);;All (*)")
        if not f:
            return
        try:
            text = Path(f).read_text(encoding='utf-8')
            urls = []
            if f.endswith('.json'):
                data = json.loads(text)
                if isinstance(data, list):
                    for item in data:
                        urls.append(item['url'] if isinstance(item, dict) else str(item))
                elif isinstance(data, dict) and 'urls' in data:
                    urls = data['urls']
            else:
                for line in text.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line.split(',')[0].strip() if f.endswith('.csv') else line)
            
            if urls:
                self.url_input.setText(urls[0])
                self.log(self.t['import_success'].format(count=len(urls)))
                for u in urls:
                    self.log(f"  → {u}")
        except Exception as e:
            self.log(f"{self.t.get('import_error', '❌ Import error')}: {e}")
    
    def _export_history(self):
        if not self.download_history:
            QMessageBox.information(self, self.t.get("export_btn", "Export"), self.t.get("export_empty", "No history to export"))
            return
        f, _ = QFileDialog.getSaveFileName(self, self.t.get("export_btn", "Export"),
                                            str(Path.home() / "aura_history.json"),
                                            "JSON (*.json);;Text (*.txt)")
        if not f:
            return
        try:
            if f.endswith('.json'):
                Path(f).write_text(json.dumps(self.download_history, ensure_ascii=False, indent=2), encoding='utf-8')
            else:
                lines = [f"{e.get('date','')} | {e.get('name','')} | {e.get('status','')}"
                         for e in self.download_history]
                Path(f).write_text('\n'.join(lines), encoding='utf-8')
            self.log(f"{self.t['export_success']} {f}")
        except Exception as e:
            self.log(f"❌ {e}")
    
    # ══════════════════════════════════════════════════════════════════════════
    #  DOWNLOAD HISTORY
    # ══════════════════════════════════════════════════════════════════════════
    
    def _get_history_file(self):
        return get_settings_dir() / f"history_{self.platform}.json"
    
    def _load_download_history(self):
        try:
            f = self._get_history_file()
            if f.exists():
                self.download_history = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            self.download_history = []
        self._dm_refresh_tree()
    
    def _save_download_history(self):
        if is_debug_mode():
            return
        try:
            f = self._get_history_file()
            f.parent.mkdir(parents=True, exist_ok=True)
            # Keep max 1000
            data = self.download_history[-1000:]
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
    
    def _add_to_history(self, name, status="done", size="", dtype="video"):
        entry = {
            "name": name, "status": status, "size": size, "type": dtype,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "platform": self.platform,
        }
        self.download_history.append(entry)
        self._save_download_history()
        self._dm_refresh_tree()
    
    def _dm_refresh_tree(self):
        self.dm_tree.clear()
        filt = "all"
        btn = self.dm_filter_group.checkedButton()
        if btn:
            filt = btn.property("filter") or "all"
        search = self.dm_search.text().lower().strip() if hasattr(self, 'dm_search') else ""
        
        for entry in reversed(self.download_history):
            if filt != "all" and entry.get("type") != filt:
                continue
            if search and search not in entry.get("name", "").lower():
                continue
            item = QTreeWidgetItem([
                entry.get("status", ""),
                entry.get("name", ""),
                entry.get("size", ""),
                entry.get("date", ""),
            ])
            self.dm_tree.addTopLevelItem(item)
    
    def _dm_apply_filter(self, *args):
        self._dm_refresh_tree()
    
    def _dm_sort(self, key):
        # Toggle direction on repeated click
        if getattr(self, '_last_sort_key', None) == key:
            self._sort_reverse = not getattr(self, '_sort_reverse', True)
        else:
            self._sort_reverse = True
        self._last_sort_key = key
        self.download_history.sort(key=lambda e: e.get(key, ""), reverse=self._sort_reverse)
        self._dm_refresh_tree()
    
    def _dm_clear_completed(self):
        self.download_history = [e for e in self.download_history if e.get("status") != "done"]
        self._save_download_history()
        self._dm_refresh_tree()
    
    # ══════════════════════════════════════════════════════════════════════════
    #  DOWNLOAD LOGIC (Core backend)
    # ══════════════════════════════════════════════════════════════════════════
    
    def normalize_url(self, url, mode):
        url = url.strip().rstrip('/')
        if not url:
            return ""
        if not self.pc.get("normalize_channel_url", False):
            return url
        if mode == self.MODE_CHANNEL:
            known_suffixes = ['/videos', '/shorts', '/streams', '/playlists',
                            '/community', '/about', '/featured', '/channels']
            url_lower = url.lower()
            has_suffix = any(url_lower.endswith(s) for s in known_suffixes)
            has_special_path = '/watch?' in url or '/playlist?' in url
            if not has_suffix and not has_special_path:
                url += '/videos'
                self.log(self.t["url_videos_added"])
        return url
    
    def _is_valid_url_format(self, url):
        url = url.strip().lower()
        if not url:
            return False
        if url.startswith(('http://', 'https://')):
            return True
        domains = self.pc.get("domains", [])
        return any(d in url for d in domains)
    
    def validate_inputs(self):
        try:
            return self._validate_inputs_impl()
        except Exception as e:
            import traceback
            self.log(f"\n❌ ERROR in validate_inputs:\n{traceback.format_exc()}")
            return None
    
    def _validate_inputs_impl(self):
        t = self.t
        mode = self._get_mode()
        url = self.url_input.text().strip()
        outdir = self.outdir_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, t.get("error_title", "Error"), t["error_no_url"])
            return None
        
        if not outdir:
            QMessageBox.warning(self, t.get("error_title", "Error"), t["error_no_outdir"])
            return None
        
        if not self._is_valid_url_format(url):
            result = QMessageBox.question(self, t.get("error_title", "Error"),
                                           t["error_invalid_url"],
                                           QMessageBox.Yes | QMessageBox.No)
            if result != QMessageBox.Yes:
                return None
        
        # Ensure output directory exists
        try:
            Path(outdir).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        url = self.normalize_url(url, mode)
        cookies = self.cookies_input.text().strip()
        
        return {
            "mode": mode, "url": url, "outdir": outdir, "cookies": cookies,
        }
    
    def _get_output_template(self, outdir, mode):
        platform_name = get_platform_name(self.platform, self.lang)
        base = str(Path(outdir) / platform_name)
        numbering = "" if self.chk_nonumber.isChecked() else "%(playlist_index)s_"
        
        # Truncate directory names to 60 chars to prevent Windows MAX_PATH (260) overflow.
        # --trim-filenames only trims the filename, not directory components.
        # A 100+ char channel name + 150 char filename + deep base path → OSError.
        uploader = "%(uploader).60s"
        playlist = "%(playlist_title).60s"
        
        if mode == self.MODE_CHANNEL:
            return str(Path(base) / uploader / f"{numbering}%(title)s.%(ext)s")
        elif mode == self.MODE_PLAYLIST:
            return str(Path(base) / playlist / f"{numbering}%(title)s.%(ext)s")
        elif mode == self.MODE_AUDIO:
            source = self._get_audio_source()
            if source == self.AUDIO_SOURCE_CHANNEL:
                return str(Path(base) / "Audio" / uploader / f"{numbering}%(title)s.%(ext)s")
            elif source == self.AUDIO_SOURCE_PLAYLIST:
                return str(Path(base) / "Audio" / playlist / f"{numbering}%(title)s.%(ext)s")
            return str(Path(base) / "Audio" / "%(title)s.%(ext)s")
        return str(Path(base) / "%(title)s.%(ext)s")
    
    def _get_video_format_string(self, quality, audio_lang=None):
        height_map = {q[0]: q[2] for q in VIDEO_QUALITIES}
        height = height_map.get(quality, 0)
        
        audio_filter = ""
        if audio_lang and audio_lang != "any":
            audio_filter = f"[language={audio_lang}]"
        
        if quality == "max":
            return f"bv*+ba{audio_filter}/b" if audio_filter else "bv*+ba/b"
        return f"bv*[height<={height}]+ba{audio_filter}/b[height<={height}]/b"
    
    def _get_audio_format_string(self, audio_lang=None):
        lang_filter = f"[language={audio_lang}]" if audio_lang and audio_lang != "any" else ""
        return f"ba{lang_filter}/b"
    
    def _build_command(self, mode, url, cookies, output_template, archive_path, max_downloads=None):
        try:
            return self._build_command_impl(mode, url, cookies, output_template, archive_path, max_downloads)
        except Exception as e:
            import traceback
            self.log(f"\n❌ ERROR in _build_command:\n{traceback.format_exc()}")
            raise
    
    def _build_command_impl(self, mode, url, cookies, output_template, archive_path, max_downloads=None):
        # Use system PATH binary (resolved by DepsWorker)
        ytdlp_bin = getattr(self, '_ytdlp_bin', find_binary("yt-dlp"))
        cmd = [ytdlp_bin]
        
        # ffmpeg location (from system PATH)
        ffmpeg_bin = getattr(self, '_ffmpeg_bin', find_binary("ffmpeg"))
        ffmpeg_dir = str(Path(ffmpeg_bin).parent) if ffmpeg_bin and ffmpeg_bin != "ffmpeg" else None
        if ffmpeg_dir:
            cmd.extend(["--ffmpeg-location", ffmpeg_dir])
        
        # Config file
        if self.pc.get("use_ytdlp_config", False):
            ytdlp_conf = get_ytdlp_config_path()
            if ytdlp_conf and ytdlp_conf.exists():
                cmd.extend(["--config-location", str(ytdlp_conf)])
        
        # JavaScript runtime for YouTube (required for n-challenge solving)
        # Only "deno" is enabled by default in yt-dlp; explicitly enable "node"
        if self.platform == "youtube":
            cmd.extend(["--js-runtimes", "node"])
        
        cmd.extend(["-o", output_template])
        
        # Sanitize filenames on Windows (titles with : ? * " etc crash file creation)
        if sys.platform == 'win32':
            cmd.append("--windows-filenames")
            # Windows MAX_PATH = 260 chars. Long video titles (200+ chars) combined
            # with deep output paths easily exceed this → OSError crash.
            # --windows-filenames only strips illegal chars, NOT length.
            # Trim filename component to 150 chars to leave room for path prefix.
            cmd.extend(["--trim-filenames", "150"])
        
        if self.chk_archive.isChecked() and archive_path:
            cmd.extend(["--download-archive", str(archive_path)])
        
        audio_lang = self._get_audio_language()
        
        # Collect YouTube extractor params — will be emitted as single --extractor-args
        yt_extractor_params = []
        
        # Metadata language (title, description) — separate from audio track
        meta_lang = self._get_meta_language()
        if meta_lang and meta_lang != "any" and self.platform == "youtube":
            yt_extractor_params.append(f"lang={meta_lang}")
            
            ml = meta_lang
            ML = ml.upper()
            # Accept-Language header
            if ml == "ru":
                al_hdr = "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
            elif ml == "en":
                al_hdr = "en-US,en;q=0.9"
            else:
                al_hdr = f"{ml}-{ML},{ml};q=0.9,en-US;q=0.8,en;q=0.7"
            cmd.extend(["--add-header", f"Accept-Language:{al_hdr}"])
        
        if mode == self.MODE_AUDIO:
            fmt = self._get_audio_format()
            bitrate = self._get_audio_bitrate()
            cmd.extend(["-f", self._get_audio_format_string(audio_lang)])
            cmd.extend(["-x", "--audio-format", fmt])
            if bitrate != "max" and fmt not in ("wav", "flac"):
                cmd.extend(["--audio-quality", bitrate])
            # Single audio — prevent downloading entire playlist
            src = self._get_audio_source()
            if src == self.AUDIO_SOURCE_VIDEO:
                cmd.append("--no-playlist")
        else:
            quality = self._get_quality()
            cmd.extend(["-f", self._get_video_format_string(quality, audio_lang)])
            # Single video — prevent downloading entire playlist
            if mode == self.MODE_VIDEO:
                cmd.append("--no-playlist")
        
        # Subtitles
        if self.chk_subs.isChecked():
            sub_lang = self._get_sub_language()
            cmd.extend(["--write-sub", "--sub-lang", sub_lang])
            # Auto-generated subtitles only exist on YouTube
            if self.platform == "youtube":
                cmd.append("--write-auto-sub")
        
        # SponsorBlock (YouTube only)
        if self.platform == "youtube" and self.chk_sb and self.chk_sb.isChecked():
            cats = self._get_sb_categories()
            if cats:
                cats_str = ",".join(cats)
                action = self._get_sb_action()
                if action == "remove":
                    cmd.extend(["--sponsorblock-remove", cats_str])
                    if self.chk_sb_keyframes.isChecked():
                        cmd.append("--force-keyframes-at-cuts")
                else:
                    cmd.extend(["--sponsorblock-mark", cats_str])
        
        # Reverse
        if self.chk_reverse.isChecked() and mode in (self.MODE_PLAYLIST, self.MODE_CHANNEL):
            cmd.append("--playlist-reverse")
        
        # Cookies / Auth
        auth_args = self._get_auth_args()
        has_cookies_or_auth = bool(auth_args)
        
        if not has_cookies_or_auth and cookies and os.path.isfile(cookies):
            cmd.extend(["--cookies", cookies])
            has_cookies_or_auth = True
        elif auth_args:
            cmd.extend(auth_args)
        
        # no_cookies_args: platform-specific fallback when no cookies/auth provided
        # cookies_args: platform-specific args when cookies/auth ARE provided
        # Extract extractor-args separately to merge with our yt_extractor_params
        ea_source = self.pc.get("cookies_args", []) if has_cookies_or_auth else self.pc.get("no_cookies_args", [])
        if ea_source:
            i = 0
            while i < len(ea_source):
                if ea_source[i] == "--extractor-args" and i + 1 < len(ea_source):
                    ea_val = ea_source[i + 1]
                    if ea_val.startswith("youtube:"):
                        params_str = ea_val[len("youtube:"):]
                        for p in params_str.split(";"):
                            p = p.strip()
                            if p:
                                yt_extractor_params.append(p)
                    else:
                        cmd.extend(["--extractor-args", ea_val])
                    i += 2
                else:
                    cmd.append(ea_source[i])
                    i += 1
        
        # Emit all YouTube extractor params as single --extractor-args
        if yt_extractor_params:
            combined = ";".join(yt_extractor_params)
            cmd.extend(["--extractor-args", f"youtube:{combined}"])
        
        # Proxy
        proxy = self.proxy_input.text().strip()
        if proxy:
            cmd.extend(["--proxy", proxy])
        
        # aria2c
        if self.chk_aria2c.isChecked():
            threads = self.aria2c_threads_combo.currentText()
            cmd.extend(["--downloader", "aria2c",
                        "--downloader-args", f"aria2c:-x {threads} -s {threads} -k 1M --check-certificate=false"])
        
        # Max downloads
        if max_downloads:
            cmd.extend(["--max-downloads", str(max_downloads)])
        
        # Network resilience: longer timeout, infinite retries
        cmd.extend(["--socket-timeout", "60",
                     "--retries", "inf",
                     "--fragment-retries", "inf",
                     "--extractor-retries", "inf",
                     "--file-access-retries", "inf",
                     "--retry-sleep", "exp=1:10"])
        
        # Platform-specific extra args
        extra = self.pc.get("extra_args", [])
        if extra:
            cmd.extend(extra)
        
        cmd.append(url)
        return cmd
    
    def start_download(self):
        try:
            self._start_download_impl()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.log(f"\n❌ CRITICAL ERROR in start_download:\n{tb}")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def _start_download_impl(self):
        params = self.validate_inputs()
        if not params:
            return
        
        mode = params["mode"]
        url = params["url"]
        cookies = params["cookies"]
        outdir = params["outdir"]
        
        # Warn about mass audio download from channel/playlist
        if mode == self.MODE_AUDIO:
            src = self._get_audio_source()
            if src in (self.AUDIO_SOURCE_CHANNEL, self.AUDIO_SOURCE_PLAYLIST):
                warn = self.pc.get("warn_mass_audio", {})
                warn_msg = warn.get(self.lang, warn.get("en", ""))
                if warn_msg:
                    reply = QMessageBox.question(self, "⚠️", warn_msg,
                                                  QMessageBox.Yes | QMessageBox.No)
                    if reply != QMessageBox.Yes:
                        return
        
        output_template = self._get_output_template(outdir, mode)
        
        # Warn about SponsorBlock re-encoding (remove + force-keyframes)
        if (self.platform == "youtube" and self.chk_sb and self.chk_sb.isChecked()
                and self._get_sb_action() == "remove"
                and self.chk_sb_keyframes.isChecked()):
            reply = QMessageBox.question(self, "⚠️",
                self.t.get("sb_reencode_warn", "SponsorBlock + Precise cuts will re-encode the entire video. Continue?"),
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        settings_dir = get_settings_dir()
        settings_dir.mkdir(parents=True, exist_ok=True)
        archive_path = settings_dir / f"archive_{self.platform}.txt"
        
        self._reset_progress()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.stop_event.clear()
        self._download_generation += 1
        self._restart_process = None
        self._restart_thread = None
        
        self.log("")
        self.log("=" * 50)
        self.log(f"  ▶ {self.t['download_started']}")
        self.log(f"  URL: {url}")
        self.log(self.t.get("log_mode", "  Mode: {mode}").format(mode=mode))
        meta_lang = self._get_meta_language()
        if meta_lang != "any" and self.platform == "youtube":
            self.log(self.t.get("log_title_lang", "  🏷️ Title language: {lang}").format(lang=meta_lang))
            self.log(self.t.get("log_ytdlp_titles_note", "  ⚠️ Translated titles broken in yt-dlp (bug #13363)"))
            self.log(self.t.get("log_ytdlp_titles_note2", "     Will work when yt-dlp fixes it"))
        # SponsorBlock summary
        if self.platform == "youtube" and self.chk_sb and self.chk_sb.isChecked():
            sb_cats = self._get_sb_categories()
            if sb_cats:
                sb_action = self._get_sb_action()
                action_name = self.t.get(f"sb_action_{sb_action}", sb_action)
                cats_str = ", ".join(sb_cats)
                self.log(f"  {self.t['sb_enabled_log'].format(action=action_name, cats=cats_str)}")
                if sb_action == "remove" and self.chk_sb_keyframes.isChecked():
                    self.log(f"  {self.t.get('sb_force_keyframes', '🔑 Precise cuts')}")
        self.log("=" * 50)
        self.log("")
        
        self._save_settings()
        
        # Determine concurrent video count
        concurrent = 1
        is_multi = mode in (self.MODE_PLAYLIST, self.MODE_CHANNEL)
        if not is_multi and mode == self.MODE_AUDIO:
            src = self._get_audio_source()
            is_multi = src in (self.AUDIO_SOURCE_CHANNEL, self.AUDIO_SOURCE_PLAYLIST)
        
        if is_multi:
            try:
                concurrent = int(self.concurrent_combo.currentText())
            except (ValueError, AttributeError):
                concurrent = 1
        
        if self.chk_restart.isChecked() and mode in (self.MODE_PLAYLIST, self.MODE_CHANNEL):
            self._download_with_restart(mode, url, cookies, output_template, archive_path)
        elif concurrent > 1 and is_multi:
            self._download_parallel(mode, url, cookies, output_template, archive_path, concurrent)
        else:
            cmd = self._build_command(mode, url, cookies, output_template, archive_path)
            self.log(f"$ {' '.join(cmd)}")
            self.log("")
            self._run_worker(cmd)
    
    def _run_worker(self, cmd):
        self.worker = DownloadWorker(cmd, self.stop_event)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self._handle_progress_line)
        self.worker.finished_signal.connect(self._download_finished)
        self.worker.start()
    
    def _download_parallel(self, mode, url, cookies, output_template, archive_path, concurrent):
        """Download multiple videos simultaneously using N interleaved yt-dlp processes."""
        self.log(self.t.get("log_parallel", "🚀 Parallel download: {n} videos at once").format(n=concurrent))
        self.log("")
        
        self._parallel_workers = []
        self._parallel_codes = []
        self._parallel_total = concurrent
        self._is_parallel_mode = True
        self._parallel_state = {}
        self._parallel_archive_main = archive_path  # Main archive file
        self._parallel_archive_parts = []  # Per-worker archive files
        
        for i in range(concurrent):
            worker_id = i + 1
            items_arg = f"{worker_id}::{concurrent}"
            
            # Use per-worker archive file to avoid race condition
            worker_archive = None
            if archive_path and self.chk_archive.isChecked():
                ap = Path(archive_path)
                worker_archive = str(ap.parent / f"{ap.stem}_w{worker_id}{ap.suffix}")
                self._parallel_archive_parts.append(worker_archive)
                # Copy main archive to each worker so they all know what's already downloaded
                try:
                    if ap.exists():
                        shutil.copy2(str(ap), worker_archive)
                except Exception:
                    pass
            
            cmd = self._build_command(mode, url, cookies, output_template, worker_archive or archive_path)
            cmd.insert(-1, "--playlist-items")
            cmd.insert(-1, items_arg)
            
            self.log(self.t.get("log_worker_task", "  Worker {id}/{total}: --playlist-items {items}").format(
                id=worker_id, total=concurrent, items=items_arg))
            
            self._parallel_state[worker_id] = {
                'total': 0, 'downloaded': 0, 'pct': 0,
                'speed': '', 'eta': '', 'last_dest': '', 'pending': False
            }
            
            worker = DownloadWorker(cmd, self.stop_event)
            worker.log_signal.connect(lambda line, n=worker_id: self.log(f"[W{n}] {line}"))
            worker.progress_signal.connect(lambda line, n=worker_id: self._handle_parallel_progress(n, line))
            worker.finished_signal.connect(self._parallel_worker_finished)
            self._parallel_workers.append(worker)
        
        self.log("")
        
        for w in self._parallel_workers:
            w.start()
    
    def _parallel_worker_finished(self, return_code):
        """Called when one parallel worker finishes. When all done, signal completion."""
        self._parallel_codes.append(return_code)
        remaining = self._parallel_total - len(self._parallel_codes)
        
        if remaining > 0:
            self.log(self.t.get("log_worker_done", "  ℹ️ Worker finished (code {code}), {remaining} still running...").format(
                code=return_code, remaining=remaining))
            return
        
        # All workers done — merge per-worker archive files into main archive
        main_archive = getattr(self, '_parallel_archive_main', None)
        parts = getattr(self, '_parallel_archive_parts', [])
        if main_archive and parts:
            try:
                # Collect all unique video IDs from per-worker archives
                all_ids = set()
                if Path(main_archive).exists():
                    all_ids.update(Path(main_archive).read_text(encoding='utf-8').strip().splitlines())
                for part in parts:
                    p = Path(part)
                    if p.exists():
                        all_ids.update(p.read_text(encoding='utf-8').strip().splitlines())
                        try:
                            p.unlink()  # Clean up per-worker file
                        except Exception:
                            pass
                # Write merged archive
                if all_ids:
                    Path(main_archive).write_text('\n'.join(sorted(all_ids)) + '\n', encoding='utf-8')
            except Exception as e:
                self.log(f"⚠️ Archive merge: {e}")
        
        # All workers done — report overall result
        worst_code = max(self._parallel_codes) if self._parallel_codes else 0
        self._parallel_workers = []
        self._download_finished(worst_code)
    
    def _download_finished(self, return_code):
        try:
            self._download_finished_impl(return_code)
        except Exception as e:
            import traceback
            self.log(f"\n⚠️ ERROR in _download_finished:\n{traceback.format_exc()}")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def _download_finished_impl(self, return_code):
        # Flush any pending history entry from last video (single mode)
        if hasattr(self, '_pending_history') and self._pending_history:
            self._flush_pending_history()
        
        # Flush any pending entries from parallel workers
        for state in getattr(self, '_parallel_state', {}).values():
            self._flush_parallel_pending(state)
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._is_parallel_mode = False
        self._parallel_state = {}
        
        # Reset progress indicators
        self.progress_bar.setValue(100 if return_code == 0 else 0)
        self.speed_label.setText(self.t["speed_idle"])
        self.current_speed = ""
        self.current_eta = ""
        
        self.log("")
        if return_code == 0:
            self.log(f"✅ {self.t['download_complete']}")
            jokes = self.t.get("joke_finish", [])
            if jokes:
                self.log(f"  {random.choice(jokes)}")
            self.progress_label.setText(self.t.get("progress_done", "✅"))
            self._show_finish_notification(True)
        elif self.stop_event.is_set():
            # User explicitly stopped — not an error
            self.progress_label.setText(f"⏹")
        else:
            self.log(f"⚠️ {self.t.get('download_error', 'Download finished with errors')} (code: {return_code})")
            self.progress_label.setText(f"⚠️ code {return_code}")
            self._show_finish_notification(False)
        self.log("")
    
    def _show_finish_notification(self, success):
        """Show system tray notification when download finishes."""
        if not self.chk_notify.isChecked():
            return
        if self.isActiveWindow():
            return
        if not hasattr(self, '_tray_icon'):
            return
        try:
            title = "✦ AURA ✦"
            if success:
                msg = self.t.get("notify_title_done", "✅ Download complete")
                icon_type = QSystemTrayIcon.Information
            else:
                msg = self.t.get("notify_title_error", "⚠️ Download finished with errors")
                icon_type = QSystemTrayIcon.Warning
            self._tray_icon.showMessage(title, msg, icon_type, 5000)
        except Exception:
            pass
    
    def stop_download(self):
        has_running = False
        if self.worker and self.worker.isRunning():
            has_running = True
        for w in getattr(self, '_parallel_workers', []):
            if w.isRunning():
                has_running = True
                break
        # Restart mode uses threading.Thread + subprocess, not QThread workers
        if self._restart_thread and self._restart_thread.is_alive():
            has_running = True
        
        if has_running:
            reply = QMessageBox.question(self, "⏹", self.t.get("stop_confirm", "Stop download?"),
                                          QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        self.stop_event.set()
        if self.worker:
            self.worker.stop()
        for w in getattr(self, '_parallel_workers', []):
            w.stop()
        self._parallel_workers = []
        # Kill restart mode subprocess directly (don't wait for stdout loop to notice)
        if self._restart_process:
            try:
                self._restart_process.terminate()
                self._restart_process.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
            except Exception:
                try:
                    self._restart_process.kill()
                except Exception:
                    pass
            self._restart_process = None
        
        self.log(f"\n⏹ {self.t['download_stopped']}\n")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def _download_with_restart(self, mode, url, cookies, output_template, archive_path):
        """Download with restart-each-video mode (sequential runs)."""
        self.log(f"🔄 {self.t.get('restart_mode', 'Restart mode: downloading one at a time...')}")
        
        # Build command on main thread (widgets accessed safely)
        base_cmd = self._build_command(mode, url, cookies, output_template, archive_path, max_downloads=1)
        generation = self._download_generation  # Capture — ignore stale callbacks
        
        def _restart_loop():
            empty_runs = 0
            run_number = 0
            while not self.stop_event.is_set() and empty_runs < MAX_CONSECUTIVE_EMPTY_RUNS:
                run_number += 1
                self._sig_log.emit(f"\n{'='*40}\n  Run #{run_number}\n{'='*40}")
                
                cmd = list(base_cmd)  # copy of pre-built command
                
                try:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                text=True, encoding='utf-8', errors='surrogateescape',
                                                creationflags=SUBPROCESS_FLAGS, env=_get_subprocess_env(),
                                                bufsize=1)
                    self._restart_process = process  # Track for stop/close cleanup
                    found_new = False
                    for line in process.stdout:
                        if self.stop_event.is_set():
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except Exception:
                                process.kill()
                            return
                        line = _fix_encoding(line.rstrip('\n\r'))
                        if line:
                            self._sig_log.emit(line)
                            self._sig_progress.emit(line)
                            if self._is_download_complete_line(line):
                                found_new = True
                    
                    process.wait()
                    self._restart_process = None
                    
                    if found_new:
                        empty_runs = 0
                    else:
                        empty_runs += 1
                
                except Exception as e:
                    self._sig_log.emit(f"❌ {e}")
                    self._restart_process = None
                    break
            
            # Only emit finished if this is still the current download
            # (user may have stopped and started a new one)
            if self._download_generation == generation:
                self._sig_finished.emit(0)
        
        t = threading.Thread(target=_restart_loop, daemon=True)
        self._restart_thread = t
        t.start()


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG LOCATION DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class ConfigLocationDialog(QDialog):
    """Ask user where to store settings on first run."""
    def __init__(self, lang="en", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.result_path = None
        self._key1_held_since = None  # timestamp when "1" was pressed
        self._debug_timer = QTimer(self)
        self._debug_timer.setInterval(500)  # check every 0.5s
        self._debug_timer.timeout.connect(self._check_debug_hold)
        
        # No close button — must choose
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        texts = {
            "ru": {
                "title": "Выбор папки для настроек",
                "message": (f"Выберите, где создать папку с настройками:\n\n"
                           f"📁 {SETTINGS_FOLDER_NAME}\n\n"
                           f"Настройки сохраняются отдельно для каждой платформы.\n\n"
                           f"• Домашняя папка — стандартное расположение\n"
                           f"• Своя папка — например, рядом со скриптом"),
                "home_btn": "🏠 Домашняя папка",
                "custom_btn": "📂 Выбрать свою папку",
                "error_folder": "Не удалось создать папку настроек:\n{e}",
            },
            "en": {
                "title": "Settings Location",
                "message": (f"Choose where to create the settings folder:\n\n"
                           f"📁 {SETTINGS_FOLDER_NAME}\n\n"
                           f"Settings are saved separately for each platform.\n\n"
                           f"• Home folder — standard location\n"
                           f"• Custom folder — e.g., next to the script"),
                "home_btn": "🏠 Home Folder",
                "custom_btn": "📂 Choose Folder",
                "error_folder": "Cannot create settings folder:\n{e}",
            },
        }
        t = texts.get(lang, texts["en"])
        self._t = t
        
        self.setWindowTitle(f"✦ AURA ✦ — {t['title']}")
        self.setFixedSize(440, 220)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        title = QLabel("✦ AURA VIDEO DOWNLOADER ✦")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50;")
        layout.addWidget(title)
        
        msg = QLabel(t["message"])
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 10pt;")
        layout.addWidget(msg)
        
        btn_layout = QHBoxLayout()
        
        home_btn = QPushButton(t["home_btn"])
        home_btn.setFixedHeight(36)
        home_btn.setCursor(Qt.PointingHandCursor)
        home_btn.clicked.connect(self._use_home)
        btn_layout.addWidget(home_btn)
        
        custom_btn = QPushButton(t["custom_btn"])
        custom_btn.setFixedHeight(36)
        custom_btn.setCursor(Qt.PointingHandCursor)
        custom_btn.clicked.connect(self._use_custom)
        btn_layout.addWidget(custom_btn)
        
        layout.addLayout(btn_layout)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_1 and not event.isAutoRepeat():
            self._key1_held_since = time.monotonic()
            self._debug_timer.start()
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_1 and not event.isAutoRepeat():
            self._key1_held_since = None
            self._debug_timer.stop()
        super().keyReleaseEvent(event)
    
    def _check_debug_hold(self):
        if self._key1_held_since and (time.monotonic() - self._key1_held_since) >= 12.0:
            self._debug_timer.stop()
            self._key1_held_since = None
            self._activate_debug()
    
    def _use_home(self):
        try:
            settings_dir = Path.home() / SETTINGS_FOLDER_NAME
            settings_dir.mkdir(parents=True, exist_ok=True)
            pointer_file = get_pointer_file()
            pointer_file.write_text("default", encoding='utf-8')
            self.result_path = settings_dir
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self._t["title"], self._t["error_folder"].format(e=e))
    
    def _use_custom(self):
        folder = QFileDialog.getExistingDirectory(self, self._t["title"], str(Path.home()))
        if folder:
            try:
                settings_dir = Path(folder) / SETTINGS_FOLDER_NAME
                settings_dir.mkdir(parents=True, exist_ok=True)
                pointer_file = get_pointer_file()
                pointer_file.write_text(folder, encoding='utf-8')
                self.result_path = settings_dir
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, self._t["title"], self._t["error_folder"].format(e=e))
    
    def _activate_debug(self):
        """Developer debug mode — nothing saved to disk, nothing persists."""
        global _DEBUG_MODE
        _DEBUG_MODE = True
        self.result_path = None
        self.accept()
    
    def reject(self):
        """Prevent closing with Escape — must choose a folder."""
        pass
    
    def run(self):
        self.exec()
        return self.result_path


def ask_config_location(lang):
    """Show config location dialog on first run."""
    pointer_file = get_pointer_file()
    
    # Already configured — skip
    if pointer_file.exists():
        return
    
    dlg = ConfigLocationDialog(lang)
    dlg.run()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # Windows-specific setup — MUST be done BEFORE QApplication
    if sys.platform == 'win32':
        try:
            from ctypes import windll
            # NOTE: Do NOT call SetProcessDpiAwareness() here — Qt6/PySide6
            # already sets DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 internally.
            # Calling it manually causes a "SetProcessDpiAwarenessContext() failed" warning.
            # AppUserModelID — proper taskbar icon grouping
            windll.shell32.SetCurrentProcessExplicitAppUserModelID("Aura Video Downloader")
        except Exception:
            pass
    
    app = QApplication(sys.argv)
    app.setApplicationName("Aura Video Downloader")
    app.setStyle("Fusion")
    
    # App icon — used for all windows, taskbar, and tray
    _icon_path = resource_path("app.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))
    
    # 1. Language selection
    lang_dlg = LanguageSelector()
    lang = lang_dlg.run()
    if not lang:
        sys.exit(0)
    
    # 2. Config location (FIRST! — must know WHERE to save before saving anything)
    #    Shows dialog only when pointer.txt doesn't exist (first run or after reset)
    ask_config_location(lang)
    
    # 3. Theme: first run (no general.json) → show picker, otherwise → load saved
    general_config = get_settings_dir() / "general.json"
    if not general_config.exists():
        theme_dlg = ThemeSelector(lang)
        theme_id = theme_dlg.run()
        if not theme_id:
            sys.exit(0)
    else:
        theme_id = get_theme_config()
    
    # 4. Platform selection
    plat_dlg = PlatformSelector(lang, theme_id)
    platform = plat_dlg.run()
    if not platform:
        sys.exit(0)
    
    # 5. Main window — loop allows platform switching without full restart
    while True:
        window = AuraDownloader(lang=lang, platform=platform, theme_id=theme_id)
        window.show()
        app.exec()
        
        # Check if user requested a platform switch
        next_platform = getattr(window, '_next_platform', None)
        if not next_platform:
            break
        platform = next_platform
    
    sys.exit(0)


if __name__ == "__main__":
    main()
