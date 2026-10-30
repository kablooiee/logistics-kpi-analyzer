# -*- coding: utf-8 -*-
"""Страница поиска заявок."""

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit

from ui.pages.base import BasePage
from ui.helpers import RESULTS_DOCUMENT_STYLESHEET


class SearchPage(BasePage):
    """Страница поиска заявок."""

    def __init__(self, parent_main):
        super().__init__(parent_main, 'Поиск', 'Поиск по полям заявок')
        self.search_limit = 50

        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Номер заявки, менеджер, перевозчик, водитель...')
        self.search_input.returnPressed.connect(self.search_click)
        row.addWidget(self.search_input, 1)

        self.search_button = QPushButton('Найти')
        self.search_button.setObjectName('primaryButton')
        self.search_button.setEnabled(False)
        self.search_button.clicked.connect(self.search_click)
        row.addWidget(self.search_button)
        self.content_layout.addLayout(row)

        self.info_label = QLabel('Введите минимум 2 символа')
        self.info_label.setStyleSheet('color: #95a5a6;')
        self.content_layout.addWidget(self.info_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.document().setDefaultStyleSheet(RESULTS_DOCUMENT_STYLESHEET)
        self.content_layout.addWidget(self.results_text, 1)

    def set_data_loaded(self, loaded: bool):
        self.search_button.setEnabled(loaded)

    def search_click(self):
        self.parent_main.search_click()
