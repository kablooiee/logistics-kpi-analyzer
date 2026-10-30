# -*- coding: utf-8 -*-
"""Вспомогательные функции и классы UI."""

from PyQt5.QtCore import QDate, QThread, pyqtSignal
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout

from core.excel import ParseError, parse_excel_to_json_with_progress

RESULTS_DOCUMENT_STYLESHEET = """
    body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #2c3e50; line-height: 1.5; }
    h1 { font-size: 16pt; color: #1a1a2e; margin: 12px 0 8px 0; border-bottom: 2px solid #3498db; padding-bottom: 4px; font-weight: 600; }
    h2 { font-size: 13pt; color: #2c3e50; margin: 12px 0 6px 0; font-weight: 600; }
    h3 { font-size: 12pt; color: #555; margin: 10px 0 4px 0; font-weight: 600; }
    p { margin: 4px 0; }
    table { border-collapse: collapse; margin: 8px 0; }
    th { background-color: #34495e; color: white; padding: 6px 10px; text-align: left; font-weight: 600; font-size: 10pt; }
    td { border-bottom: 1px solid #ecf0f1; padding: 5px 10px; font-size: 10pt; }
    tr:nth-child(even) td { background-color: #fafbfc; }
    blockquote { border-left: 3px solid #3498db; margin: 6px 0; padding: 4px 12px; background: #ecf0f1; font-size: 10pt; }
    ul, ol { margin: 4px 0 4px 22px; }
    li { margin: 2px 0; }
    strong { color: #1a1a2e; }
"""

def markdown_to_html(text: str) -> str:
    """Простой рендеринг markdown в HTML для QTextEdit."""
    try:
        import markdown
        return markdown.markdown(
            text, extensions=['tables', 'nl2br', 'fenced_code']
        )
    except ImportError:
        return f"<pre style='font-family: Consolas, monospace;'>{text}</pre>"

def to_qdate_safe(value):
    """Преобразует date/datetime-подобное значение в QDate, иначе None."""
    if value is None:
        return None
    try:
        return QDate(value.year, value.month, value.day)
    except Exception:
        return None

class Card(QFrame):
    """Информационная карточка KPI/качества без интерактивности."""

    STATUS_COLORS = {
        'good': '#27ae60',
        'warning': '#f39c12',
        'critical': '#e74c3c',
        'neutral': '#95a5a6',
    }

    def __init__(self, label: str, value: str, status: str, comment: str):
        super().__init__()
        color = self.STATUS_COLORS.get(status, self.STATUS_COLORS['neutral'])
        self.setMinimumHeight(136)
        self.setMinimumWidth(180)
        self.setStyleSheet(
            f'QFrame {{'
            f'background: #ffffff;'
            f'border: 1px solid #d9e1e7;'
            f'border-left: 4px solid {color};'
            f'border-radius: 8px;'
            f'}}'
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        label_widget = QLabel(label)
        label_widget.setStyleSheet('font-size: 9pt; color: #7f8c8d;')
        label_widget.setWordWrap(True)
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setStyleSheet('font-size: 13pt; font-weight: 700; color: #1f2d3d;')
        value_widget.setWordWrap(True)
        layout.addWidget(value_widget)

        comment_widget = QLabel(comment)
        comment_widget.setStyleSheet('font-size: 8pt; color: #95a5a6;')
        comment_widget.setWordWrap(True)
        layout.addWidget(comment_widget)

class ParseWorker(QThread):
    """Фоновый поток парсинга Excel с сигналом прогресса."""

    progress = pyqtSignal(int, int)
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, filepath, sheet_name=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.sheet_name = sheet_name

    def run(self):
        def on_progress(current_row, total_rows):
            self.progress.emit(current_row, total_rows)

        try:
            json_str = parse_excel_to_json_with_progress(
                self.filepath,
                self.sheet_name,
                progress_callback=on_progress,
            )
            self.finished_ok.emit(json_str)
        except ParseError as e:
            self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(f'Неожиданная ошибка: {e}')
