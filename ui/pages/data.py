# -*- coding: utf-8 -*-
"""Страница загрузки/сохранения и базовых операций."""

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit

from ui.pages.base import BasePage
from ui.helpers import RESULTS_DOCUMENT_STYLESHEET


class DataPage(BasePage):
    """Страница загрузки/сохранения и базовых операций."""

    def __init__(self, parent_main):
        super().__init__(parent_main, 'Данные', 'Загрузка и сохранение')

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.btn_open = QPushButton('Открыть')
        self.btn_open.setObjectName('primaryButton')
        self.btn_open.clicked.connect(self.parent_main.open_file)
        top_row.addWidget(self.btn_open)

        self.btn_save = QPushButton('Сохранить')
        self.btn_save.clicked.connect(self.parent_main.save_file_as)
        self.btn_save.setEnabled(False)
        top_row.addWidget(self.btn_save)

        self.btn_statistics = QPushButton('Статистика')
        self.btn_statistics.clicked.connect(self.parent_main.show_statistics)
        self.btn_statistics.setEnabled(False)
        top_row.addWidget(self.btn_statistics)

        self.btn_file_stats = QPushButton('Статистика файла')
        self.btn_file_stats.clicked.connect(self.parent_main.show_file_statistics)
        self.btn_file_stats.setEnabled(False)
        top_row.addWidget(self.btn_file_stats)

        self.btn_filters = QPushButton('Фильтры')
        self.btn_filters.clicked.connect(self.parent_main.open_filters_dialog)
        self.btn_filters.setEnabled(False)
        top_row.addWidget(self.btn_filters)

        self.filters_indicator = QLabel('Фильтры: нет')
        self.filters_indicator.setStyleSheet('color: #7f8c8d;')
        top_row.addWidget(self.filters_indicator)
        top_row.addStretch(1)
        self.content_layout.addLayout(top_row)

        self.info_label = QLabel('Загрузите файл Excel или JSON.')
        self.info_label.setStyleSheet('color: #7f8c8d;')
        self.content_layout.addWidget(self.info_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.document().setDefaultStyleSheet(RESULTS_DOCUMENT_STYLESHEET)
        self.content_layout.addWidget(self.results_text, 1)
