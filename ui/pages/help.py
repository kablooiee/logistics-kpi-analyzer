# -*- coding: utf-8 -*-
"""Страница справки с описанием, формулами и инструкцией."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTabWidget, QTextBrowser, QVBoxLayout, QWidget

from ui.helpers import RESULTS_DOCUMENT_STYLESHEET


class HelpPage(QWidget):
    """Страница справки с описанием, формулами и инструкцией."""

    def __init__(self, parent_main):
        super().__init__()
        self.parent_main = parent_main
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        btn_home = QPushButton('← Главная')
        btn_home.setObjectName('navButton')
        btn_home.clicked.connect(lambda: self.parent_main.show_page('home'))
        nav.addWidget(btn_home, alignment=Qt.AlignLeft)

        title = QLabel('Помощь')
        title.setStyleSheet('font-size: 16pt; font-weight: 700; color: #1a1a2e;')
        title.setAlignment(Qt.AlignCenter)
        nav.addWidget(title, 1)
        nav.addWidget(QLabel(''), alignment=Qt.AlignRight)
        root.addLayout(nav)

        tabs = QTabWidget()
        tabs.addTab(self._build_text_tab(self._about_html()), 'О программе')
        tabs.addTab(self._build_text_tab(self._formulas_html()), 'Формулы KPI')
        tabs.addTab(self._build_text_tab(self._instruction_html()), 'Инструкция')
        root.addWidget(tabs, 1)

    def _build_text_tab(self, html: str):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.document().setDefaultStyleSheet(
            RESULTS_DOCUMENT_STYLESHEET
            + "\ncode { font-family: Consolas, 'Courier New', monospace; "
            "background: #f4f6f8; padding: 2px 4px; border-radius: 3px; }"
            "\npre { font-family: Consolas, 'Courier New', monospace; "
            "background: #f8fbfd; border: 1px solid #dfe6e9; border-radius: 6px; "
            "padding: 10px; }"
        )
        browser.setHtml(html)
        layout.addWidget(browser)
        return widget

    def _about_html(self) -> str:
        return """
        <h2>О назначении системы</h2>
        <p>
            «Анализатор отчётов» предназначен для анализа эффективности логистических
            бизнес-процессов на основе табличных выгрузок из учётных систем.
        </p>
        <p>
            Программа автоматически распознаёт структуру файла, рассчитывает
            систему KPI по четырём методологическим группам и формирует отчёт
            для управленческого анализа.
        </p>
        <p>
            Принцип работы: загружаете Excel-файл → программа определяет
            столбцы → рассчитывает показатели → представляет результаты
            в виде графиков и таблиц.
        </p>
        <p><strong>Поддерживаемые форматы:</strong> <code>.xlsx</code>, <code>.xls</code>, <code>.json</code></p>
        <h2>Блок-схема процесса использования</h2>
        <ol>
            <li>Открыть файл</li>
            <li>Просмотреть качество данных и сводку</li>
            <li>Выполнить анализ нужной группы KPI</li>
            <li>Изучить аномалии и рекомендации</li>
            <li>Сохранить отчёт</li>
        </ol>
        """

    def _formulas_html(self) -> str:
        return """
        <h2>Группа 1. Финансово-экономические</h2>
        <p><code>Маржа = Сумма заказчика − Сумма перевозчика</code></p>
        <p><code>Маржинальность, % = Маржа / Сумма заказчика × 100</code></p>
        <p><code>Средний чек = Σ Сумма заказчика / Количество заявок</code></p>
        <p><code>Маржа на километр = Σ Маржа / Σ Пробег</code></p>
        <p><code>Доля убыточных = Кол-во заявок с маржой &lt; 0 / Всего</code></p>

        <h2>Группа 2. Операционные</h2>
        <p><code>Нагрузка менеджера = Кол-во заявок / Кол-во менеджеров филиала</code></p>
        <p><code>Доля холостого пробега = Σ Холостой / (Σ Гружёный + Σ Холостой)</code></p>

        <h2>Группа 3. Качество и надёжность</h2>
        <p><code>Success rate = Заявок без отмены и с закрытием / Всего × 100</code></p>
        <p><code>Доля отмен = Заявок с date_cancel / Всего × 100</code></p>

        <h2>Группа 4. Своевременность</h2>
        <p><code>Длительность сделки = Дата закрытия − Дата подачи (часы)</code></p>
        <p><code>Отклонение погрузки = Факт. дата − Плановая дата (часы)</code></p>
        <p><code>Доля "в срок" = Заявок с отклонением ≤ 2ч / Всего × 100</code></p>
        """

    def _instruction_html(self) -> str:
        return """
        <h2>Как начать работу</h2>
        <ol>
            <li>
                Подготовьте Excel-файл с выгрузкой заявок. Программа распознаёт
                столбцы автоматически — название может быть любым из стандартных вариантов.
            </li>
            <li>
                На главной странице нажмите плитку <strong>Данные</strong>, выберите файл.
            </li>
            <li>
                После загрузки на главной появятся карточки качества данных
                и ключевых показателей.
            </li>
        </ol>

        <h2>Какой анализ для чего</h2>
        <ul>
            <li><strong>Финансы</strong> — для оценки прибыльности и сравнения филиалов</li>
            <li><strong>Операции</strong> — для понимания загрузки команды и распределения работы</li>
            <li><strong>Качество</strong> — для анализа отмен и причин потерь</li>
            <li><strong>Своевременность</strong> — для оценки соблюдения графиков</li>
            <li><strong>Аномалии</strong> — для выявления конкретных проблемных заявок</li>
            <li><strong>Воронка</strong> — для понимания, на каком этапе теряются заявки</li>
            <li><strong>Рекомендации</strong> — для получения авто-инсайтов и фиксации собственных выводов</li>
        </ul>

        <h2>Фильтры</h2>
        <p>
            Чтобы анализировать срез данных (один филиал, один месяц и т.д.),
            используйте кнопку <strong>Фильтры</strong>. Применённые фильтры
            отображаются на главной странице.
        </p>
        """
