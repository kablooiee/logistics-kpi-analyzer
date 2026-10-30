# -*- coding: utf-8 -*-
"""
Менеджер настроек приложения на базе JSON-файла.
Экспортирует `Settings` и singleton-функцию `get_settings`.
"""

import copy
import json
import os
import shutil


# ============================================================
# Константы и пути
# ============================================================

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SETTINGS_PATH = os.path.join(_ROOT_DIR, 'settings.json')
_SETTINGS_BAK_PATH = os.path.join(_ROOT_DIR, 'settings.json.bak')
_NOTES_DIR = os.path.join(_ROOT_DIR, 'data', 'notes')

DEFAULT_SETTINGS = {
    'thresholds': {
        'margin_pct_critical': 20.0,
        'margin_pct_warning': 25.0,
        'load_delay_hours_critical': 4.0,
        'load_delay_hours_warning': 2.0,
        'success_rate_critical': 70.0,
        'success_rate_warning': 80.0,
        'cancel_rate_critical': 15.0,
    },
    'ui': {
        'dark_theme': False,
        'window_width': 1200,
        'window_height': 800,
        'font_size': 11,
    },
    'analysis': {
        'max_rows': 100000,
        'anomalies_limit': 10,
    },
}


# ============================================================
# Класс Settings
# ============================================================

class Settings:
    """Чтение и запись файла настроек `settings.json`."""

    def __init__(self):
        self._data = copy.deepcopy(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        """Читает настройки из файла, создавая его при отсутствии."""
        if not os.path.isfile(_SETTINGS_PATH):
            self._data = copy.deepcopy(DEFAULT_SETTINGS)
            self.save(self._data)
            return copy.deepcopy(self._data)

        try:
            with open(_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                raw = f.read()
            self._data = json.loads(raw)
            return copy.deepcopy(self._data)
        except json.JSONDecodeError as e:
            print(
                f'Warning: settings.json is invalid JSON ({e!s}). '
                f'Backing up to settings.json.bak and recreating defaults.'
            )
            try:
                shutil.copy2(_SETTINGS_PATH, _SETTINGS_BAK_PATH)
            except OSError as copy_err:
                print(f'Warning: could not create settings backup: {copy_err!s}')
            self._data = copy.deepcopy(DEFAULT_SETTINGS)
            self.save(self._data)
            return copy.deepcopy(self._data)

    def save(self, settings_dict=None):
        """Сохраняет настройки в `settings.json`."""
        if settings_dict is not None:
            self._data = copy.deepcopy(settings_dict)
        with open(_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, path, default=None):
        """Возвращает значение по пути вида `thresholds.margin_pct_critical`."""
        if not path or not isinstance(path, str):
            return default
        cur = self._data
        for key in path.split('.'):
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
        return cur

    def set(self, path, value):
        """Устанавливает значение по пути и сразу сохраняет файл."""
        if not path or not isinstance(path, str):
            return
        keys = path.split('.')
        cur = self._data
        for key in keys[:-1]:
            nxt = cur.get(key)
            if not isinstance(nxt, dict):
                cur[key] = {}
            cur = cur[key]
        cur[keys[-1]] = value
        self.save()

    def reset_to_defaults(self):
        """Сбрасывает настройки к значениям по умолчанию."""
        self._data = copy.deepcopy(DEFAULT_SETTINGS)
        self.save(self._data)

    def save_notes(self, file_hash: str, notes: str):
        """Сохраняет заметки аналитика в data/notes/<file_hash>.json."""
        if not file_hash:
            return
        os.makedirs(_NOTES_DIR, exist_ok=True)
        safe_hash = ''.join(ch for ch in str(file_hash) if ch.isalnum() or ch in ('-', '_'))
        if not safe_hash:
            return
        path = os.path.join(_NOTES_DIR, f'{safe_hash}.json')
        payload = {
            'file_hash': safe_hash,
            'notes': notes or '',
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def load_notes(self, file_hash: str) -> str:
        """Загружает заметки аналитика по хешу или возвращает пустую строку."""
        if not file_hash:
            return ''
        safe_hash = ''.join(ch for ch in str(file_hash) if ch.isalnum() or ch in ('-', '_'))
        if not safe_hash:
            return ''
        path = os.path.join(_NOTES_DIR, f'{safe_hash}.json')
        if not os.path.isfile(path):
            return ''
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return str(data.get('notes', '') or '')
        except Exception:
            return ''


# ============================================================
# Singleton-доступ
# ============================================================

_instance = None


def get_settings():
    """Возвращает singleton-экземпляр `Settings`."""
    global _instance
    if _instance is None:
        _instance = Settings()
    return _instance
