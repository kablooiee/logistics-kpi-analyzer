# -*- coding: utf-8 -*-
"""Страница выбора группы KPI с отчётом и графиками."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextOption
from PyQt5.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from core.reports import Reports
from core.charts import Charts
from ui.helpers import RESULTS_DOCUMENT_STYLESHEET, markdown_to_html


class AnalysisPage(QWidget):
    """Страница выбора группы KPI с отчётом и графиками."""

    SECTIONS = {
        'financial': {
            'title': 'Финансы',
            'description': 'Выручка, маржа, маржинальность, средний чек по филиалам.',
            'report_method': 'get_financial_report',
            'charts_main': [
                ('chart_margin_by_branch', 'Маржа по филиалам', 'Маржа в рублях и маржинальность в % по каждому филиалу.'),
                ('chart_revenue_dynamics', 'Динамика выручки', 'Динамика суммарной выручки по месяцам.'),
            ],
            'charts_extra': [
                ('chart_avg_check_by_branch', 'Средний чек по филиалам', 'Средний чек по каждому филиалу.'),
                ('chart_margin_pct_distribution', 'Распределение маржинальности', 'Гистограмма распределения маржинальности по заявкам.'),
            ],
        },
        'operational': {
            'title': 'Операции',
            'description': 'Нагрузка менеджеров, типы перевозчиков, структура холостого пробега.',
            'report_method': 'get_operational_report',
            'charts_main': [
                ('chart_top_managers', 'Топ менеджеров', 'ТОП менеджеров по выручке и объёму заявок.'),
                ('chart_carrier_type_comparison', 'Типы перевозчиков', 'Сравнение типов перевозчиков по количеству и маржинальности.'),
            ],
            'charts_extra': [
                ('chart_load_by_branch', 'Нагрузка по филиалам', 'Средняя нагрузка менеджеров по филиалам.'),
                ('chart_empty_km_share', 'Доля холостого пробега', 'Доля холостого пробега по филиалам.'),
            ],
        },
        'quality': {
            'title': 'Качество',
            'description': 'Успешность, причины отмен и распределение качества обработки.',
            'report_method': 'get_quality_report',
            'charts_main': [
                ('chart_cancellation_reasons', 'Причины отмен', 'Структура отмен по категориям причин.'),
                ('chart_success_rate_by_branch', 'Success rate по филиалам', 'Доля успешных и отменённых заявок по филиалам.'),
            ],
            'charts_extra': [
                ('chart_cancellations_by_month', 'Отмены по месяцам', 'Сезонность отмен по месяцам.'),
                ('chart_cancel_fault_split', 'Наша вина vs клиент', 'Разделение отмен по зоне ответственности.'),
            ],
        },
        'timeliness': {
            'title': 'Своевременность',
            'description': 'Длительность сделки, опоздания на погрузке и процент выполнения в срок.',
            'report_method': 'get_timeliness_report',
            'charts_main': [
                ('chart_duration_distribution', 'Распределение длительности', 'Распределение длительности обработки сделок в часах.'),
                ('chart_on_time_by_branch', 'В срок по филиалам', 'Процент заявок в срок на погрузке по филиалам.'),
            ],
            'charts_extra': [
                ('chart_load_delay_distribution', 'Распределение задержек', 'Гистограмма задержек погрузки.'),
                ('chart_duration_by_branch', 'Длительность по филиалам', 'Средняя длительность сделки по филиалам.'),
            ],
        },
    }

    def __init__(self, parent_main):
        super().__init__()
        self.parent_main = parent_main
        self.current_section = 'financial'
        self.section_buttons = {}
        self._canvas_refs = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        btn_home = QPushButton('← Главная')
        btn_home.setObjectName('navButton')
        btn_home.clicked.connect(lambda: self.parent_main.show_page('home'))
        nav.addWidget(btn_home, alignment=Qt.AlignLeft)

        title = QLabel('Анализ KPI')
        title.setStyleSheet('font-size: 16pt; font-weight: 700; color: #1a1a2e;')
        title.setAlignment(Qt.AlignCenter)
        nav.addWidget(title, 1)
        nav.addWidget(QLabel(''), alignment=Qt.AlignRight)
        root.addLayout(nav)

        body = QHBoxLayout()
        body.setSpacing(14)

        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        left_title = QLabel('Группы показателей')
        left_title.setStyleSheet('font-size: 11pt; font-weight: 600; color: #34495e;')
        left_layout.addWidget(left_title)

        self.section_group = QButtonGroup(self)
        self.section_group.setExclusive(True)
        for key in ('financial', 'operational', 'quality', 'timeliness'):
            meta = self.SECTIONS[key]
            btn = QPushButton(meta['title'])
            btn.setObjectName('sectionButton')
            btn.setCheckable(True)
            btn.setFixedHeight(54)
            btn.setStyleSheet('text-align: left; padding-left: 14px; font-size: 11pt;')
            btn.clicked.connect(lambda _=False, sec=key: self.show_section(sec))
            self.section_group.addButton(btn)
            self.section_buttons[key] = btn
            left_layout.addWidget(btn)

        left_layout.addStretch(1)
        self.section_description = QLabel(self.SECTIONS['financial']['description'])
        self.section_description.setWordWrap(True)
        self.section_description.setStyleSheet('font-size: 10pt; color: #7f8c8d;')
        left_layout.addWidget(self.section_description)
        body.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(260)
        self.results_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.results_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.results_text.document().setDefaultStyleSheet(RESULTS_DOCUMENT_STYLESHEET)
        right_layout.addWidget(self.results_text, 1)

        chart_selector_row = QHBoxLayout()
        chart_selector_row.setSpacing(8)
        chart_selector_label = QLabel('Дополнительные графики:')
        chart_selector_label.setStyleSheet('font-size: 10pt; color: #5d6d7e;')
        chart_selector_row.addWidget(chart_selector_label)
        self.extra_chart_combo = QComboBox()
        self.extra_chart_combo.currentIndexChanged.connect(self._on_chart_selection_changed)
        chart_selector_row.addWidget(self.extra_chart_combo, 1)
        right_layout.addLayout(chart_selector_row)

        self.charts_scroll = QScrollArea()
        self.charts_scroll.setWidgetResizable(True)
        self.charts_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.charts_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.charts_container = QWidget()
        self.charts_layout = QVBoxLayout(self.charts_container)
        self.charts_layout.setContentsMargins(0, 0, 0, 0)
        self.charts_layout.setSpacing(10)
        self.charts_scroll.setWidget(self.charts_container)
        right_layout.addWidget(self.charts_scroll, 2)
        body.addWidget(right_panel, 1)

        root.addLayout(body, 1)
        self.section_buttons['financial'].setChecked(True)
        self._show_not_loaded_state()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            child = item.layout()
            if child is not None:
                self._clear_layout(child)

    def _show_not_loaded_state(self):
        self.results_text.setHtml(
            "<div style='color:#7f8c8d; text-align:center; margin-top:40px;'>"
            "Загрузите файл на главной странице"
            "</div>"
        )
        self._clear_layout(self.charts_layout)
        self._canvas_refs.clear()
        self.extra_chart_combo.blockSignals(True)
        self.extra_chart_combo.clear()
        self.extra_chart_combo.addItem('Показать основные', '__main__')
        self.extra_chart_combo.blockSignals(False)
        self.extra_chart_combo.setEnabled(False)

    def set_data_loaded(self, loaded: bool):
        for btn in self.section_buttons.values():
            btn.setEnabled(loaded)
        self.extra_chart_combo.setEnabled(loaded)
        if not loaded:
            self._show_not_loaded_state()

    def _charts_by_section(self, section: str):
        meta = self.SECTIONS.get(section, {})
        main = meta.get('charts_main', [])
        extra = meta.get('charts_extra', [])
        return main, extra

    def _populate_chart_selector(self, section: str):
        main, extra = self._charts_by_section(section)
        self.extra_chart_combo.blockSignals(True)
        self.extra_chart_combo.clear()
        self.extra_chart_combo.addItem('Показать основные', '__main__')
        for method_name, option_label, _caption in main + extra:
            self.extra_chart_combo.addItem(option_label, method_name)
        self.extra_chart_combo.setCurrentIndex(0)
        self.extra_chart_combo.blockSignals(False)
        self.extra_chart_combo.setEnabled(True)

    def _chart_caption_map(self, section: str):
        main, extra = self._charts_by_section(section)
        return {method_name: caption for method_name, _label, caption in main + extra}

    def _render_charts(self, analyzer):
        self._clear_layout(self.charts_layout)
        self._canvas_refs.clear()
        visualizer = Charts(analyzer)
        main, _extra = self._charts_by_section(self.current_section)
        caption_map = self._chart_caption_map(self.current_section)
        selected = self.extra_chart_combo.currentData()
        if selected == '__main__':
            chart_defs = [(method_name, caption_map.get(method_name, '')) for method_name, _label, _caption in main]
            canvas_height = 300
        else:
            chart_defs = [(selected, caption_map.get(selected, ''))]
            canvas_height = 460

        for method_name, caption in chart_defs:
            method = getattr(visualizer, method_name)
            fig = method()
            fig.subplots_adjust(top=0.90, bottom=0.18, left=0.08, right=0.97)
            canvas = FigureCanvasQTAgg(fig)
            canvas.setMinimumHeight(canvas_height)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self._canvas_refs.append(canvas)

            wrapper = QWidget()
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(6, 6, 6, 8)
            wrapper_layout.setSpacing(6)
            wrapper_layout.addWidget(canvas)

            subtitle = QLabel(caption)
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet('font-size: 9pt; color: #7f8c8d;')
            wrapper_layout.addWidget(subtitle)
            self.charts_layout.addWidget(wrapper)
        self.charts_layout.addStretch(1)

    def _on_chart_selection_changed(self, _index: int):
        analyzer = self.parent_main._refresh_analyzer()
        if analyzer is None:
            self._show_not_loaded_state()
            return
        self._render_charts(analyzer)

    def show_section(self, section: str):
        if section not in self.SECTIONS:
            return
        self.current_section = section
        for key, btn in self.section_buttons.items():
            btn.setChecked(key == section)
        self.section_description.setText(self.SECTIONS[section]['description'])

        analyzer = self.parent_main._refresh_analyzer()
        if analyzer is None:
            self._show_not_loaded_state()
            return

        formatter = Reports(analyzer)
        report_method_name = self.SECTIONS[section]['report_method']
        report_method = getattr(formatter, report_method_name)
        report_md = report_method()
        self.results_text.setHtml(markdown_to_html(report_md))
        self._populate_chart_selector(section)
        self._render_charts(analyzer)

    def on_show(self):
        analyzer = self.parent_main._refresh_analyzer()
        if analyzer is None:
            self._show_not_loaded_state()
            return
        self.show_section(self.current_section)
