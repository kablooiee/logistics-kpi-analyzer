# -*- coding: utf-8 -*-
"""Страница авто-рекомендаций и заметок аналитика."""

import os

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.settings import get_settings
from ui.pages.base import BasePage


class RecommendationsPage(BasePage):
    """Страница авто-рекомендаций и заметок аналитика."""

    SEVERITY_COLORS = {
        'info': '#3498db',
        'warning': '#f39c12',
        'critical': '#e74c3c',
    }

    def __init__(self, parent_main):
        super().__init__(parent_main, 'Рекомендации', '')
        self.settings_mgr = get_settings()
        self._notes_timer = QTimer(self)
        self._notes_timer.setSingleShot(True)
        self._notes_timer.setInterval(2000)
        self._notes_timer.timeout.connect(self._autosave_notes)
        self._loading_notes = False

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        left = QGroupBox('Автоматические инсайты')
        left_layout = QVBoxLayout(left)
        self.insights_scroll = QScrollArea()
        self.insights_scroll.setWidgetResizable(True)
        self.insights_container = QWidget()
        self.insights_layout = QVBoxLayout(self.insights_container)
        self.insights_layout.setContentsMargins(0, 0, 0, 0)
        self.insights_layout.setSpacing(8)
        self.insights_scroll.setWidget(self.insights_container)
        left_layout.addWidget(self.insights_scroll)

        right = QGroupBox('Заметки аналитика')
        right_layout = QVBoxLayout(right)
        notes_hint = QLabel(
            'Введите свои выводы и рекомендации. Они будут сохранены и '
            'попадут в финальный отчёт руководителю.'
        )
        notes_hint.setWordWrap(True)
        notes_hint.setStyleSheet('color: #5d6d7e;')
        right_layout.addWidget(notes_hint)

        self.notes_editor = QTextEdit()
        self.notes_editor.setMinimumHeight(300)
        self.notes_editor.setStyleSheet('font-size: 11pt;')
        self.notes_editor.textChanged.connect(self._on_notes_changed)
        right_layout.addWidget(self.notes_editor, 1)

        bottom = QHBoxLayout()
        self.notes_file_label = QLabel('Заметки для файла: —')
        self.notes_file_label.setStyleSheet('color: #7f8c8d; font-size: 10pt;')
        bottom.addWidget(self.notes_file_label)
        bottom.addStretch(1)
        self.notes_status_label = QLabel('Заметки автоматически сохраняются')
        self.notes_status_label.setStyleSheet('color: #7f8c8d; font-size: 10pt;')
        bottom.addWidget(self.notes_status_label)
        self.btn_save_notes = QPushButton('Сохранить сейчас')
        self.btn_save_notes.setObjectName('primaryButton')
        self.btn_save_notes.clicked.connect(self.save_notes_now)
        bottom.addWidget(self.btn_save_notes)
        right_layout.addLayout(bottom)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([520, 520])
        self.content_layout.addWidget(splitter, 1)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            child = item.layout()
            if child is not None:
                self._clear_layout(child)

    def _build_insight_card(self, rec: dict):
        severity = rec.get('severity', 'info')
        color = self.SEVERITY_COLORS.get(severity, self.SEVERITY_COLORS['info'])
        frame = QFrame()
        frame.setStyleSheet(
            'QFrame {'
            'background: white;'
            'border: 1px solid #d0d6dc;'
            f'border-left: 4px solid {color};'
            'border-radius: 6px;'
            '}'
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        cat = QLabel(rec.get('category', ''))
        cat.setStyleSheet('font-size: 9pt; color: #7f8c8d;')
        layout.addWidget(cat)

        title = QLabel(rec.get('title', ''))
        title.setWordWrap(True)
        title.setStyleSheet('font-size: 12pt; font-weight: 700; color: #2c3e50;')
        layout.addWidget(title)

        text = QLabel(rec.get('text', ''))
        text.setWordWrap(True)
        text.setStyleSheet('font-size: 10pt; color: #2c3e50;')
        layout.addWidget(text)
        return frame

    def _populate_insights(self, recs: list):
        self._clear_layout(self.insights_layout)
        if not recs:
            msg = QLabel(
                'Программа не нашла критичных инсайтов в данных. '
                'Это хороший знак — основные показатели в норме.'
            )
            msg.setWordWrap(True)
            msg.setStyleSheet('color: #7f8c8d; padding: 8px;')
            self.insights_layout.addWidget(msg)
            self.insights_layout.addStretch(1)
            return

        for rec in recs:
            self.insights_layout.addWidget(self._build_insight_card(rec))
        self.insights_layout.addStretch(1)

    def _on_notes_changed(self):
        if self._loading_notes:
            return
        self.notes_status_label.setText('Автосохранение...')
        self._notes_timer.start()

    def _autosave_notes(self):
        self._save_notes(manual=False)

    def save_notes_now(self):
        self._save_notes(manual=True)

    def _save_notes(self, manual: bool):
        file_hash = self.parent_main.file_hash
        if not file_hash:
            self.notes_status_label.setText('Нет привязки к файлу для сохранения')
            return
        self.settings_mgr.save_notes(file_hash, self.notes_editor.toPlainText())
        self.notes_status_label.setText('Сохранено' if manual else 'Автосохранение выполнено')

    def set_data_loaded(self, loaded: bool):
        self.notes_editor.setEnabled(loaded)
        self.btn_save_notes.setEnabled(loaded)
        if not loaded:
            self._populate_insights([])
            self.notes_file_label.setText('Заметки для файла: —')
            self.notes_editor.clear()
            self.notes_status_label.setText('Загрузите файл для получения рекомендаций')

    def on_show(self):
        analyzer = self.parent_main._refresh_analyzer()
        if analyzer is None:
            self.set_data_loaded(False)
            return

        recs = analyzer.get_auto_recommendations()
        self._populate_insights(recs)
        self.set_data_loaded(True)

        file_hash = self.parent_main.file_hash or ''
        file_name = os.path.basename(self.parent_main.file_path or self.parent_main.json_path or '—')
        self.notes_file_label.setText(f'Заметки для файла: {file_name}')
        self._loading_notes = True
        try:
            notes = self.settings_mgr.load_notes(file_hash) if file_hash else ''
            self.notes_editor.setPlainText(notes)
        finally:
            self._loading_notes = False
        self.notes_status_label.setText('Заметки автоматически сохраняются')
