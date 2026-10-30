# -*- coding: utf-8 -*-
"""Страница проблемных заявок."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QTextEdit

from ui.pages.base import BasePage
from ui.helpers import RESULTS_DOCUMENT_STYLESHEET, markdown_to_html
from ui.helpers import Card


class AnomaliesPage(BasePage):
    """Страница проблемных заявок."""

    def __init__(self, parent_main):
        super().__init__(parent_main, 'Проблемные заявки', 'Аномалии по KPI-правилам')
        self.btn_run = QPushButton('Показать проблемные заявки')
        self.btn_run.setObjectName('primaryButton')
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self.parent_main.show_anomalies)
        self.content_layout.addWidget(self.btn_run, alignment=Qt.AlignLeft)

        self.quality_group = QGroupBox('Качество данных')
        self.quality_cards_layout = QHBoxLayout()
        self.quality_cards_layout.setSpacing(10)
        self.quality_group.setLayout(self.quality_cards_layout)
        self.content_layout.addWidget(self.quality_group)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.content_layout.addWidget(self.separator)

        self.anomalies_title = QLabel('Проблемные заявки')
        self.anomalies_title.setStyleSheet('font-size: 12pt; font-weight: 600; color: #34495e;')
        self.content_layout.addWidget(self.anomalies_title)

        self.no_data_label = QLabel('Загрузите файл на главной странице для просмотра аномалий')
        self.no_data_label.setAlignment(Qt.AlignCenter)
        self.no_data_label.setWordWrap(True)
        self.no_data_label.setStyleSheet('color: #7f8c8d; font-size: 10pt; padding: 20px;')
        self.content_layout.addWidget(self.no_data_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.document().setDefaultStyleSheet(RESULTS_DOCUMENT_STYLESHEET)
        self.content_layout.addWidget(self.results_text, 1)
        self._set_no_data_state(True)

    def set_data_loaded(self, loaded: bool):
        self.btn_run.setEnabled(loaded)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _populate_quality_cards(self, analyzer):
        quality_cards = analyzer.get_data_quality() or []
        self._clear_layout(self.quality_cards_layout)
        for card in quality_cards[:4]:
            widget = Card(
                card.get('label', ''),
                card.get('value', '—'),
                card.get('status', 'neutral'),
                card.get('comment', ''),
            )
            self.quality_cards_layout.addWidget(widget)
        self.quality_cards_layout.addStretch(1)

    def _set_no_data_state(self, is_no_data: bool):
        self.quality_group.setVisible(not is_no_data)
        self.separator.setVisible(not is_no_data)
        self.anomalies_title.setVisible(not is_no_data)
        self.results_text.setVisible(not is_no_data)
        self.no_data_label.setVisible(is_no_data)
        if is_no_data:
            self.results_text.setHtml(markdown_to_html(''))
            self._clear_layout(self.quality_cards_layout)

    def on_show(self):
        analyzer = self.parent_main._refresh_analyzer()
        if analyzer is None:
            self._set_no_data_state(True)
            self.no_data_label.setText('Загрузите файл на главной странице для просмотра аномалий')
            return

        self._populate_quality_cards(analyzer)
        report = self.parent_main._anomalies_md(
            analyzer,
            limit_per_category=self.parent_main._anomalies_limit(),
        )
        self.results_text.setHtml(markdown_to_html(report))
        self._set_no_data_state(False)
