# -*- coding: utf-8 -*-
"""Точка входа в программу анализа KPI логистики."""

import sys

from ui.main_window import main as ui_main


def main() -> None:
    """Запуск приложения."""
    try:
        ui_main()
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()