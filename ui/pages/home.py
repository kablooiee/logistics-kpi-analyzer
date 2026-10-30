# -*- coding: utf-8 -*-
"""Главная страница с плиточной навигацией."""

import html
import os
import sys
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.settings import get_settings
from core.charts import Charts
from ui.dialogs import ReportDialog
from ui.helpers import Card

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class HomePage(QWidget):
    """Главная страница с плиточной навигацией."""

    TILE_MAP = [
        ('Данные', 'data'),
        ('Анализ', 'analysis'),
        ('Сравнение', 'comparison'),
        ('Поиск', 'search'),
        ('Аномалии', 'anomalies'),
        ('Воронка', 'funnel'),
        ('Рекомендации', 'recommendations'),
        ('Отчёт', 'report'),
    ]

    def __init__(self, parent_main: 'MainWindow'):
        super().__init__()
        self.parent_main = parent_main
        self.tile_buttons = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(16)

        header_panel = QWidget()
        header_panel.setObjectName('homePanel')
        header_layout = QVBoxLayout(header_panel)
        header_layout.setContentsMargins(18, 16, 18, 16)
        header_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        title = QLabel('Анализатор отчётов')
        title.setStyleSheet('font-size: 22pt; font-weight: 700; color: #1a1a2e;')
        header.addWidget(title, 1, Qt.AlignLeft)

        btn_help = QPushButton('Помощь')
        btn_help.clicked.connect(lambda: self.parent_main.show_page('help'))
        btn_settings = QPushButton('Настройки')
        btn_settings.clicked.connect(lambda: self.parent_main.show_page('settings'))
        header.addWidget(btn_help)
        header.addWidget(btn_settings)
        header_layout.addLayout(header)

        self.file_info_label = QLabel(
            'Файл не загружен. Нажмите Данные, чтобы открыть Excel или JSON.'
        )
        self.file_info_label.setAlignment(Qt.AlignCenter)
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setStyleSheet(
            'color: #7f8c8d; border: 1px solid #dfe6e9; border-radius: 8px; padding: 12px;'
        )
        header_layout.addWidget(self.file_info_label)
        root.addWidget(header_panel)

        self.kpi_group = QGroupBox('Ключевые показатели')
        self.kpi_cards_layout = QGridLayout()
        self.kpi_cards_layout.setSpacing(10)
        for col in range(4):
            self.kpi_cards_layout.setColumnStretch(col, 1)
        self.kpi_group.setLayout(self.kpi_cards_layout)
        self.kpi_group.setVisible(False)
        root.addWidget(self.kpi_group)

        tiles_panel = QWidget()
        tiles_panel.setObjectName('tilePanel')
        tiles_layout = QVBoxLayout(tiles_panel)
        tiles_layout.setContentsMargins(18, 18, 18, 18)
        tiles_layout.setSpacing(12)

        tiles_title = QLabel('Разделы системы')
        tiles_title.setStyleSheet('font-size: 12pt; font-weight: 600; color: #34495e;')
        tiles_layout.addWidget(tiles_title, alignment=Qt.AlignLeft)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for col in range(4):
            grid.setColumnStretch(col, 1)
        for row in range(2):
            grid.setRowStretch(row, 1)
        for i, (label, page_name) in enumerate(self.TILE_MAP):
            btn = QPushButton(label)
            btn.setObjectName('tileButton')
            btn.setMinimumSize(240, 104)
            btn.setMaximumHeight(120)
            btn.setCursor(Qt.PointingHandCursor)
            if page_name == 'report':
                btn.clicked.connect(self.on_report_click)
            else:
                btn.clicked.connect(lambda _=False, n=page_name: self.parent_main.show_page(n))
            row, col = divmod(i, 4)
            grid.addWidget(btn, row, col)
            self.tile_buttons[page_name] = btn
        tiles_layout.addLayout(grid)
        root.addWidget(tiles_panel)
        root.addStretch(1)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)

    def update_cards(self, analyzer):
        if analyzer is None:
            self._clear_layout(self.kpi_cards_layout)
            self.kpi_group.setVisible(False)
            return

        summary_cards = analyzer.get_summary_cards() or []
        self._clear_layout(self.kpi_cards_layout)

        if summary_cards:
            for i, card in enumerate(summary_cards[:8]):
                row, col = divmod(i, 4)
                widget = Card(
                    card.get('label', ''),
                    card.get('value', '—'),
                    card.get('status', 'neutral'),
                    card.get('comment', ''),
                )
                self.kpi_cards_layout.addWidget(widget, row, col)
            self.kpi_group.setVisible(True)
        else:
            self.kpi_group.setVisible(False)

    def set_tiles_enabled(self, loaded: bool):
        for page_name, btn in self.tile_buttons.items():
            btn.setEnabled(loaded or page_name == 'data')

    def on_report_click(self):
        analyzer = self.parent_main._refresh_analyzer()
        if analyzer is None:
            QMessageBox.warning(self, 'Нет данных', 'Сначала загрузите файл на странице Данные.')
            return

        dialog = ReportDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        config = dialog.get_config()
        exports_dir = 'exports'
        os.makedirs(exports_dir, exist_ok=True)
        output_path = os.path.join(exports_dir, config['filename'])
        self.parent_main.status_label.setText('Формирование отчёта...')
        QApplication.processEvents()

        try:
            from core.reports import Pdf
            visualizer = self.parent_main.charts
            if visualizer is None:
                visualizer = Charts(analyzer)
                self.parent_main.charts = visualizer
            file_hash = getattr(self.parent_main, 'file_hash', None)
            builder = Pdf(
                analyzer,
                visualizer,
                get_settings(),
                file_hash=file_hash,
            )
            builder.build_pdf(
                sections=config['sections'],
                output_path=output_path,
                report_title=config['title'],
            )

            msg = QMessageBox(self)
            msg.setWindowTitle('Отчёт сформирован')
            msg.setText(f'Отчёт сохранён:\n{os.path.abspath(output_path)}')
            msg.setIcon(QMessageBox.Information)
            open_btn = msg.addButton('Открыть папку', QMessageBox.ActionRole)
            msg.addButton('Закрыть', QMessageBox.AcceptRole)
            msg.exec_()

            if msg.clickedButton() == open_btn:
                import subprocess

                folder = os.path.abspath(exports_dir)
                if sys.platform == 'win32':
                    os.startfile(folder)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', folder], check=False)
                else:
                    subprocess.run(['xdg-open', folder], check=False)
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка формирования отчёта', f'Не удалось сформировать отчёт:\n{e}')
        finally:
            self.parent_main.status_label.setText('Готово')

    def update_file_info(
        self,
        loaded: bool,
        file_name: str = '',
        period_text: str = '—',
        records_count: int = 0,
        analyzed_count: int = 0,
    ):
        if not loaded:
            self.file_info_label.setText(
                'Файл не загружен. Нажмите Данные, чтобы открыть Excel или JSON.'
            )
            self.file_info_label.setAlignment(Qt.AlignCenter)
            self.file_info_label.setStyleSheet(
                'color: #7f8c8d; border: 1px solid #dfe6e9; border-radius: 8px; padding: 12px;'
            )
            return
        file_name_html = html.escape(str(file_name or '—'))
        period_html = html.escape(str(period_text or '—'))
        records_count = int(records_count or 0)
        analyzed_count = int(analyzed_count or 0)
        if records_count > analyzed_count:
            records_line = (
                f'<span style="color: #000000;">Записей в файле: {records_count} | </span>'
                f'<span style="color: #f39c12; font-weight: 700;">'
                f'Проанализировано: {analyzed_count} (из {records_count})'
                f'</span>'
            )
        else:
            records_line = (
                f'<span style="color: #000000;">'
                f'Записей в файле: {records_count} | Проанализировано: {analyzed_count}'
                f'</span>'
            )
        self.file_info_label.setText(
            f'Файл: {file_name_html}<br>'
            f'Период данных: {period_html}<br>'
            f'{records_line}'
        )
        self.file_info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.file_info_label.setStyleSheet(
            'color: #2c3e50; border: 1px solid #d0d6dc; border-radius: 8px; padding: 12px;'
        )
