# -*- coding: utf-8 -*-
"""
Главное окно PyQt5 приложения анализа отчётов.
Экспортирует `MainWindow` и функцию `main()` для запуска приложения.
"""

import hashlib
import json
import os
import shutil
import sys
from datetime import date, datetime, time

from PyQt5.QtCore import QDate
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStackedWidget,
    QStatusBar,
)

from core.analyzer import Analyzer
from core.reports import compare_periods
from core.settings import get_settings
from ui.dialogs import FiltersDialog
from ui.pages.analysis import AnalysisPage
from ui.pages.anomalies import AnomaliesPage
from ui.pages.comparison import ComparisonPage
from ui.pages.data import DataPage
from ui.pages.funnel import FunnelPage
from ui.pages.help import HelpPage
from ui.pages.home import HomePage
from ui.pages.recommendations import RecommendationsPage
from ui.pages.search import SearchPage
from ui.pages.settings import SettingsPage
from ui.helpers import markdown_to_html, to_qdate_safe
from ui.helpers import ParseWorker


class MainWindow(QMainWindow):
    """Главное окно приложения анализа отчётов."""

    PAGES = {
        'home': HomePage,
        'data': DataPage,
        'analysis': AnalysisPage,
        'comparison': ComparisonPage,
        'search': SearchPage,
        'anomalies': AnomaliesPage,
        'funnel': FunnelPage,
        'recommendations': RecommendationsPage,
        'settings': SettingsPage,
        'help': HelpPage,
    }
    DATA_PAGES = (
        'analysis',
        'comparison',
        'search',
        'anomalies',
        'recommendations',
    )
    ANALYSIS_KEYS = ('financial', 'operational', 'quality', 'timeliness')

    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            * { font-family: 'Segoe UI', Arial, sans-serif; }
            QMainWindow, QWidget { font-size: 11pt; color: #2c3e50; }
            QLabel { font-size: 11pt; }
            QGroupBox {
                font-size: 11pt; font-weight: 600; border: 1px solid #d0d6dc;
                border-radius: 6px; margin-top: 14px; padding: 10px 8px 8px 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #34495e;
            }
            QLineEdit, QComboBox, QDateEdit, QSpinBox {
                font-size: 11pt; padding: 5px 8px; border: 1px solid #d0d6dc;
                border-radius: 4px; min-height: 24px; background: white;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color: #3498db; }
            QPushButton {
                font-size: 11pt; font-weight: 500; padding: 8px 14px; border-radius: 6px;
                min-height: 26px; background-color: #ecf0f1; color: #2c3e50; border: 1px solid #d0d6dc;
            }
            QPushButton:hover { background-color: #dde4e8; border-color: #c1ccd6; }
            QPushButton:disabled { background-color: #f4f6f6; color: #95a5a6; }
            QPushButton#primaryButton { background-color: #3498db; color: white; border: none; }
            QPushButton#primaryButton:hover { background-color: #2980b9; }
            QWidget#homePanel, QWidget#tilePanel {
                background-color: #ffffff;
                border: 1px solid #e4e9ee;
                border-radius: 12px;
            }
            QPushButton#tileButton {
                background-color: #ffffff; color: #2c3e50; border: 1px solid #d0d6dc;
                border-radius: 10px; font-size: 13pt; font-weight: 600;
                padding: 12px 16px; text-align: center;
            }
            QPushButton#tileButton:hover {
                border: 2px solid #3498db; background-color: #f4f9ff;
            }
            QPushButton#tileButton:pressed {
                background-color: #ebf4fe;
            }
            QPushButton#navButton {
                background-color: #eef6ff;
                color: #2c6db2;
                border: 1px solid #b7d4f3;
                border-radius: 8px;
                font-size: 11pt;
                font-weight: 600;
                padding: 7px 14px;
                text-align: left;
            }
            QPushButton#navButton:hover {
                background-color: #dceeff;
                border-color: #93c2f0;
                color: #235f9a;
            }
            QPushButton#sectionButton {
                background-color: #ecf0f1;
                color: #2c3e50;
                border: none;
                border-radius: 5px;
                padding: 14px;
                text-align: left;
                font-size: 12pt;
                font-weight: 500;
            }
            QPushButton#sectionButton:hover {
                background-color: #d5dbdb;
            }
            QPushButton#sectionButton:checked {
                background-color: #3498db;
                color: white;
            }
            QTextEdit { font-size: 11pt; border: 1px solid #d0d6dc; border-radius: 4px; background: white; padding: 8px; }
            QProgressBar {
                border: 1px solid #d0d6dc; border-radius: 3px; text-align: center;
                font-size: 10pt; height: 18px; background: #ecf0f1;
            }
            QProgressBar::chunk { background-color: #3498db; border-radius: 2px; }
            QStatusBar { font-size: 10pt; background: #f4f6f6; border-top: 1px solid #d0d6dc; }
        """)

        self.setWindowTitle('Анализатор отчётов')
        self.resize(1400, 900)
        self.setMinimumSize(1100, 700)

        self.file_path = None
        self.json_path = None
        self.processed_data = None
        self._parse_worker = None
        self.filters = {}
        self.filter_options = {}
        self.filter_dates = (None, None)
        self.analyzer = None
        self.charts = None
        self._cached_filter_signature = None
        self.file_hash = None
        self.file_info = ''
        os.makedirs('exports', exist_ok=True)

        self.setStatusBar(QStatusBar())
        self.status_label = QLabel('Готово')
        self.status_progress = QProgressBar()
        self.status_progress.setFixedWidth(220)
        self.status_progress.setVisible(False)
        self.status_progress.setTextVisible(True)
        self.status_progress.setRange(0, 100)
        self.status_progress.setValue(0)
        self.statusBar().addPermanentWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.status_progress)

        self.init_ui()

    def init_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.pages = {}

        for key, page_cls in self.PAGES.items():
            self.pages[key] = page_cls(self)

        for page in self.pages.values():
            self.stack.addWidget(page)

        self.refresh_home()
        self._set_data_loaded_ui(False)
        self._update_filters_indicator()
        self.show_page('home')

    def show_page(self, name: str):
        page = self.pages.get(name)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        on_show = getattr(page, 'on_show', None)
        if callable(on_show):
            on_show()

    def _analysis_max_rows(self):
        return int(get_settings().get('analysis.max_rows', 100000))

    def _anomalies_limit(self):
        return int(get_settings().get('analysis.anomalies_limit', 10))

    def _active_filters_count(self):
        f = self.filters or {}
        return sum(1 for key in ('date_from', 'date_to', 'branch', 'manager', 'carrier_type') if f.get(key))

    def _update_filters_indicator(self):
        active = self._active_filters_count()
        label = self.pages['data'].filters_indicator
        if active > 0:
            label.setText(f'Фильтры: применены ({active})')
            label.setStyleSheet('color: #3498db; font-weight: 600;')
        else:
            label.setText('Фильтры: нет')
            label.setStyleSheet('color: #7f8c8d; font-weight: 400;')

    def _set_data_loaded_ui(self, loaded: bool):
        self.pages['data'].btn_save.setEnabled(loaded)
        self.pages['data'].btn_statistics.setEnabled(loaded)
        self.pages['data'].btn_file_stats.setEnabled(loaded)
        self.pages['data'].btn_filters.setEnabled(loaded)
        for key in self.DATA_PAGES:
            self.pages[key].set_data_loaded(loaded)
        self.pages['home'].set_tiles_enabled(loaded)

    def _has_data(self) -> bool:
        return bool(self.json_path and self.processed_data)

    def _need_data(self, text='Сначала загрузите данные (JSON).') -> bool:
        if self.json_path:
            return False
        QMessageBox.warning(self, 'Предупреждение', text)
        return True

    def _reset_cache(self):
        self._cached_filter_signature = None
        self.analyzer = None
        self.charts = None

    def _clear_reports(self):
        # После новой загрузки сбрасываем вычисленные экраны, чтобы не показывать старые данные.
        for key in ('analysis', 'comparison', 'search', 'anomalies'):
            self.pages[key].results_text.clear()

    def _set_filter_dates(self, dmin, dmax):
        qd_min = to_qdate_safe(dmin)
        qd_max = to_qdate_safe(dmax)
        if qd_min and qd_max:
            if qd_min > qd_max:
                qd_min, qd_max = qd_max, qd_min
            self.filter_dates = (qd_min, qd_max)
            return
        self.filter_dates = (None, None)

    @staticmethod
    def _escape_md(value) -> str:
        return str(value if value is not None else '').replace('|', '\\|')

    @staticmethod
    def _fmt_money(value) -> str:
        if value is None:
            return '—'
        try:
            return f"{float(value):,.0f}".replace(',', ' ') + ' ₽'
        except (TypeError, ValueError):
            return '—'

    @staticmethod
    def _fmt_pct(value) -> str:
        if value is None:
            return '—'
        try:
            return f'{float(value):.1f}%'
        except (TypeError, ValueError):
            return '—'

    @staticmethod
    def _fmt_float(value) -> str:
        if value is None:
            return '—'
        try:
            return f'{float(value):.1f}'
        except (TypeError, ValueError):
            return '—'

    def _stats_md(self, analyzer, stats: dict) -> str:
        opts = analyzer.get_filter_options()
        dmin = opts.get('date_min')
        dmax = opts.get('date_max')
        period = '—'
        if dmin and dmax:
            period = f"{dmin.strftime('%d.%m.%Y')} — {dmax.strftime('%d.%m.%Y')}"

        total = int(stats.get('total_requests', 0))
        successful = int(stats.get('successful_requests', 0))
        success_pct = float(stats.get('success_rate', 0.0))
        avg_km = float(stats.get('avg_km', 0.0))
        income = float(stats.get('total_income', 0.0))
        expenses = float(stats.get('total_expenses', 0.0))
        profit = float(stats.get('total_profit', income - expenses))
        unique_branches = int(stats.get('unique_branches', 0))
        branch_stats = stats.get('branch_stats') or {}
        manager_col = analyzer.cols.get('manager')
        unique_managers = int(analyzer.df_filtered[manager_col].nunique()) if manager_col else 0

        lines = [
            '# Общая статистика файла',
            '',
            f'- **Всего заявок:** {total}',
            f'- **Период данных:** {period}',
            f'- **Уникальных филиалов:** {unique_branches}',
            f'- **Уникальных менеджеров:** {unique_managers}',
            f'- **Общая выручка:** {income:,.0f} ₽'.replace(',', ' '),
            f'- **Общие затраты:** {expenses:,.0f} ₽'.replace(',', ' '),
            f'- **Общая прибыль:** {profit:,.0f} ₽'.replace(',', ' '),
            f'- **Успешных заявок:** {successful} ({success_pct:.1f}%)',
            f'- **Средний пробег:** {avg_km:.1f} км',
        ]

        if branch_stats:
            lines.extend(['', '## Топ филиалов по количеству заявок'])
            for branch, count in list(branch_stats.items())[:10]:
                lines.append(f'- **{branch}:** {count}')

        top_managers = stats.get('top_managers') or {}
        if top_managers:
            lines.extend(['', '## Топ менеджеров'])
            for manager, count in top_managers.items():
                lines.append(f'- **{manager}:** {count}')
        return '\n'.join(lines)

    def _filters_signature(self):
        f = self.filters or {}
        return (
            f.get('date_from').isoformat() if f.get('date_from') else None,
            f.get('date_to').isoformat() if f.get('date_to') else None,
            f.get('branch'),
            f.get('manager'),
            f.get('carrier_type'),
        )

    def _refresh_analyzer(self):
        if not self.json_path:
            self.analyzer = None
            self.charts = None
            self._cached_filter_signature = None
            return None
        sig = self._filters_signature()
        # Пересчитываем анализатор только если фильтры поменялись.
        if self.analyzer is None or self._cached_filter_signature != sig:
            analyzer = Analyzer(self.json_path, max_rows=self._analysis_max_rows())
            if self.filters:
                analyzer.apply_filters(self.filters)
            self.analyzer = analyzer
            self.charts = None
            self._cached_filter_signature = sig
        return self.analyzer

    def _calculate_file_hash(self):
        if not self.processed_data:
            return None
        file_name = os.path.basename(self.file_path or self.json_path or '')
        records = self.processed_data.get('records', []) or []
        records_count = len(records)
        first_date = ''
        if self.filter_options:
            dmin = self.filter_options.get('date_min')
            if dmin:
                first_date = dmin.strftime('%Y-%m-%d')
        if not first_date and records:
            first_rec = records[0]
            for key in ('datetime', 'Дата подачи заявки', 'Дата  загрузки', 'Дата загрузки'):
                if first_rec.get(key):
                    first_date = str(first_rec.get(key))
                    break
        payload = f'{file_name}|{first_date}|{records_count}'
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]

    def refresh_home(self):
        if not self._has_data():
            self.pages['home'].update_file_info(False)
            self.pages['home'].update_cards(None)
            return
        max_rows = int(get_settings().get('analysis.max_rows', 100000))
        analyzer = self.analyzer
        if analyzer is None or int(getattr(analyzer, 'max_rows', 0) or 0) != max_rows:
            analyzer = Analyzer(self.json_path, max_rows=max_rows)
            if self.filters:
                analyzer.apply_filters(self.filters)
            self.analyzer = analyzer
            self.charts = None
            self._cached_filter_signature = self._filters_signature()
        file_name = os.path.basename(self.file_path or self.json_path)
        records_count = len(self.processed_data.get('records', []) or [])
        analyzed_count = len(analyzer.df) if analyzer is not None and analyzer.df is not None else 0
        period = '—'
        dmin = self.filter_options.get('date_min') if self.filter_options else None
        dmax = self.filter_options.get('date_max') if self.filter_options else None
        if dmin and dmax:
            period = f"{dmin.strftime('%d.%m.%Y')} — {dmax.strftime('%d.%m.%Y')}"
        self.pages['home'].update_file_info(True, file_name, period, records_count, analyzed_count)
        self.pages['home'].update_cards(analyzer)

    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            'Открыть файл',
            '',
            'Поддерживаемые файлы (*.xlsx *.xls *.json);;Excel (*.xlsx *.xls);;JSON (*.json)',
        )
        if not filepath:
            return

        ext = os.path.splitext(filepath)[1].lower()
        if ext in ('.xlsx', '.xls'):
            self._start_excel_parsing(filepath)
            return
        if ext == '.json':
            self._load_json_file(filepath)
            return
        QMessageBox.warning(self, 'Ошибка', 'Неподдерживаемый формат файла.')

    def _start_excel_parsing(self, filepath):
        if self._parse_worker is not None and self._parse_worker.isRunning():
            return

        self.file_path = filepath
        self.status_label.setText('Загрузка файла...')
        self.status_progress.setVisible(True)
        self.status_progress.setRange(0, 0)
        self.status_progress.setValue(0)
        self.status_progress.setFormat('Подготовка...')
        self.pages['data'].btn_open.setEnabled(False)

        worker = ParseWorker(filepath, sheet_name=None, parent=self)
        self._parse_worker = worker
        worker.progress.connect(self._on_parse_progress)
        worker.finished_ok.connect(self._on_parse_finished_ok)
        worker.failed.connect(self._on_parse_failed)
        worker.finished.connect(self._on_parse_worker_finished)
        worker.start()

    def _on_parse_progress(self, current_row, total_rows):
        if total_rows > 0:
            self.status_label.setText(f'Парсинг строк: {current_row} из {total_rows}')
            self.status_progress.setRange(0, total_rows)
            self.status_progress.setValue(current_row)
            self.status_progress.setFormat(f'{current_row} / {total_rows}')

    def _on_parse_finished_ok(self, json_result):
        json_dir = 'data'
        os.makedirs(json_dir, exist_ok=True)
        source_name = os.path.splitext(os.path.basename(self.file_path or 'converted'))[0]
        # Служебные символы из имени убираем, чтобы сохранение не падало на разных ОС.
        safe_name = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in source_name)
        safe_name = safe_name.strip('_') or 'converted'
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.json_path = os.path.join(json_dir, f'{safe_name}_{stamp}.json')
        with open(self.json_path, 'w', encoding='utf-8') as f:
            f.write(json_result)

        self.processed_data = json.loads(json_result)
        metadata = self.processed_data.get('metadata', {})
        records = self.processed_data.get('records', [])
        actions = self.processed_data.get('actions', [])

        stats_report = self.generate_parsing_stats(metadata, records, actions)
        self.file_info = stats_report
        self.pages['data'].results_text.setHtml(markdown_to_html(stats_report))
        self._clear_reports()

        self.filters = {}
        self._set_data_loaded_ui(True)
        self.populate_filter_options()
        self._reset_cache()
        self._refresh_analyzer()
        self.file_hash = self._calculate_file_hash()
        self.status_progress.setVisible(False)
        filename = os.path.basename(self.file_path) if self.file_path else os.path.basename(self.json_path)
        records_count = metadata.get('total_records', 0)
        self.pages['data'].info_label.setText(f'Файл: {filename} | Записей: {records_count}')
        self.status_label.setText(f'Файл: {filename} | Записей: {records_count}')
        self.refresh_home()

        QMessageBox.information(
            self,
            'Успех',
            (
                f'Файл успешно обработан!\n'
                f'Обработано {records_count} записей.\n'
                f'JSON сохранён: {self.json_path}'
            ),
        )

    def _on_parse_failed(self, error_text):
        self.status_progress.setVisible(False)
        self.status_label.setText('Готово')
        QMessageBox.warning(self, 'Ошибка', error_text)

    def _on_parse_worker_finished(self):
        self.pages['data'].btn_open.setEnabled(True)
        if not self.json_path:
            self.status_label.setText('Готово')
        self._parse_worker = None

    def populate_filter_options(self):
        if self._need_data():
            return
        self._update_filters_indicator()
        try:
            tmp = Analyzer(self.json_path, max_rows=self._analysis_max_rows())
            self.filter_options = tmp.get_filter_options() or {}
        except Exception:
            return

        dmin, dmax = self.filter_options.get('date_min'), self.filter_options.get('date_max')
        self._set_filter_dates(dmin, dmax)

    def open_filters_dialog(self):
        if self._need_data():
            return
        try:
            analyzer = Analyzer(self.json_path, max_rows=self._analysis_max_rows())
            options = analyzer.get_filter_options()
            dlg = FiltersDialog(options, self.filters or {}, self)
            if dlg.exec_() != dlg.Accepted:
                return
            chosen = dlg.get_filters()
            if any(chosen.get(k) is not None for k in ('date_from', 'date_to', 'branch', 'manager', 'carrier_type')):
                self.filters = chosen
            else:
                self.filters = {}
            self._reset_cache()
            self._refresh_analyzer()
            self._update_filters_indicator()
            self.refresh_home()
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось применить фильтры: {e}')

    def _normalize_loaded_json_data(self, raw):
        if isinstance(raw, list):
            # Если пришёл голый массив, приводим его к формату records/actions/metadata.
            records = [r for r in raw if isinstance(r, dict)]
            return {
                'records': records,
                'actions': [],
                'metadata': {
                    'total_records': len(records),
                    'data_summary': {'total_columns': len(records[0]) if records else 0},
                },
            }

        if isinstance(raw, dict):
            if isinstance(raw.get('records'), list):
                data = dict(raw)
                data.setdefault('actions', [])
                data.setdefault('metadata', {})
                data['metadata'].setdefault('total_records', len(data.get('records') or []))
                data['metadata'].setdefault(
                    'data_summary',
                    {'total_columns': len((data.get('records') or [{}])[0]) if data.get('records') else 0},
                )
                return data

            for key in ('data', 'items', 'rows', 'result'):
                if isinstance(raw.get(key), list):
                    records = [r for r in raw.get(key) if isinstance(r, dict)]
                    return {
                        'records': records,
                        'actions': [],
                        'metadata': {
                            'total_records': len(records),
                            'data_summary': {'total_columns': len(records[0]) if records else 0},
                        },
                    }

        raise ValueError(
            'Неподдерживаемая структура JSON. Ожидается объект с ключом "records" '
            'или массив записей.'
        )

    def _load_json_file(self, filepath):
        last_error = None
        raw_data = None
        for enc in ('utf-8', 'utf-8-sig', 'cp1251'):
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    raw_data = json.load(f)
                break
            except Exception as e:
                last_error = e
        if raw_data is None:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось открыть JSON: {last_error}')
            self.status_label.setText('Готово')
            return

        try:
            self.processed_data = self._normalize_loaded_json_data(raw_data)
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось распознать структуру JSON: {e}')
            self.status_label.setText('Готово')
            return

        self.file_path = filepath
        self.json_path = filepath
        self.filters = {}
        self._set_data_loaded_ui(True)
        self.populate_filter_options()
        self._reset_cache()
        self._refresh_analyzer()
        self.file_hash = self._calculate_file_hash()

        metadata = self.processed_data.get('metadata', {}) or {}
        records = self.processed_data.get('records', []) or []
        actions = self.processed_data.get('actions', []) or []
        self.file_info = self.generate_parsing_stats(metadata, records, actions)
        self.pages['data'].results_text.setHtml(markdown_to_html(self.file_info))

        records_count = len(self.processed_data.get('records', []) or [])
        filename = os.path.basename(filepath)
        self.pages['data'].info_label.setText(f'Файл: {filename} | Записей: {records_count}')
        self.status_label.setText(f'Файл: {filename} | Записей: {records_count}')
        self.status_progress.setVisible(False)
        self.refresh_home()

    def show_file_statistics(self):
        if self._need_data():
            return
        if not self.file_info:
            metadata = self.processed_data.get('metadata', {}) if self.processed_data else {}
            records = self.processed_data.get('records', []) if self.processed_data else []
            actions = self.processed_data.get('actions', []) if self.processed_data else []
            self.file_info = self.generate_parsing_stats(metadata, records, actions)
        self.pages['data'].results_text.setHtml(markdown_to_html(self.file_info))
        self.show_page('data')

    def show_statistics(self):
        if self._need_data():
            return
        try:
            analyzer = self._refresh_analyzer()
            if analyzer is None:
                return

            stats = analyzer.get_statistics()
            report = self._stats_md(analyzer, stats)
            self.pages['data'].results_text.setHtml(markdown_to_html(report))
            self.show_page('data')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Ошибка при формировании статистики: {e}')

    def setup_comparison_dates(self):
        page = self.pages['comparison']
        today = QDate.currentDate()
        min_qd, max_qd = self.filter_dates
        for w in (page.a_from, page.a_to, page.b_from, page.b_to):
            if min_qd and max_qd:
                w.setMinimumDate(min_qd)
                w.setMaximumDate(max_qd)
            else:
                w.clearMinimumDate()
                w.clearMaximumDate()
                w.setDate(today)
        if min_qd and max_qd:
            total_days = min_qd.daysTo(max_qd)
            if total_days <= 0:
                page.a_from.setDate(min_qd)
                page.a_to.setDate(max_qd)
                page.b_from.setDate(min_qd)
                page.b_to.setDate(max_qd)
            else:
                mid = min_qd.addDays(total_days // 2)
                page.a_from.setDate(min_qd)
                page.a_to.setDate(mid)
                b_start = mid.addDays(1) if mid < max_qd else mid
                page.b_from.setDate(b_start)
                page.b_to.setDate(max_qd)

    def compare_periods_click(self):
        if self._need_data('Сначала загрузите JSON.'):
            return
        period_a, period_b = self.pages['comparison'].get_periods()
        try:
            report = compare_periods(
                self.json_path,
                period_a,
                period_b,
                base_filters=self.filters or {},
            )
            self.pages['comparison'].results_text.setHtml(markdown_to_html(report))
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', str(e))

    def search_click(self):
        if self._need_data():
            return
        page = self.pages['search']
        query = page.search_input.text().strip()
        if len(query) < 2:
            page.info_label.setText('Введите минимум 2 символа')
            page.info_label.setStyleSheet('color: #c0392b;')
            page.results_text.clear()
            return

        try:
            analyzer = self._refresh_analyzer()
            rows = analyzer.search(query, limit=page.search_limit)
        except Exception as e:
            page.info_label.setText(f'Ошибка поиска: {e}')
            page.info_label.setStyleSheet('color: #c0392b;')
            return

        if rows:
            page.info_label.setText(f'Найдено {len(rows)} результатов')
            page.info_label.setStyleSheet('color: #2e7d32;')
        else:
            page.info_label.setText('Ничего не найдено')
            page.info_label.setStyleSheet('color: #c0392b;')

        lines = [
            '# Поиск заявок',
            '',
            f'Запрос: **{self._escape_md(query)}**',
            '',
            '| № заявки | Дата | Филиал | Менеджер | Сумма | Маржа | Статус |',
            '|---|---|---|---|---:|---:|---|',
        ]
        for r in rows:
            lines.append(
                f"| {self._escape_md(r.get('case_id', ''))} "
                f"| {self._escape_md(r.get('Дата подачи заявки', ''))} "
                f"| {self._escape_md(r.get('Филиал (заказчик)', ''))} "
                f"| {self._escape_md(r.get('Менеджер', ''))} "
                f"| {self._fmt_money(r.get('Сумма заказчика'))} "
                f"| {self._fmt_money(r.get('Маржа'))} "
                f"| {self._escape_md(r.get('Статус', ''))} |"
            )
        if len(rows) == page.search_limit:
            lines.extend(['', f'Показаны первые {page.search_limit}. Уточните запрос.'])
        page.results_text.setHtml(markdown_to_html('\n'.join(lines)))

    def run_analysis_choice(self, choice: str):
        if self._need_data():
            return
        if choice in self.ANALYSIS_KEYS:
            self.show_page('analysis')
            self.pages['analysis'].show_section(choice)

    def _anomalies_md(self, analyzer, limit_per_category=10):
        thresholds = get_settings().get('thresholds', {}) or {}
        anomalies = analyzer.find_anomalies(thresholds, limit_per_category=limit_per_category)
        category_meta = [
            ('low_margin', '🔴 Низкая маржинальность'),
            ('loss', '🔴 Убыточные заявки'),
            ('late_load', '🔴 Опоздания на погрузку'),
            ('long_processing', '🔴 Долгая обработка'),
            ('high_empty_km', '🔴 Высокий холостой пробег'),
            ('cancelled_by_us', '🔴 Отмены по нашей вине'),
        ]

        total = sum(len(anomalies.get(k, [])) for k, _ in category_meta)
        non_empty = sum(1 for k, _ in category_meta if anomalies.get(k))

        lines = [
            '# Проблемные заявки',
            '',
            (
                f'Найдено **{total}** в **{non_empty}** категориях. '
                f'Пороги: margin_pct_critical={thresholds.get("margin_pct_critical", 20.0)}, '
                f'load_delay_hours_critical={thresholds.get("load_delay_hours_critical", 4.0)}.'
            ),
            '',
        ]

        for cat_key, title in category_meta:
            items = anomalies.get(cat_key, []) or []
            if not items:
                continue
            lines.append(f'## {title} ({len(items)})')
            if cat_key in ('low_margin', 'loss'):
                lines.append('| № заявки | Дата | Филиал | Менеджер | Сумма | Маржа | Маржинальность |')
                lines.append('|---|---|---|---|---:|---:|---:|')
            elif cat_key == 'late_load':
                lines.append('| № заявки | Дата | Филиал | Менеджер | Сумма | Задержка, ч |')
                lines.append('|---|---|---|---|---:|---:|')
            elif cat_key == 'long_processing':
                lines.append('| № заявки | Дата | Филиал | Менеджер | Сумма | Длительность, ч |')
                lines.append('|---|---|---|---|---:|---:|')
            elif cat_key == 'high_empty_km':
                lines.append('| № заявки | Дата | Филиал | Менеджер | Сумма | Холостой, км | Доля холостого, % |')
                lines.append('|---|---|---|---|---:|---:|---:|')
            elif cat_key == 'cancelled_by_us':
                lines.append('| № заявки | Дата | Филиал | Менеджер | Сумма | Причина отмены |')
                lines.append('|---|---|---|---|---:|---|')
            for it in items:
                case_id = self._escape_md(it.get('case_id', ''))
                date_val = self._escape_md(it.get('дата', ''))
                branch = self._escape_md(it.get('филиал', ''))
                manager = self._escape_md(it.get('менеджер', ''))
                sum_val = self._fmt_money(it.get('сумма'))
                if cat_key in ('low_margin', 'loss'):
                    lines.append(
                        f"| {case_id} | {date_val} | {branch} | {manager} "
                        f"| {sum_val} | {self._fmt_money(it.get('маржа'))} | {self._fmt_pct(it.get('маржинальность_pct'))} |"
                    )
                elif cat_key == 'late_load':
                    lines.append(
                        f"| {case_id} | {date_val} | {branch} | {manager} "
                        f"| {sum_val} | {self._fmt_float(it.get('задержка_погрузки_ч'))} |"
                    )
                elif cat_key == 'long_processing':
                    lines.append(
                        f"| {case_id} | {date_val} | {branch} | {manager} "
                        f"| {sum_val} | {self._fmt_float(it.get('длительность_ч'))} |"
                    )
                elif cat_key == 'high_empty_km':
                    lines.append(
                        f"| {case_id} | {date_val} | {branch} | {manager} "
                        f"| {sum_val} | {self._fmt_float(it.get('холостой_пробег_км'))} | {self._fmt_float(it.get('холостой_пробег_pct'))} |"
                    )
                elif cat_key == 'cancelled_by_us':
                    reason = self._escape_md(it.get('причина_отмены', '') or '—')
                    lines.append(
                        f"| {case_id} | {date_val} | {branch} | {manager} "
                        f"| {sum_val} | {reason} |"
                    )
            lines.append('')

        if total == 0:
            lines.append('Проблемные заявки по заданным правилам не найдены.')
        return '\n'.join(lines)

    def show_anomalies(self):
        if self._need_data():
            return
        try:
            self.show_page('anomalies')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Ошибка выполнения анализа: {e}')

    def save_file_as(self):
        if self._need_data('Нет данных для сохранения!'):
            return

        default_name = f'report_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            'Сохранить JSON',
            default_name,
            'JSON (*.json)',
        )
        if not filepath:
            return
        if not filepath.lower().endswith('.json'):
            filepath += '.json'

        try:
            shutil.copyfile(self.json_path, filepath)
            self.status_label.setText(f'Сохранено: {os.path.basename(filepath)}')
            QMessageBox.information(self, 'Успех', f'Файл успешно сохранен:\n{filepath}')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Ошибка при сохранении файла: {e}')

    def generate_parsing_stats(self, metadata, records, actions):
        report = [
            "# СТАТИСТИКА ДАННЫХ",
            "",
            "## Общая информация",
            f"- **Всего записей:** {metadata.get('total_records', 0)}",
            f"- **Всего столбцов:** {metadata.get('data_summary', {}).get('total_columns', 0)}",
        ]
        text_fields = 0
        numeric_fields = len(metadata.get('columns_detected', {}).get('numeric_columns', []))
        date_fields = 0
        boolean_fields = 0
        if records:
            sample_record = records[0]
            for key, value in sample_record.items():
                if isinstance(value, str) and len(str(value)) > 10:
                    text_fields += 1
                elif isinstance(value, (int, float)):
                    numeric_fields += 1
                elif 'True' in str(value) or 'False' in str(value):
                    boolean_fields += 1
                elif 'date' in key.lower() or 'время' in key.lower():
                    date_fields += 1
        report.extend([
            "",
            "## Структура данных",
            f"- **Текстовые поля:** {text_fields} (адреса, названия, описания)",
            f"- **Числовые поля:** {numeric_fields} (суммы, расстояния, количества)",
            f"- **Логические поля:** {boolean_fields} (флаги, статусы)",
            f"- **Поля дат/времени:** {date_fields} (даты операций, загрузки, разгрузки)",
        ])
        numeric_cols = metadata.get('columns_detected', {}).get('numeric_columns', [])
        if numeric_cols:
            report.append("")
            report.append("## Финансовые показатели")
            for col in numeric_cols:
                report.append(f"- {col}")
        branch_customer_stats = {}
        for record in records:
            branch = record.get('Филиал (заказчик)', 'Не указан')
            branch_customer_stats[branch] = branch_customer_stats.get(branch, 0) + 1
        if branch_customer_stats:
            report.append("")
            report.append("## Филиалы заказчиков")
            sorted_branches = sorted(branch_customer_stats.items(), key=lambda x: x[1], reverse=True)
            for branch, count in sorted_branches[:10]:
                report.append(f"- **{branch}:** {count} заявок")
        manager_stats = {}
        for record in records:
            manager = record.get('Менеджер', 'Не указан')
            if manager and manager != 'Не указан':
                manager_stats[manager] = manager_stats.get(manager, 0) + 1
        if manager_stats:
            report.append("")
            report.append("## Активные менеджеры")
            sorted_managers = sorted(manager_stats.items(), key=lambda x: x[1], reverse=True)
            for manager, count in sorted_managers[:10]:
                report.append(f"- **{manager}:** {count} заявок")
        total_income = 0
        total_expenses = 0
        successful_orders = 0
        cancelled_orders = 0
        for record in records:
            income = record.get('Сумма заказчика', 0)
            expenses = record.get('Сумма перевозчика', 0)
            if isinstance(income, (int, float)) and income > 0:
                total_income += income
            if isinstance(expenses, (int, float)) and expenses > 0:
                total_expenses += expenses
            cancelled = record.get('Дата отмены заявки')
            if cancelled:
                cancelled_orders += 1
            else:
                successful_orders += 1
        total_profit = total_income - total_expenses
        total_records = len(records) or 1
        report.extend([
            "",
            "## Финансовая сводка",
            f"- **Общая сумма заказчиков:** {total_income:,.0f} руб.",
            f"- **Общая сумма перевозчиков:** {total_expenses:,.0f} руб.",
            f"- **Общая прибыль:** {total_profit:,.0f} руб.",
            f"- **Средняя прибыль на заявку:** {total_profit/total_records:,.0f} руб.",
            "",
            "## Статус заявок",
            f"- **Успешных заявок:** {successful_orders} ({successful_orders/total_records*100:.1f}%)",
            f"- **Отмененных заявок:** {cancelled_orders} ({cancelled_orders/total_records*100:.1f}%)",
        ])
        report.extend([
            "",
            "---",
            "*Преобразованный JSON сохранён в папку `data`*",
            "*Нажмите 'Анализ' для детального анализа*",
        ])
        return "\n".join(report)


def main():
    """Точка входа UI-модуля: создаёт QApplication и показывает окно."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(250, 250, 250))
    palette.setColor(QPalette.WindowText, QColor(50, 50, 50))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(248, 248, 248))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(50, 50, 50))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(50, 50, 50))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    font = QFont('Segoe UI', 14)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
