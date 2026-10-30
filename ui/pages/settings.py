# -*- coding: utf-8 -*-
"""Страница настроек порогов KPI и параметров анализа."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QGroupBox,
)

from core.settings import get_settings


class SettingsPage(QWidget):
    """Страница настроек порогов KPI и параметров анализа."""

    def __init__(self, parent_main):
        super().__init__()
        self.parent_main = parent_main
        self.settings_mgr = get_settings()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        btn_home = QPushButton('← Главная')
        btn_home.setObjectName('navButton')
        btn_home.clicked.connect(lambda: self.parent_main.show_page('home'))
        nav.addWidget(btn_home, alignment=Qt.AlignLeft)

        title = QLabel('Настройки')
        title.setStyleSheet('font-size: 16pt; font-weight: 700; color: #1a1a2e;')
        title.setAlignment(Qt.AlignCenter)
        nav.addWidget(title, 1)
        nav.addWidget(QLabel(''), alignment=Qt.AlignRight)
        root.addLayout(nav)

        thresholds_group = QGroupBox('Пороги KPI')
        thresholds_form = QFormLayout()
        thresholds_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        thresholds_form.setFormAlignment(Qt.AlignTop)
        thresholds_form.setHorizontalSpacing(16)
        thresholds_form.setVerticalSpacing(10)

        self.margin_pct_critical = self._make_double_spin(0, 100, 0.5, '%')
        self.margin_pct_warning = self._make_double_spin(0, 100, 0.5, '%')
        self.load_delay_hours_critical = self._make_double_spin(0, 48, 0.5, ' ч')
        self.load_delay_hours_warning = self._make_double_spin(0, 48, 0.5, ' ч')
        self.success_rate_critical = self._make_double_spin(0, 100, 0.5, '%')
        self.success_rate_warning = self._make_double_spin(0, 100, 0.5, '%')
        self.cancel_rate_critical = self._make_double_spin(0, 100, 0.5, '%')

        self._add_form_row(
            thresholds_form,
            'Критичная маржинальность, %',
            self.margin_pct_critical,
            'Если маржинальность заявки ниже этого значения — она попадёт в раздел проблемных.',
        )
        self._add_form_row(
            thresholds_form,
            'Предупреждение по марже, %',
            self.margin_pct_warning,
            'Граница раннего предупреждения по маржинальности.',
        )
        self._add_form_row(
            thresholds_form,
            'Критичная задержка погрузки, ч',
            self.load_delay_hours_critical,
            'Если средняя задержка выше — показатель считается критичным.',
        )
        self._add_form_row(
            thresholds_form,
            'Предупреждение по задержке, ч',
            self.load_delay_hours_warning,
            'Порог предупреждения по отклонению от плановой погрузки.',
        )
        self._add_form_row(
            thresholds_form,
            'Минимальный success rate, %',
            self.success_rate_critical,
            'Нижняя граница допустимого уровня успешных заявок.',
        )
        self._add_form_row(
            thresholds_form,
            'Норма success rate, %',
            self.success_rate_warning,
            'Целевой уровень успешных заявок без отмен.',
        )
        self._add_form_row(
            thresholds_form,
            'Критичная доля отмен, %',
            self.cancel_rate_critical,
            'Если доля отмен выше этого значения — необходимы корректирующие меры.',
        )
        thresholds_group.setLayout(thresholds_form)
        root.addWidget(thresholds_group)

        analysis_group = QGroupBox('Анализ')
        analysis_form = QFormLayout()
        analysis_form.setHorizontalSpacing(16)
        analysis_form.setVerticalSpacing(10)
        self.anomalies_limit = self._make_int_spin(1, 100, 5)
        self.max_rows = self._make_int_spin(100, 500000, 100)

        self._add_form_row(
            analysis_form,
            'Записей на категорию аномалий',
            self.anomalies_limit,
            'Ограничивает количество проблемных заявок в каждой категории.',
        )
        self._add_form_row(
            analysis_form,
            'Лимит строк анализа',
            self.max_rows,
            'Максимальное число строк, которое будет обрабатываться в расчётах.',
        )
        analysis_group.setLayout(analysis_form)
        root.addWidget(analysis_group)

        ui_group = QGroupBox('Интерфейс')
        ui_form = QFormLayout()
        ui_form.setHorizontalSpacing(16)
        ui_form.setVerticalSpacing(10)
        self.dark_theme = QCheckBox('Включить тёмную тему')
        self.font_size = self._make_int_spin(9, 16, 1)
        self._add_form_row(
            ui_form,
            'Тёмная тема',
            self.dark_theme,
            'Пока подготовительный параметр. В будущем влияет на оформление интерфейса.',
        )
        self._add_form_row(
            ui_form,
            'Размер шрифта',
            self.font_size,
            'Базовый размер шрифта интерфейса для последующих запусков.',
        )
        ui_group.setLayout(ui_form)
        root.addWidget(ui_group)

        actions = QHBoxLayout()
        actions.addStretch(1)
        btn_save = QPushButton('Сохранить')
        btn_save.setObjectName('primaryButton')
        btn_save.clicked.connect(self.save_click)
        actions.addWidget(btn_save)

        btn_defaults = QPushButton('По умолчанию')
        btn_defaults.clicked.connect(self.reset_click)
        actions.addWidget(btn_defaults)

        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(lambda: self.parent_main.show_page('home'))
        actions.addWidget(btn_cancel)
        root.addLayout(actions)

    def _make_double_spin(self, minimum, maximum, step, suffix=''):
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(1)
        spin.setSuffix(suffix)
        spin.setMinimumWidth(170)
        return spin

    def _make_int_spin(self, minimum, maximum, step):
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setMinimumWidth(170)
        return spin

    def _add_form_row(self, form: QFormLayout, label_text: str, control: QWidget, hint: str):
        wrapper = QWidget()
        v = QVBoxLayout(wrapper)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        v.addWidget(control)
        hint_lbl = QLabel(hint)
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet('font-size: 9pt; color: #7f8c8d;')
        v.addWidget(hint_lbl)
        form.addRow(QLabel(label_text), wrapper)

    def on_show(self):
        cfg = self.settings_mgr.load() or {}
        thresholds = cfg.get('thresholds', {}) or {}
        analysis = cfg.get('analysis', {}) or {}
        ui = cfg.get('ui', {}) or {}

        self.margin_pct_critical.setValue(float(thresholds.get('margin_pct_critical', 20.0)))
        self.margin_pct_warning.setValue(float(thresholds.get('margin_pct_warning', 25.0)))
        self.load_delay_hours_critical.setValue(float(thresholds.get('load_delay_hours_critical', 4.0)))
        self.load_delay_hours_warning.setValue(float(thresholds.get('load_delay_hours_warning', 2.0)))
        self.success_rate_critical.setValue(float(thresholds.get('success_rate_critical', 70.0)))
        self.success_rate_warning.setValue(float(thresholds.get('success_rate_warning', 80.0)))
        self.cancel_rate_critical.setValue(float(thresholds.get('cancel_rate_critical', 15.0)))
        self.anomalies_limit.setValue(int(analysis.get('anomalies_limit', 10)))
        self.max_rows.setValue(int(analysis.get('max_rows', 100000)))
        self.dark_theme.setChecked(bool(ui.get('dark_theme', False)))
        self.font_size.setValue(int(ui.get('font_size', 11)))

    def save_click(self):
        cfg = self.settings_mgr.load() or {}
        cfg.setdefault('thresholds', {})
        cfg.setdefault('analysis', {})
        cfg.setdefault('ui', {})

        cfg['thresholds']['margin_pct_critical'] = float(self.margin_pct_critical.value())
        cfg['thresholds']['margin_pct_warning'] = float(self.margin_pct_warning.value())
        cfg['thresholds']['load_delay_hours_critical'] = float(self.load_delay_hours_critical.value())
        cfg['thresholds']['load_delay_hours_warning'] = float(self.load_delay_hours_warning.value())
        cfg['thresholds']['success_rate_critical'] = float(self.success_rate_critical.value())
        cfg['thresholds']['success_rate_warning'] = float(self.success_rate_warning.value())
        cfg['thresholds']['cancel_rate_critical'] = float(self.cancel_rate_critical.value())
        cfg['analysis']['anomalies_limit'] = int(self.anomalies_limit.value())
        cfg['analysis']['max_rows'] = int(self.max_rows.value())
        cfg['ui']['dark_theme'] = bool(self.dark_theme.isChecked())
        cfg['ui']['font_size'] = int(self.font_size.value())

        self.settings_mgr.save(cfg)
        self.parent_main._reset_cache()
        QMessageBox.information(self, 'Готово', 'Настройки сохранены')
        self.parent_main.show_page('home')

    def reset_click(self):
        self.settings_mgr.reset_to_defaults()
        self.on_show()
