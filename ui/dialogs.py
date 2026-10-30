# -*- coding: utf-8 -*-
"""Диалоговые окна приложения."""

import os
from datetime import date, datetime, time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from ui.helpers import to_qdate_safe

class ChartViewerDialog(QDialog):
    """Окно просмотра 1-2 графиков выбранного анализа."""

    def __init__(self, title: str, figures: list, parent=None):
        super().__init__(parent)
        self._figures = figures
        self.setWindowTitle(title)
        self.resize(1100, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        for _, fig in self._figures:
            canvas = FigureCanvasQTAgg(fig)
            canvas.setMinimumHeight(300)
            layout.addWidget(canvas, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_save = QPushButton('Сохранить')
        btn_save.clicked.connect(self.save_charts_click)
        buttons.addWidget(btn_save)
        btn_close = QPushButton('Закрыть')
        btn_close.clicked.connect(self.accept)
        buttons.addWidget(btn_close)
        layout.addLayout(buttons)

    def save_charts_click(self):
        export_dir = os.path.join(os.getcwd(), 'exports')
        os.makedirs(export_dir, exist_ok=True)
        saved = 0
        for name, fig in self._figures:
            fig.savefig(os.path.join(export_dir, f'{name}.png'), dpi=110, bbox_inches='tight')
            saved += 1
        QMessageBox.information(self, 'Готово', f'Сохранено {saved} графиков в папку:\n{export_dir}')

class FiltersDialog(QDialog):
    """Модальный диалог выбора фильтров данных."""

    def __init__(self, options: dict, current: dict, parent=None):
        super().__init__(parent)
        self.options = options or {}
        self.current = current or {}
        self._date_min = to_qdate_safe(self.options.get('date_min'))
        self._date_max = to_qdate_safe(self.options.get('date_max'))

        self.setWindowTitle('Фильтры')
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        period_group = QGroupBox('Период')
        period_layout = QGridLayout()
        period_layout.setHorizontalSpacing(10)
        period_layout.setVerticalSpacing(8)

        period_layout.addWidget(QLabel('С:'), 0, 0)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat('dd.MM.yyyy')
        period_layout.addWidget(self.date_from, 0, 1)

        period_layout.addWidget(QLabel('По:'), 0, 2)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat('dd.MM.yyyy')
        period_layout.addWidget(self.date_to, 0, 3)
        period_group.setLayout(period_layout)
        layout.addWidget(period_group)

        data_group = QGroupBox('Фильтры по данным')
        data_layout = QGridLayout()
        data_layout.setHorizontalSpacing(10)
        data_layout.setVerticalSpacing(8)

        data_layout.addWidget(QLabel('Филиал:'), 0, 0)
        self.combo_branch = QComboBox()
        data_layout.addWidget(self.combo_branch, 0, 1)

        data_layout.addWidget(QLabel('Менеджер:'), 1, 0)
        self.combo_manager = QComboBox()
        data_layout.addWidget(self.combo_manager, 1, 1)

        data_layout.addWidget(QLabel('Тип перевозчика:'), 2, 0)
        self.combo_carrier_type = QComboBox()
        data_layout.addWidget(self.combo_carrier_type, 2, 1)
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_apply = QPushButton('Применить')
        self.btn_apply.setObjectName('primaryButton')
        self.btn_apply.clicked.connect(self.accept)
        buttons.addWidget(self.btn_apply)

        self.btn_reset = QPushButton('Сбросить')
        self.btn_reset.clicked.connect(self.reset_values)
        buttons.addWidget(self.btn_reset)

        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)

        self._fill_combo(self.combo_branch, self.options.get('branches') or [])
        self._fill_combo(self.combo_manager, self.options.get('managers') or [])
        self._fill_combo(self.combo_carrier_type, self.options.get('carrier_types') or [])
        self._apply_initial_values()

    def _fill_combo(self, combo, items):
        combo.clear()
        combo.addItem('Все')
        for item in items:
            combo.addItem(str(item))

    def _apply_initial_values(self):
        if self._date_min and self._date_max:
            self.date_from.setDateRange(self._date_min, self._date_max)
            self.date_to.setDateRange(self._date_min, self._date_max)
            self.date_from.setDate(self._date_min)
            self.date_to.setDate(self._date_max)

        c_from = self.current.get('date_from')
        c_to = self.current.get('date_to')
        q_from = to_qdate_safe(c_from)
        q_to = to_qdate_safe(c_to)
        if q_from and self._date_min and self._date_max:
            self.date_from.setDate(max(self._date_min, min(q_from, self._date_max)))
        if q_to and self._date_min and self._date_max:
            self.date_to.setDate(max(self._date_min, min(q_to, self._date_max)))

        def set_combo_value(combo, value):
            if not value:
                combo.setCurrentIndex(0)
                return
            idx = combo.findText(str(value), Qt.MatchFixedString)
            combo.setCurrentIndex(idx if idx >= 0 else 0)

        set_combo_value(self.combo_branch, self.current.get('branch'))
        set_combo_value(self.combo_manager, self.current.get('manager'))
        set_combo_value(self.combo_carrier_type, self.current.get('carrier_type'))

    def reset_values(self):
        self.combo_branch.setCurrentIndex(0)
        self.combo_manager.setCurrentIndex(0)
        self.combo_carrier_type.setCurrentIndex(0)
        if self._date_min and self._date_max:
            self.date_from.setDate(self._date_min)
            self.date_to.setDate(self._date_max)

    def get_filters(self) -> dict:
        qd1 = self.date_from.date()
        qd2 = self.date_to.date()
        if qd1 > qd2:
            qd1, qd2 = qd2, qd1

        date_from = datetime(qd1.year(), qd1.month(), qd1.day())
        date_to = datetime.combine(date(qd2.year(), qd2.month(), qd2.day()), time.max)

        if self._date_min and self._date_max:
            min_dt = datetime(self._date_min.year(), self._date_min.month(), self._date_min.day())
            max_dt = datetime.combine(
                date(self._date_max.year(), self._date_max.month(), self._date_max.day()),
                time.max,
            )
            if date_from == min_dt and date_to == max_dt:
                date_from = None
                date_to = None

        branch = self.combo_branch.currentText()
        manager = self.combo_manager.currentText()
        carrier_type = self.combo_carrier_type.currentText()

        return {
            'date_from': date_from,
            'date_to': date_to,
            'branch': None if branch == 'Все' else branch,
            'manager': None if manager == 'Все' else manager,
            'carrier_type': None if carrier_type == 'Все' else carrier_type,
        }

class ReportDialog(QDialog):
    """Диалог настройки параметров итогового PDF-отчёта."""

    SECTION_ITEMS = [
        ('summary', 'Сводка ключевых показателей'),
        ('financial', 'Финансовый анализ'),
        ('operational', 'Операционный анализ'),
        ('quality', 'Анализ качества'),
        ('timeliness', 'Анализ своевременности'),
        ('anomalies', 'Проблемные заявки'),
        ('recommendations', 'Автоматические рекомендации'),
        ('analyst_notes', 'Заметки аналитика'),
    ]
    DEFAULT_ENABLED_SECTIONS = {
        'summary',
        'financial',
        'operational',
        'quality',
        'timeliness',
        'anomalies',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Формирование отчёта')
        self.resize(520, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        today = datetime.now()
        self.name_input = QLineEdit(f'Отчёт Анализатора отчётов ({today.strftime("%d.%m.%Y")})')
        root.addWidget(QLabel('Название отчёта:'))
        root.addWidget(self.name_input)

        sections_group = QGroupBox('Какие разделы включить')
        sections_layout = QVBoxLayout(sections_group)
        sections_layout.setContentsMargins(10, 10, 10, 10)
        sections_layout.setSpacing(6)
        self.section_checks = {}
        for key, title in self.SECTION_ITEMS:
            cb = QCheckBox(title)
            cb.setChecked(key in self.DEFAULT_ENABLED_SECTIONS)
            sections_layout.addWidget(cb)
            self.section_checks[key] = cb
        root.addWidget(sections_group)

        file_group = QGroupBox('Имя файла')
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(10, 10, 10, 10)
        file_layout.setSpacing(6)
        row = QHBoxLayout()
        stamp = today.strftime('%Y%m%d_%H%M%S')
        self.filename_input = QLineEdit(f'kpi_report_{stamp}')
        row.addWidget(self.filename_input, 1)
        row.addWidget(QLabel('.pdf'))
        file_layout.addLayout(row)
        hint = QLabel('Файл будет сохранён в папку exports/')
        hint.setStyleSheet('font-size: 9pt; color: #7f8c8d;')
        file_layout.addWidget(hint)
        root.addWidget(file_group)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        btn_ok = QPushButton('Сформировать')
        btn_ok.setObjectName('primaryButton')
        btn_ok.clicked.connect(self.accept)
        buttons.addWidget(btn_ok)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)
        root.addLayout(buttons)

    def get_config(self) -> dict:
        sections = [key for key, _title in self.SECTION_ITEMS if self.section_checks[key].isChecked()]
        title = (self.name_input.text() or '').strip() or 'Отчёт Анализатора отчётов'
        filename_base = (self.filename_input.text() or '').strip() or f'kpi_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        safe_filename = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in filename_base).strip('_')
        if not safe_filename:
            safe_filename = f'kpi_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        return {
            'title': title,
            'filename': safe_filename + '.pdf',
            'sections': sections,
        }
