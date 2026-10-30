# -*- coding: utf-8 -*-
"""Страница процессной воронки обработки заявок."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QLabel, QScrollArea, QTextEdit, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from core.charts import Charts
from ui.pages.base import BasePage
from ui.helpers import RESULTS_DOCUMENT_STYLESHEET, markdown_to_html


class FunnelPage(BasePage):
    """Страница процессной воронки обработки заявок."""

    NO_DATA_MESSAGE = (
        'Для построения воронки недостаточно этапов. '
        'Проверьте, что в файле есть даты процессов (погрузка, доставка, закрытие).'
    )

    def __init__(self, parent_main):
        super().__init__(parent_main, 'Воронка процесса', '')
        self._canvas = None
        self._loss_reason_widgets = []

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scroll_content = QWidget()
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setContentsMargins(2, 2, 2, 10)
        self.scroll_content_layout.setSpacing(10)
        self.scroll.setWidget(self.scroll_content)
        self.content_layout.addWidget(self.scroll, 1)

        self.description_label = QLabel(
            'Движение заявок по этапам обработки. '
            'Показаны точки потерь и причины отмен на каждом этапе.'
        )
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet('color: #5d6d7e;')
        self.scroll_content_layout.addWidget(self.description_label)

        self.warning_label = QLabel('')
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet(
            'background-color: #fff8e1; color: #8a6d3b; border: 1px solid #f0d98c; '
            'border-radius: 8px; padding: 8px 10px;'
        )
        self.warning_label.setVisible(False)
        self.scroll_content_layout.addWidget(self.warning_label)

        self.chart_wrap = QFrame()
        self.chart_wrap.setStyleSheet('QFrame { background: #ffffff; border: 1px solid #dfe6e9; border-radius: 8px; }')
        self.chart_wrap.setFixedHeight(420)
        chart_layout = QVBoxLayout(self.chart_wrap)
        chart_layout.setContentsMargins(10, 10, 10, 10)
        chart_layout.setSpacing(6)
        self.scroll_content_layout.addWidget(self.chart_wrap)

        self.table_text = QTextEdit()
        self.table_text.setReadOnly(True)
        self.table_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_text.document().setDefaultStyleSheet(RESULTS_DOCUMENT_STYLESHEET)
        self.scroll_content_layout.addWidget(self.table_text)

        self.losses_title = QLabel('Где отваливаются заявки')
        self.losses_title.setStyleSheet('font-size: 12pt; font-weight: 700; color: #2c3e50;')
        self.scroll_content_layout.addWidget(self.losses_title)

        self.losses_container = QWidget()
        self.losses_layout = QVBoxLayout(self.losses_container)
        self.losses_layout.setContentsMargins(0, 0, 0, 0)
        self.losses_layout.setSpacing(8)
        self.scroll_content_layout.addWidget(self.losses_container)

        self.insights_label = QLabel('')
        self.insights_label.setWordWrap(True)
        self.insights_label.setTextFormat(Qt.RichText)
        self.insights_label.setStyleSheet(
            'background-color: #fff5f5; color: #922b21; border: 1px solid #f5b7b1; border-radius: 8px; padding: 12px;'
        )
        self.scroll_content_layout.addWidget(self.insights_label)
        self.scroll_content_layout.addStretch(1)

    def _set_chart_widget(self, widget):
        layout = self.chart_wrap.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        layout.addWidget(widget)
        self._canvas = widget

    def _show_no_data(self, message: str):
        msg = QLabel(message)
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet('color: #7f8c8d; font-size: 10pt; padding: 20px;')
        self._set_chart_widget(msg)
        self.table_text.setHtml(markdown_to_html(''))
        self._fit_table_height()
        self._populate_losses({})
        self.insights_label.setText(message)
        self.warning_label.setVisible(False)

    def _build_table_markdown(self, stages):
        start_count = int(stages[0].get('count', 0)) if stages else 0
        lines = [
            '| Этап | Количество | Потеря на этапе | % от старта |',
            '|---|---:|---:|---:|',
        ]
        for i, row in enumerate(stages):
            stage = row.get('name', '')
            count = int(row.get('count', 0))
            loss = '—' if i == 0 else f"-{int(row.get('loss', 0))}"
            pct = (count / start_count * 100.0) if start_count > 0 else 0.0
            lines.append(f'| {stage} | {count} | {loss} | {pct:.1f}% |')
        return '\n'.join(lines)

    def _clear_losses(self):
        while self.losses_layout.count():
            item = self.losses_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._loss_reason_widgets.clear()

    def _populate_losses(self, cancellations_by_stage: dict):
        self._clear_losses()
        title_map = {
            'После подачи': 'После подачи (до загрузки)',
            'После загрузки': 'После загрузки (до доставки)',
            'После доставки': 'После доставки (до закрытия)',
        }
        has_losses = False
        for bucket in ('После подачи', 'После загрузки', 'После доставки'):
            payload = cancellations_by_stage.get(bucket) or {}
            count = int(payload.get('count', 0) or 0)
            if count <= 0:
                continue
            has_losses = True
            section = QFrame()
            section.setStyleSheet(
                'QFrame { background: #ffffff; border: 1px solid #dfe6e9; border-radius: 8px; }'
            )
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(10, 8, 10, 8)
            section_layout.setSpacing(5)

            header = QLabel(f'{title_map.get(bucket, bucket)} — потеряно {count} заявок')
            header.setStyleSheet('font-weight: 700; color: #2c3e50;')
            section_layout.addWidget(header)

            reasons = payload.get('by_reason') or {}
            if reasons:
                for reason, reason_count in reasons.items():
                    row = QLabel(f'• {reason}: {int(reason_count)}')
                    row.setWordWrap(True)
                    row.setStyleSheet('color: #34495e;')
                    section_layout.addWidget(row)
                    self._loss_reason_widgets.append(row)
            else:
                row = QLabel('Причины не определены')
                row.setStyleSheet('color: #7f8c8d;')
                section_layout.addWidget(row)
            self.losses_layout.addWidget(section)

        if not has_losses:
            empty = QLabel('Существенных потерь по этапам отмен не обнаружено.')
            empty.setWordWrap(True)
            empty.setStyleSheet('color: #7f8c8d; padding: 4px 0;')
            self.losses_layout.addWidget(empty)

        self.losses_layout.addStretch(1)

    def _fit_table_height(self):
        doc = self.table_text.document()
        doc.setTextWidth(max(self.table_text.viewport().width(), 1))
        content_h = int(doc.size().height())
        # Делаем таблицу частью общего скролла страницы, без отдельной прокрутки.
        self.table_text.setFixedHeight(max(110, content_h + 16))

    def _build_summary(self, stages: list, cancellations_by_stage: dict):
        if len(stages) < 2:
            return 'Недостаточно данных для определения точки потерь.'
        main_stage = None
        for stage in stages[1:]:
            loss = int(stage.get('loss', 0) or 0)
            if main_stage is None or loss > int(main_stage.get('loss', 0) or 0):
                main_stage = stage
        if main_stage is None or int(main_stage.get('loss', 0) or 0) <= 0:
            return 'Существенных потерь между этапами не обнаружено.'

        stage_name = str(main_stage.get('name', 'этап'))
        stage_loss = int(main_stage.get('loss', 0) or 0)
        bucket_by_stage = {
            'Загружено': 'После подачи',
            'Доставлено': 'После загрузки',
            'Закрыто': 'После доставки',
        }
        bucket = bucket_by_stage.get(stage_name, 'После подачи')
        payload = cancellations_by_stage.get(bucket) or {}
        bucket_count = int(payload.get('count', 0) or 0)
        reasons = payload.get('by_reason') or {}
        if reasons and bucket_count > 0:
            reason, reason_count = max(reasons.items(), key=lambda x: int(x[1] or 0))
            reason_count = int(reason_count or 0)
            reason_pct = (reason_count / bucket_count * 100.0) if bucket_count > 0 else 0.0
            return (
                f'Главная точка потерь: <b>{stage_name}</b> (-{stage_loss} заявок). '
                f'Доминирующая причина: {reason} ({reason_pct:.1f}% потерь на этапе).'
            )
        return (
            f'Главная точка потерь: <b>{stage_name}</b> (-{stage_loss} заявок). '
            'Доминирующая причина: не определена.'
        )

    def on_show(self):
        analyzer = self.parent_main._refresh_analyzer()
        if analyzer is None:
            self._show_no_data('Загрузите файл на главной странице для просмотра воронки.')
            return

        funnel_data = analyzer.get_funnel_data()
        stages = funnel_data.get('stages') or []
        if len(stages) < 2:
            self._show_no_data(self.NO_DATA_MESSAGE)
            return

        missing = []
        if analyzer.cols.get('date_load') is None:
            missing.append('Дата загрузки (плановая)')
        if analyzer.cols.get('date_fact_load') is None:
            missing.append('Дата фактической загрузки')
        if analyzer.cols.get('date_fact_unload') is None:
            missing.append('Дата фактической разгрузки')
        if analyzer.cols.get('date_close') is None:
            missing.append('Дата закрытия')
        if missing:
            self.warning_label.setText(
                'Предупреждение: часть этапов скрыта, отсутствуют столбцы дат: '
                + ', '.join(missing)
                + '.'
            )
            self.warning_label.setVisible(True)
        else:
            self.warning_label.setVisible(False)

        visualizer = Charts(analyzer)
        fig = visualizer.chart_process_funnel(funnel_data)
        canvas = FigureCanvasQTAgg(fig)
        canvas.setFixedHeight(400)
        self._set_chart_widget(canvas)
        self.table_text.setHtml(markdown_to_html(self._build_table_markdown(stages)))
        self._fit_table_height()
        cancellations = funnel_data.get('cancellations_by_stage') or {}
        self._populate_losses(cancellations)
        self.insights_label.setText(self._build_summary(stages, cancellations))
