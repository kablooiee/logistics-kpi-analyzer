# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np


class Charts:
    """Построение графиков по данным Analyzer."""

    COLORS = {
        'blue': '#3498db',
        'green': '#2ecc71',
        'red': '#e74c3c',
        'orange': '#f39c12',
        'purple': '#9b59b6',
        'dark': '#34495e',
    }

    def __init__(self, analyzer):
        self.analyzer = analyzer  # экземпляр Analyzer
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams['font.family'] = ['Segoe UI', 'Arial', 'sans-serif']
        plt.rcParams['axes.titlesize'] = 11
        plt.rcParams['axes.titleweight'] = 'bold'
        plt.rcParams['axes.labelsize'] = 9
        plt.rcParams['xtick.labelsize'] = 8
        plt.rcParams['ytick.labelsize'] = 8

    def _new_figure(self) -> Figure:
        return Figure(figsize=(8, 5), dpi=100)

    def _empty_figure(self, title: str, message: str = 'Недостаточно данных для построения') -> Figure:
        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.set_title(title, fontsize=11)
        ax.text(0.5, 0.5, message, ha='center', va='center', color=self.COLORS['dark'])
        ax.axis('off')
        self._finalize_figure(fig)
        return fig

    def _rotate_xlabels(self, ax):
        labels = ax.get_xticklabels()
        # Поворачиваем подписи только когда названия реально длинные.
        need_rotation = any(len((lbl.get_text() or '').strip()) > 10 for lbl in labels)
        if not need_rotation:
            return
        for lbl in labels:
            lbl.set_rotation(25)
            lbl.set_ha('right')
            lbl.set_fontsize(8)

    def _style_axis(self, ax):
        if ax.get_title():
            ax.set_title(ax.get_title(), fontsize=11)
        if ax.get_xlabel():
            ax.set_xlabel(ax.get_xlabel(), fontsize=9)
        if ax.get_ylabel():
            ax.set_ylabel(ax.get_ylabel(), fontsize=9)
        ax.tick_params(axis='both', labelsize=8)

    def _finalize_figure(self, fig):
        for axis in fig.axes:
            self._style_axis(axis)
        fig.tight_layout(pad=1.2)

    def chart_margin_by_branch(self) -> Figure:
        """Bar chart: маржа и маржинальность по филиалам."""
        fin = self.analyzer.calculate_financial_kpi()
        by_branch = fin.get('by_branch') or {}
        if not by_branch:
            return self._empty_figure('Маржа и маржинальность по филиалам')

        branches = list(by_branch.keys())
        margin = [float(v.get('margin') or 0) for v in by_branch.values()]
        margin_pct = [float(v.get('margin_pct') or 0) for v in by_branch.values()]
        x = np.arange(len(branches))

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax2 = ax.twinx()

        ax.bar(x, margin, color=self.COLORS['blue'], alpha=0.9, label='Маржа, ₽')
        ax2.plot(x, margin_pct, color=self.COLORS['red'], marker='o', linewidth=2, label='Маржинальность, %')

        ax.set_title('Маржа и маржинальность по филиалам')
        ax.set_ylabel('Маржа, ₽')
        ax2.set_ylabel('Маржинальность, %')
        ax.set_xticks(x)
        ax.set_xticklabels(branches)
        self._rotate_xlabels(ax)

        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc='upper right')
        self._finalize_figure(fig)
        return fig

    def chart_cancellation_reasons(self) -> Figure:
        """Donut chart: структура отмен по причинам."""
        qual = self.analyzer.calculate_quality_kpi()
        reasons = qual.get('cancellation_reasons') or {}
        if not reasons:
            return self._empty_figure('Структура отмен по причинам')

        labels = list(reasons.keys())
        values = [int(v.get('count') or 0) for v in reasons.values()]
        total = sum(values)
        if total <= 0:
            return self._empty_figure('Структура отмен по причинам')
        # Проценты считаем отдельно и отдаём в легенду, чтобы подписи не наезжали.
        percentages = [(value / total) * 100 for value in values]
        palette = [
            self.COLORS['blue'], self.COLORS['green'], self.COLORS['red'],
            self.COLORS['orange'], self.COLORS['purple'], self.COLORS['dark'],
        ]

        fig = Figure(figsize=(7, 6), dpi=100)
        ax = fig.add_subplot(111)
        wedges, _ = ax.pie(
            values,
            startangle=90,
            colors=[palette[i % len(palette)] for i in range(len(values))],
            wedgeprops={'width': 0.4, 'edgecolor': 'white'},
        )
        # Держим круг слева, а легенду — в фиксированной зоне справа.
        # Это предотвращает "съезд" donut-графика при изменении ширины окна.
        ax.set_position([0.06, 0.12, 0.60, 0.76])
        ax.legend(
            wedges,
            [f"{label} — {pct:.1f}%" for label, pct in zip(labels, percentages)],
            loc='center left',
            bbox_to_anchor=(1.02, 0.5),
            fontsize=9,
            frameon=False,
            borderaxespad=0.0,
        )
        ax.set_title('Структура отмен по причинам', fontsize=11, pad=12)
        ax.axis('equal')
        # Отдельный tight_layout с запасом справа под легенду.
        self._style_axis(ax)
        fig.tight_layout(rect=(0, 0, 0.88, 1), pad=1.2)
        return fig

    def chart_revenue_dynamics(self) -> Figure:
        """Line chart: выручка по месяцам."""
        d = self.analyzer.df_filtered
        sum_col = self.analyzer.cols.get('sum_customer')
        date_col = self.analyzer._date_column_for_filter()
        if d is None or d.empty or not sum_col or not date_col:
            return self._empty_figure('Динамика выручки по месяцам')

        tmp = d[[date_col, sum_col]].copy()
        tmp[date_col] = tmp[date_col].dropna()
        tmp = tmp.dropna(subset=[date_col])
        if tmp.empty:
            return self._empty_figure('Динамика выручки по месяцам')

        tmp['_month'] = tmp[date_col].dt.to_period('M').astype(str)
        grp = tmp.groupby('_month')[sum_col].sum().sort_index()
        if grp.empty:
            return self._empty_figure('Динамика выручки по месяцам')

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.plot(grp.index.tolist(), grp.values.tolist(), color=self.COLORS['green'], marker='o', linewidth=2)
        ax.set_title('Динамика выручки по месяцам')
        ax.set_ylabel('Выручка, ₽')
        ax.set_xlabel('Период')
        self._rotate_xlabels(ax)
        self._finalize_figure(fig)
        return fig

    def chart_avg_check_by_branch(self) -> Figure:
        """Bar chart: средний чек по филиалам."""
        fin = self.analyzer.calculate_financial_kpi()
        by_branch = fin.get('by_branch') or {}
        if not by_branch:
            return self._empty_figure('Средний чек по филиалам')

        labels = list(by_branch.keys())
        avg_check = [float(v.get('avg_check') or 0) for v in by_branch.values()]
        x = np.arange(len(labels))

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.bar(x, avg_check, color=self.COLORS['green'])
        ax.set_title('Средний чек по филиалам')
        ax.set_ylabel('Средний чек, ₽')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        self._rotate_xlabels(ax)
        self._finalize_figure(fig)
        return fig

    def chart_margin_pct_distribution(self) -> Figure:
        """Histogram: распределение маржинальности по заявкам."""
        d = self.analyzer.df_filtered
        if d is None or d.empty or '_margin_pct' not in d.columns:
            return self._empty_figure('Распределение маржинальности')
        values = d['_margin_pct'].dropna().astype(float)
        if values.empty:
            return self._empty_figure('Распределение маржинальности')

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.hist(values, bins=24, color=self.COLORS['orange'], alpha=0.85, edgecolor='white')
        ax.set_title('Распределение маржинальности, %')
        ax.set_xlabel('Маржинальность, %')
        ax.set_ylabel('Количество заявок')
        self._finalize_figure(fig)
        return fig

    def chart_success_rate_by_branch(self) -> Figure:
        """Horizontal stacked bar: успешные/отменённые по филиалам."""
        qual = self.analyzer.calculate_quality_kpi()
        by_branch = qual.get('success_rate_by_branch') or {}
        if not by_branch:
            return self._empty_figure('Успешные и отменённые по филиалам')

        branches = list(by_branch.keys())
        success = np.array([float(v.get('success_pct') or 0) for v in by_branch.values()])
        canceled = np.clip(100 - success, 0, 100)
        y = np.arange(len(branches))

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.barh(y, success, color=self.COLORS['green'], label='Успешные, %')
        ax.barh(y, canceled, left=success, color=self.COLORS['red'], alpha=0.8, label='Отменённые, %')
        ax.set_title('Успешные/отменённые заявки по филиалам')
        ax.set_xlabel('Доля, %')
        ax.set_yticks(y)
        ax.set_yticklabels(branches)
        ax.legend(loc='lower right')
        self._finalize_figure(fig)
        return fig

    def chart_carrier_type_comparison(self) -> Figure:
        """Grouped bar: количество заявок и маржинальность по типам перевозчика."""
        ops = self.analyzer.calculate_operational_kpi()
        by_type = ops.get('by_carrier_type') or {}
        if not by_type:
            return self._empty_figure('Сравнение типов перевозчика')

        labels = list(by_type.keys())
        orders = [float(v.get('orders') or 0) for v in by_type.values()]
        margin_pct = [float(v.get('avg_margin_pct') or 0) for v in by_type.values()]
        x = np.arange(len(labels))
        width = 0.38

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax2 = ax.twinx()
        ax.bar(x - width / 2, orders, width=width, color=self.COLORS['blue'], label='Заявки, шт')
        ax2.bar(x + width / 2, margin_pct, width=width, color=self.COLORS['orange'], alpha=0.85, label='Маржинальность, %')

        ax.set_title('Типы перевозчика: заявки и маржинальность')
        ax.set_ylabel('Количество заявок')
        ax2.set_ylabel('Маржинальность, %')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        self._rotate_xlabels(ax)

        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc='upper right')
        self._finalize_figure(fig)
        return fig

    def chart_top_managers(self) -> Figure:
        """Horizontal bar: топ-10 менеджеров по выручке."""
        ops = self.analyzer.calculate_operational_kpi()
        top = ops.get('top_managers') or {}
        if not top:
            return self._empty_figure('Топ-10 менеджеров по выручке')

        labels = list(top.keys())[:10]
        revenue = [float(top[name].get('revenue') or 0) for name in labels]
        y = np.arange(len(labels))

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.barh(y, revenue, color=self.COLORS['purple'])
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_title('Топ-10 менеджеров по выручке')
        ax.set_xlabel('Выручка, ₽')
        self._finalize_figure(fig)
        return fig

    def chart_load_by_branch(self) -> Figure:
        """Bar chart: средняя нагрузка менеджеров по филиалам."""
        ops = self.analyzer.calculate_operational_kpi()
        load = ops.get('manager_load_by_branch') or {}
        if not load:
            return self._empty_figure('Нагрузка менеджеров по филиалам')

        labels = list(load.keys())
        avg_load = [float(v.get('avg') or 0) for v in load.values()]
        x = np.arange(len(labels))

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.bar(x, avg_load, color=self.COLORS['blue'])
        ax.set_title('Нагрузка менеджеров по филиалам')
        ax.set_ylabel('Среднее число заявок на менеджера')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        self._rotate_xlabels(ax)
        self._finalize_figure(fig)
        return fig

    def chart_empty_km_share(self) -> Figure:
        """Bar chart: доля холостого пробега по филиалам."""
        d = self.analyzer.df_filtered
        branch_col = self.analyzer.cols.get('branch_customer')
        empty_col = self.analyzer.cols.get('empty_km')
        if d is None or d.empty or not branch_col or not empty_col or '_km_effective' not in d.columns:
            return self._empty_figure('Доля холостого пробега по филиалам')

        tmp = d[[branch_col, empty_col, '_km_effective']].copy()
        tmp[empty_col] = tmp[empty_col].astype(float)
        tmp['_km_effective'] = tmp['_km_effective'].astype(float)
        grouped = tmp.groupby(branch_col).agg(
            empty_km=(empty_col, 'sum'),
            loaded_km=('_km_effective', 'sum'),
        )
        total = grouped['empty_km'] + grouped['loaded_km']
        grouped = grouped[total > 0]
        if grouped.empty:
            return self._empty_figure('Доля холостого пробега по филиалам')
        share = (grouped['empty_km'] / (grouped['empty_km'] + grouped['loaded_km']) * 100).sort_values(ascending=False)

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.bar(share.index.tolist(), share.values.tolist(), color=self.COLORS['purple'])
        ax.set_title('Доля холостого пробега по филиалам')
        ax.set_ylabel('Холостой пробег, %')
        ax.set_ylim(0, 100)
        self._rotate_xlabels(ax)
        self._finalize_figure(fig)
        return fig

    def chart_duration_distribution(self) -> Figure:
        """Histogram: распределение длительности сделки в часах."""
        d = self.analyzer.df_filtered
        if d is None or d.empty or '_duration_h' not in d.columns:
            return self._empty_figure('Распределение длительности сделки')
        values = d['_duration_h'].dropna().astype(float)
        if values.empty:
            return self._empty_figure('Распределение длительности сделки')

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.hist(values, bins=20, color=self.COLORS['dark'], alpha=0.85, edgecolor='white')
        ax.set_title('Распределение длительности сделки (часы)')
        ax.set_xlabel('Часы')
        ax.set_ylabel('Количество заявок')
        self._finalize_figure(fig)
        return fig

    def chart_on_time_by_branch(self) -> Figure:
        """Bar chart: доля рейсов "в срок" по филиалам."""
        d = self.analyzer.df_filtered
        branch_col = self.analyzer.cols.get('branch_customer')
        if d is None or d.empty or not branch_col or '_load_delay_h' not in d.columns:
            return self._empty_figure('Доля рейсов "в срок" по филиалам')

        tmp = d[[branch_col, '_load_delay_h']].dropna(subset=['_load_delay_h'])
        if tmp.empty:
            return self._empty_figure('Доля рейсов "в срок" по филиалам')
        grp = ((tmp['_load_delay_h'] <= 2).groupby(tmp[branch_col]).mean() * 100).sort_values(ascending=False)
        if grp.empty:
            return self._empty_figure('Доля рейсов "в срок" по филиалам')

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.bar(grp.index.tolist(), grp.values.tolist(), color=self.COLORS['green'])
        ax.set_title('Доля рейсов "в срок" по филиалам')
        ax.set_ylabel('В срок, %')
        ax.set_ylim(0, 100)
        self._rotate_xlabels(ax)
        self._finalize_figure(fig)
        return fig

    def chart_cancellations_by_month(self) -> Figure:
        """Line chart: отмены заявок по месяцам."""
        d = self.analyzer.df_filtered
        cancel_col = self.analyzer.cols.get('date_cancel')
        if d is None or d.empty or not cancel_col or cancel_col not in d.columns:
            return self._empty_figure('Отмены по месяцам')

        cancel_dates = d[cancel_col].dropna()
        if cancel_dates.empty:
            return self._empty_figure('Отмены по месяцам')
        months = cancel_dates.dt.to_period('M').astype(str)
        grp = months.value_counts().sort_index()
        if grp.empty:
            return self._empty_figure('Отмены по месяцам')

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.plot(grp.index.tolist(), grp.values.tolist(), color=self.COLORS['red'], marker='o', linewidth=2)
        ax.set_title('Сезонность отмен по месяцам')
        ax.set_xlabel('Месяц')
        ax.set_ylabel('Количество отмен')
        self._rotate_xlabels(ax)
        self._finalize_figure(fig)
        return fig

    def chart_cancel_fault_split(self) -> Figure:
        """Pie chart: отмены по нашей вине vs вине клиента."""
        qual = self.analyzer.calculate_quality_kpi()
        cancel_total = int(qual.get('cancel_count') or 0)
        if cancel_total <= 0:
            return self._empty_figure('Разделение отмен по зонам ответственности')
        our_fault = int(qual.get('cancel_our_fault') or 0)
        client_fault = int(qual.get('cancel_client_fault') or 0)
        other = max(cancel_total - our_fault - client_fault, 0)

        labels = ['Наша вина', 'Вина клиента']
        values = [our_fault, client_fault]
        colors = [self.COLORS['red'], self.COLORS['green']]
        if other > 0:
            labels.append('Прочие/неопределённые')
            values.append(other)
            colors.append(self.COLORS['dark'])

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            wedgeprops={'edgecolor': 'white'},
            textprops={'fontsize': 10},
        )
        ax.set_title('Отмены: наша вина vs клиент')
        ax.axis('equal')
        self._finalize_figure(fig)
        return fig

    def chart_load_delay_distribution(self) -> Figure:
        """Histogram: распределение задержек на погрузке."""
        d = self.analyzer.df_filtered
        if d is None or d.empty or '_load_delay_h' not in d.columns:
            return self._empty_figure('Распределение задержек погрузки')
        values = d['_load_delay_h'].dropna().astype(float)
        if values.empty:
            return self._empty_figure('Распределение задержек погрузки')

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.hist(values, bins=24, color=self.COLORS['orange'], alpha=0.85, edgecolor='white')
        ax.axvline(2, color=self.COLORS['red'], linestyle='--', linewidth=1.6, label='Порог 2 часа')
        ax.set_title('Распределение задержек погрузки (часы)')
        ax.set_xlabel('Отклонение, ч')
        ax.set_ylabel('Количество заявок')
        ax.legend(loc='upper right')
        self._finalize_figure(fig)
        return fig

    def chart_duration_by_branch(self) -> Figure:
        """Bar chart: средняя длительность сделки по филиалам."""
        tim = self.analyzer.calculate_timeliness_kpi()
        by_branch = tim.get('duration_by_branch') or {}
        if not by_branch:
            return self._empty_figure('Длительность сделки по филиалам')

        labels = list(by_branch.keys())
        avg_h = [float(v.get('avg_h') or 0) for v in by_branch.values()]
        x = np.arange(len(labels))

        fig = self._new_figure()
        ax = fig.add_subplot(111)
        ax.bar(x, avg_h, color=self.COLORS['dark'])
        ax.set_title('Средняя длительность сделки по филиалам')
        ax.set_ylabel('Часы')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        self._rotate_xlabels(ax)
        self._finalize_figure(fig)
        return fig

    def chart_process_funnel(self, funnel_data) -> Figure:
        """Горизонтальная воронка процесса по этапам."""
        if not funnel_data or not isinstance(funnel_data, dict):
            return self._empty_figure('Воронка процесса', 'Недостаточно данных для построения воронки')
        stages = funnel_data.get('stages') or []
        if len(stages) < 2:
            return self._empty_figure('Воронка процесса', 'Недостаточно этапов с валидными датами')

        counts = [max(int(s.get('count', 0)), 0) for s in stages]
        start = max(counts[0], 0)
        if start <= 0:
            return self._empty_figure('Воронка процесса', 'Недостаточно данных для построения воронки')

        fig = Figure(figsize=(9, 4.5), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.2, len(stages) + 0.3)
        ax.axis('off')
        ax.set_title('Воронка процесса заявок', fontsize=11, fontweight='bold', color=self.COLORS['dark'])

        c_start = np.array([52, 152, 219]) / 255.0
        c_end = np.array([46, 204, 113]) / 255.0
        colors = []
        denom = max(len(stages) - 1, 1)
        for i in range(len(stages)):
            t = i / denom
            colors.append(tuple(c_start * (1 - t) + c_end * t))

        left_margin = 0.03
        max_width = 0.94
        center_x = left_margin + max_width / 2
        bar_h = 0.72
        widths = [max_width * (c / start) for c in counts]
        y_positions = list(reversed(range(len(stages))))

        for i, stage in enumerate(stages):
            y = y_positions[i] + 0.5
            width = widths[i]
            x0 = center_x - width / 2
            rect = plt.Rectangle(
                (x0, y - bar_h / 2),
                width,
                bar_h,
                facecolor=colors[i],
                edgecolor='white',
                linewidth=1.2,
                zorder=2,
            )
            ax.add_patch(rect)
            ax.text(
                center_x,
                y,
                f"{stage.get('name', '')}\n{counts[i]}",
                ha='center',
                va='center',
                fontsize=9,
                color='white' if width > 0.35 else self.COLORS['dark'],
                fontweight='bold',
                zorder=3,
            )
            loss = int(stage.get('loss', 0) or 0)
            if i > 0 and loss > 0:
                ax.text(
                    center_x,
                    y - bar_h / 2 - 0.14,
                    f"-{loss} заявок",
                    ha='center',
                    va='center',
                    fontsize=8,
                    color=self.COLORS['red'],
                    fontweight='bold',
                    zorder=3,
                )

        fig.tight_layout(pad=1.0)
        return fig
