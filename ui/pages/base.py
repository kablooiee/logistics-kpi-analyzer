# -*- coding: utf-8 -*-
"""Базовая страница с верхней панелью навигации."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class BasePage(QWidget):
    """Базовая страница с общей верхней панелью навигации."""

    def __init__(self, parent_main, title: str, hint_text: str = ''):
        super().__init__()
        self.parent_main = parent_main
        self.title = title
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        nav = QHBoxLayout()
        nav.setSpacing(8)

        self.btn_home = QPushButton('← Главная')
        self.btn_home.setObjectName('navButton')
        self.btn_home.clicked.connect(self.go_home)
        nav.addWidget(self.btn_home, alignment=Qt.AlignLeft)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet('font-size: 16pt; font-weight: 700; color: #1a1a2e;')
        nav.addWidget(title_label, 1)

        self.hint_label = QLabel(hint_text)
        self.hint_label.setStyleSheet('color: #7f8c8d;')
        self.hint_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.hint_label.setMinimumWidth(220)
        nav.addWidget(self.hint_label)

        root.addLayout(nav)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        root.addLayout(self.content_layout, 1)

    def go_home(self):
        self.parent_main.show_page('home')

    def on_show(self):
        """Переопределяется при необходимости."""
