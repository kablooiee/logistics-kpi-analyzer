# -*- coding: utf-8 -*-
"""Страница сравнения двух периодов."""

from datetime import date, datetime, time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDateEdit, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QTextEdit

from ui.pages.base import BasePage
from ui.helpers import RESULTS_DOCUMENT_STYLESHEET


class ComparisonPage(BasePage):
    """Страница сравнения двух периодов."""

    def __init__(self, parent_main):
        super().__init__(parent_main, 'Сравнение периодов', 'Сопоставление периодов A и B')

        hint = QLabel(
            'Выберите два периода для сравнения KPI. '
            'Программа покажет изменения по ключевым показателям.'
        )
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #7f8c8d;')
        self.content_layout.addWidget(hint)

        groups = QHBoxLayout()
        groups.setSpacing(12)
        self.a_from, self.a_to, group_a = self._build_period_group('Период A')
        self.b_from, self.b_to, group_b = self._build_period_group('Период B')
        groups.addWidget(group_a)
        groups.addWidget(group_b)
        self.content_layout.addLayout(groups)

        self.btn_compare = QPushButton('Сравнить')
        self.btn_compare.setObjectName('primaryButton')
        self.btn_compare.setEnabled(False)
        self.btn_compare.clicked.connect(self.compare_click)
        self.content_layout.addWidget(self.btn_compare, alignment=Qt.AlignLeft)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.document().setDefaultStyleSheet(RESULTS_DOCUMENT_STYLESHEET)
        self.content_layout.addWidget(self.results_text, 1)

    def _build_period_group(self, title):
        group = QGroupBox(title)
        layout = QGridLayout()
        layout.addWidget(QLabel('С:'), 0, 0)
        date_from = QDateEdit()
        date_from.setCalendarPopup(True)
        date_from.setDisplayFormat('dd.MM.yyyy')
        layout.addWidget(date_from, 0, 1)

        layout.addWidget(QLabel('По:'), 1, 0)
        date_to = QDateEdit()
        date_to.setCalendarPopup(True)
        date_to.setDisplayFormat('dd.MM.yyyy')
        layout.addWidget(date_to, 1, 1)
        group.setLayout(layout)
        return date_from, date_to, group

    def set_data_loaded(self, loaded: bool):
        self.btn_compare.setEnabled(loaded)

    def on_show(self):
        self.parent_main.setup_comparison_dates()

    def get_periods(self):
        def qd_range(q_from, q_to):
            if q_from > q_to:
                q_from, q_to = q_to, q_from
            df = datetime(q_from.year(), q_from.month(), q_from.day())
            dt = datetime.combine(date(q_to.year(), q_to.month(), q_to.day()), time.max)
            return {'date_from': df, 'date_to': dt}
        return (
            qd_range(self.a_from.date(), self.a_to.date()),
            qd_range(self.b_from.date(), self.b_to.date()),
        )

    def compare_click(self):
        self.parent_main.compare_periods_click()
