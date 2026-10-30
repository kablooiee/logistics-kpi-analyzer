# -*- coding: utf-8 -*-
"""Формирование markdown- и PDF-отчётов."""

import math
from typing import Optional

import pandas as pd

from core.analyzer import Analyzer
from core.formulas import format_money, format_percentage


class Reports:
    """Форматтер markdown-отчётов на основе данных Analyzer."""

    def __init__(self, analyzer: Analyzer):
        self.analyzer = analyzer

    def _render_financial_markdown(self, fin: dict) -> list:
        lines = ["## Финансово-экономические показатели"]
        if not fin:
            lines.append("- *нет данных*")
            return lines

        lines.append("")
        lines.append("**Общие итоги:**")
        lines.append(f"- Выручка (сумма заказчика): **{format_money(fin['total_revenue'])}**")
        lines.append(f"- Затраты (сумма перевозчика): **{format_money(fin['total_cost'])}**")
        lines.append(f"- Маржа: **{format_money(fin['total_margin'])}**")
        lines.append(f"- Маржинальность (общая): **{format_percentage(fin['margin_pct_total'])}**")
        lines.append(f"- Средний чек: **{format_money(fin['avg_check'])}**")
        lines.append(
            f"- Убыточных заявок: **{fin['loss_orders_count']}** "
            f"({format_percentage(fin['loss_orders_pct'])} от общего числа)"
        )

        if 'by_branch' in fin:
            lines.append("")
            lines.append("**По филиалам (отсортированы по марже):**")
            lines.append("")
            lines.append("| Филиал | Заявок | Выручка | Маржа | Маржинальность |")
            lines.append("|---|---:|---:|---:|---:|")
            for br, row in fin['by_branch'].items():
                lines.append(
                    f"| {br} | {int(row['count'])} "
                    f"| {format_money(row['revenue'])} "
                    f"| {format_money(row['margin'])} "
                    f"| {format_percentage(row['margin_pct'])} |"
                )

        if 'margin_per_km_by_branch' in fin:
            lines.append("")
            lines.append("**Средняя маржа на километр пробега по филиалам:**")
            for br, val in sorted(fin['margin_per_km_by_branch'].items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- {br}: **{val:.2f} ₽/км**")
        return lines

    def _render_operational_markdown(self, ops: dict) -> list:
        lines = ["## Операционные показатели"]
        if not ops:
            lines.append("- *нет данных*")
            return lines

        if 'manager_load_by_branch' in ops:
            lines.append("")
            lines.append("**Нагрузка менеджеров по филиалам:**")
            lines.append("")
            lines.append("| Филиал | Менеджеров | Средняя нагрузка | Мин | Макс |")
            lines.append("|---|---:|---:|---:|---:|")
            for br, row in ops['manager_load_by_branch'].items():
                lines.append(
                    f"| {br} | {row['managers_count']} | {row['avg']:.1f} "
                    f"| {row['min']} | {row['max']} |"
                )

        if 'empty_km_share_pct' in ops:
            lines.append("")
            lines.append(f"**Доля холостого пробега:** {format_percentage(ops['empty_km_share_pct'])}")
            lines.append(f"- Гружёный пробег: {ops['total_loaded_km']:,.0f} км".replace(",", " "))
            lines.append(f"- Холостой пробег: {ops['total_empty_km']:,.0f} км".replace(",", " "))

        if 'by_carrier_type' in ops:
            lines.append("")
            lines.append("**По типам перевозчиков:**")
            lines.append("")
            lines.append("| Тип | Заявок | Выручка | Средняя маржинальность |")
            lines.append("|---|---:|---:|---:|")
            for ct, row in ops['by_carrier_type'].items():
                mp = row.get('avg_margin_pct')
                mp_str = format_percentage(mp) if pd.notna(mp) else "—"
                lines.append(
                    f"| {ct} | {int(row['orders'])} "
                    f"| {format_money(row['revenue'])} | {mp_str} |"
                )

        if 'top_managers' in ops:
            lines.append("")
            lines.append("**ТОП-10 менеджеров по выручке:**")
            lines.append("")
            lines.append("| Менеджер | Заявок | Выручка |")
            lines.append("|---|---:|---:|")
            for m, row in ops['top_managers'].items():
                lines.append(f"| {m} | {int(row['orders'])} | {format_money(row['revenue'])} |")
        return lines

    def _render_quality_markdown(self, qual: dict) -> list:
        lines = ["## Качество и надёжность"]
        if not qual:
            lines.append("- *нет данных*")
            return lines

        if 'success_rate_total' in qual:
            lines.append("")
            lines.append(
                f"**Общая успешность:** {format_percentage(qual['success_rate_total'])} "
                f"({qual['successful_count']} из {qual['total_count']})"
            )

        if 'success_rate_by_branch' in qual:
            lines.append("")
            lines.append("**Коэффициент успешной обработки по филиалам:**")
            for br, row in sorted(qual['success_rate_by_branch'].items(), key=lambda x: x[1].get('success_pct', 0), reverse=True):
                lines.append(f"- {br}: **{format_percentage(row['success_pct'])}** ({row['orders']} заявок)")

        if 'cancellation_reasons' in qual:
            lines.append("")
            lines.append(
                f"**Структура отмен** (всего отменено: {qual['cancel_count']}, "
                f"{format_percentage(qual['cancel_rate_pct'])} от всех заявок):"
            )
            lines.append("")
            lines.append("| Причина | Количество (доля) |")
            lines.append("|---|---:|")
            for reason, row in qual['cancellation_reasons'].items():
                lines.append(f"| {reason} | {row['count']} ({format_percentage(row['pct'])}) |")

            if 'cancel_our_fault' in qual:
                lines.append("")
                lines.append(f"- Отмены по нашей вине: **{qual['cancel_our_fault']}**")
                lines.append(f"- Отмены по вине клиента: **{qual['cancel_client_fault']}**")

        if 'geocontrol_share_pct' in qual:
            lines.append("")
            lines.append(f"Доля рейсов с геоконтролем: **{format_percentage(qual['geocontrol_share_pct'])}**")
        return lines

    def _render_timeliness_markdown(self, tim: dict) -> list:
        lines = ["## Показатели своевременности"]
        if not tim:
            lines.append("- *нет данных по времени*")
            return lines

        if 'duration_h_avg' in tim:
            lines.append("")
            lines.append("**Длительность обработки заявки (от подачи до закрытия):**")
            lines.append(f"- Среднее: **{tim['duration_h_avg']:.1f} ч**")
            lines.append(f"- Медиана: **{tim['duration_h_median']:.1f} ч**")
            lines.append(f"- 90-й перцентиль: **{tim['duration_h_p90']:.1f} ч**")
            lines.append(f"- Закрыто за сутки: **{format_percentage(tim['fast_close_pct'])}**")

        if 'load_delay_h_avg' in tim:
            lines.append("")
            lines.append("**Своевременность погрузки:**")
            lines.append(f"- Среднее отклонение от плановой даты: **{tim['load_delay_h_avg']:+.1f} ч**")
            lines.append(f"- Доля «в срок» (отклонение <= 2 ч): **{format_percentage(tim['on_time_load_pct'])}**")
            lines.append(f"- Заявок с опозданием: **{tim['late_count']}**")

        if 'duration_by_branch' in tim:
            lines.append("")
            lines.append("**Средняя длительность по филиалам:**")
            for br, row in sorted(tim['duration_by_branch'].items(), key=lambda x: x[1].get('avg_h', 0)):
                lines.append(
                    f"- {br}: **{row['avg_h']:.1f} ч** "
                    f"(медиана {row['median_h']:.1f} ч, {row['count']} заявок)"
                )
        return lines

    def get_financial_report(self) -> str:
        lines = ["# Финансовый анализ", ""]
        lines.extend(self._render_financial_markdown(self.analyzer.calculate_financial_kpi()))
        return "\n".join(lines)

    def get_operational_report(self) -> str:
        lines = ["# Операционный анализ", ""]
        lines.extend(self._render_operational_markdown(self.analyzer.calculate_operational_kpi()))
        return "\n".join(lines)

    def get_quality_report(self) -> str:
        lines = ["# Анализ качества и надёжности", ""]
        lines.extend(self._render_quality_markdown(self.analyzer.calculate_quality_kpi()))
        return "\n".join(lines)

    def get_timeliness_report(self) -> str:
        lines = ["# Анализ своевременности", ""]
        lines.extend(self._render_timeliness_markdown(self.analyzer.calculate_timeliness_kpi()))
        return "\n".join(lines)

    def get_kpi_report(self) -> str:
        kpi = self.analyzer.calculate_all_kpi()
        lines = ["# АНАЛИЗ ОТЧЁТОВ ЛОГИСТИЧЕСКОЙ КОМПАНИИ", ""]

        if kpi.get('warnings'):
            lines.append("> **Замечания по данным:**")
            for w in kpi['warnings']:
                lines.append(f"> - {w}")
            lines.append("")

        lines.append(f"*Проанализировано записей: **{kpi['rows_analyzed']}***")
        lines.append("")

        lines.append("## 1. Финансово-экономические показатели")
        lines.extend(self._render_financial_markdown(kpi.get('financial', {}))[1:])
        lines.append("")

        lines.append("## 2. Операционные показатели")
        lines.extend(self._render_operational_markdown(kpi.get('operational', {}))[1:])
        lines.append("")

        lines.append("## 3. Качество и надёжность")
        lines.extend(self._render_quality_markdown(kpi.get('quality', {}))[1:])
        lines.append("")

        lines.append("## 4. Показатели своевременности")
        lines.extend(self._render_timeliness_markdown(kpi.get('timeliness', {}))[1:])
        lines.append("")
        lines.append("---")
        lines.append("*Нажмите «Показать статистику» для общей сводки по данным*")
        return "\n".join(lines)


def _flatten_period_metrics(kpi: dict) -> dict:
    fin = kpi.get('financial') or {}
    qual = kpi.get('quality') or {}
    tim = kpi.get('timeliness') or {}
    return {
        'total_revenue': fin.get('total_revenue'),
        'total_margin': fin.get('total_margin'),
        'margin_pct_total': fin.get('margin_pct_total'),
        'success_rate_total': qual.get('success_rate_total'),
        'cancel_rate_pct': qual.get('cancel_rate_pct'),
        'on_time_load_pct': tim.get('on_time_load_pct'),
        'duration_h_avg': tim.get('duration_h_avg'),
        'rows_count': float(kpi.get('rows_analyzed') or 0),
    }


def _fmt_compare_cell(key: str, value) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return '—'
    if key in ('total_revenue', 'total_margin'):
        try:
            return f"{float(value):,.0f}".replace(',', ' ') + ' ₽'
        except (TypeError, ValueError):
            return '—'
    if key in ('margin_pct_total', 'success_rate_total', 'cancel_rate_pct', 'on_time_load_pct'):
        try:
            return f"{float(value):.1f}%"
        except (TypeError, ValueError):
            return '—'
    if key == 'duration_h_avg':
        try:
            return f"{float(value):.1f} ч"
        except (TypeError, ValueError):
            return '—'
    if key == 'rows_count':
        try:
            return str(int(round(float(value))))
        except (TypeError, ValueError):
            return '—'
    return str(value)


def _delta_arrow(delta: float, inverted: bool) -> str:
    if delta is None or (isinstance(delta, float) and (math.isnan(delta) or math.isinf(delta))):
        return '—'
    if abs(delta) < 1e-9:
        return '→'
    pos = delta > 0
    if inverted:
        return '↑' if not pos else '↓'
    return '↑' if pos else '↓'


def _pct_vs_a(a: float, b: float) -> Optional[float]:
    if a is None or b is None:
        return None
    try:
        a = float(a)
        b = float(b)
    except (TypeError, ValueError):
        return None
    if abs(a) < 1e-12:
        return None
    return (b - a) / a * 100.0


def compare_periods(
    json_filepath: str,
    period_a: dict,
    period_b: dict,
    base_filters: Optional[dict] = None,
    max_rows: int = 20000,
) -> str:
    rows_meta = [
        ('total_revenue', 'Выручка (сумма заказчика)', False),
        ('total_margin', 'Маржа, ₽', False),
        ('margin_pct_total', 'Маржинальность, %', False),
        ('success_rate_total', 'Успешность, %', False),
        ('cancel_rate_pct', 'Доля отмен, %', True),
        ('on_time_load_pct', 'В срок на погрузке, %', False),
        ('duration_h_avg', 'Средняя длительность сделки, ч', True),
        ('rows_count', 'Число записей в срезе', False),
    ]

    try:
        analyzer = Analyzer(json_filepath, max_rows=max_rows)
    except Exception as e:
        return f'# ❌ Ошибка сравнения периодов\n\n{e}'

    def run_slice(period: dict) -> dict:
        # Каждый период считаем отдельно на одном и том же наборе базовых фильтров.
        analyzer.clear_filters()
        extra = base_filters or {}
        filters = {
            'date_from': period.get('date_from'),
            'date_to': period.get('date_to'),
            'branch': extra.get('branch'),
            'manager': extra.get('manager'),
            'carrier_type': extra.get('carrier_type'),
        }
        analyzer.apply_filters(filters)
        return analyzer.calculate_all_kpi()

    kpi_a = run_slice(period_a)
    kpi_b = run_slice(period_b)
    flat_a = _flatten_period_metrics(kpi_a)
    flat_b = _flatten_period_metrics(kpi_b)

    def fmt_period(p: dict) -> str:
        df, dt = p.get('date_from'), p.get('date_to')
        if df is None and dt is None:
            return '—'
        ds = df.strftime('%d.%m.%Y') if df else '…'
        de = dt.strftime('%d.%m.%Y') if dt else '…'
        return f'{ds} — {de}'

    lines = [
        '# Сравнение двух периодов (KPI)',
        '',
        f'- **Период A:** {fmt_period(period_a)}',
        f'- **Период B:** {fmt_period(period_b)}',
        '',
        '| Показатель | Период A | Период B | Изменение | % |',
        '|---|---:|---:|---:|---:|',
    ]

    for key, title, inverted in rows_meta:
        va, vb = flat_a.get(key), flat_b.get(key)
        sa = _fmt_compare_cell(key, va)
        sb = _fmt_compare_cell(key, vb)

        try:
            fa = float(va) if va is not None else None
            fb = float(vb) if vb is not None else None
        except (TypeError, ValueError):
            fa = fb = None

        if fa is not None and fb is not None:
            d = fb - fa
            arrow = _delta_arrow(d, inverted)
            if key in ('total_revenue', 'total_margin'):
                ch = f'{arrow} {d:+,.0f}'.replace(',', ' ') + ' ₽'
            elif key == 'rows_count':
                ch = f'{arrow} {int(round(d)):+d}'
            elif key == 'duration_h_avg':
                ch = f'{arrow} {d:+.1f} ч'
            else:
                ch = f'{arrow} {d:+.1f} п.п.'
            pct = _pct_vs_a(fa, fb)
            pct_s = f'{pct:+.1f}%' if pct is not None else '—'
        else:
            ch = '—'
            pct_s = '—'

        lines.append(f'| {title} | {sa} | {sb} | {ch} | {pct_s} |')

    lines.extend(['', '*Дельта и %: период B относительно A.*'])
    return '\n'.join(lines)

import html
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class Pdf:
    """Сборка итогового PDF-отчёта по KPI."""

    CARD_STATUS_COLORS = {
        'good': colors.HexColor('#E8F8F0'),
        'warning': colors.HexColor('#FEF5E7'),
        'critical': colors.HexColor('#FDECEA'),
        'neutral': colors.HexColor('#F4F6F6'),
    }

    DEFAULT_IMG_WIDTH = 14 * cm
    DEFAULT_IMG_HEIGHT = 7 * cm
    SQUARE_IMG_WIDTH = 12 * cm
    SQUARE_IMG_HEIGHT = 9 * cm

    def __init__(self, analyzer, visualizer, settings, file_hash=None):
        self.analyzer = analyzer
        self.visualizer = visualizer
        self.settings = settings
        self.file_hash = file_hash
        self._tmp_images = []
        self._register_fonts()
        self._init_styles()

    def _register_fonts(self):
        self.main_font = 'Helvetica'
        self.main_font_bold = 'Helvetica-Bold'
        font_paths = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/calibri.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/Library/Fonts/Arial.ttf',
        ]
        for path in font_paths:
            if not os.path.exists(path):
                continue
            pdfmetrics.registerFont(TTFont('MainFont', path))
            self.main_font = 'MainFont'
            bold_path = path.replace('.ttf', 'bd.ttf').replace('arial', 'arialbd')
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont('MainFontBold', bold_path))
                self.main_font_bold = 'MainFontBold'
            else:
                self.main_font_bold = self.main_font
            break

    def _init_styles(self):
        styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontName=self.main_font_bold,
            fontSize=18,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=0.3 * cm,
        )
        self.h1_style = ParagraphStyle(
            'H1',
            fontName=self.main_font_bold,
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=0.4 * cm,
            spaceAfter=0.2 * cm,
        )
        self.p_style = ParagraphStyle(
            'P',
            fontName=self.main_font,
            fontSize=10,
            leading=14,
            spaceAfter=0.15 * cm,
        )
        self.meta_style = ParagraphStyle(
            'Meta',
            fontName=self.main_font,
            fontSize=9,
            textColor=colors.HexColor('#7f8c8d'),
        )
        self.card_label_style = ParagraphStyle(
            'CardLabel',
            fontName=self.main_font,
            fontSize=8,
            textColor=colors.HexColor('#7f8c8d'),
            leading=10,
        )
        self.card_value_style = ParagraphStyle(
            'CardValue',
            fontName=self.main_font_bold,
            fontSize=12,
            textColor=colors.HexColor('#1f2d3d'),
            leading=14,
        )
        self.card_comment_style = ParagraphStyle(
            'CardComment',
            fontName=self.main_font,
            fontSize=7.5,
            textColor=colors.HexColor('#95a5a6'),
            leading=9,
        )

    @staticmethod
    def format_money(value) -> str:
        try:
            return f"{float(value):,.0f} ₽".replace(',', ' ')
        except (TypeError, ValueError):
            return '—'

    def _safe(self, value) -> str:
        return html.escape(str(value if value is not None else '—'))

    def _meta_period(self) -> str:
        d = self.analyzer.df_filtered
        if d is None or d.empty:
            return '—'
        date_col = self.analyzer._date_column_for_filter()
        if not date_col or date_col not in d.columns:
            return '—'
        series = d[date_col].dropna()
        if series.empty:
            return '—'
        dmin = series.min()
        dmax = series.max()
        try:
            return f"{dmin.strftime('%d.%m.%Y')} — {dmax.strftime('%d.%m.%Y')}"
        except Exception:
            return '—'

    def _save_figure(self, fig, name) -> str:
        tmp_dir = os.path.join('data', 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        file_name = f"{name}_{len(self._tmp_images)}.png"
        path = os.path.join(tmp_dir, file_name)
        # Сохраняем с умеренным DPI и полями, чтобы подписи графиков не обрезались в PDF.
        fig.savefig(path, dpi=130, bbox_inches='tight', pad_inches=0.3)
        self._tmp_images.append(path)
        return path

    def _cleanup_tmp_images(self):
        for path in self._tmp_images:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self._tmp_images.clear()

    def _append_figure(
        self,
        story,
        fig,
        name,
        width=DEFAULT_IMG_WIDTH,
        height=DEFAULT_IMG_HEIGHT,
    ):
        img_path = self._save_figure(fig, name)
        story.append(Spacer(1, 0.25 * cm))
        story.append(Image(img_path, width=width, height=height))
        story.append(Spacer(1, 0.5 * cm))

    def _table_style(self, has_row_bg=True):
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.main_font_bold),
            ('FONTNAME', (0, 1), (-1, -1), self.main_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d6dc')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        if has_row_bg:
            style.append(
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafbfc')])
            )
        return TableStyle(style)

    def build_pdf(self, sections, output_path, report_title):
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        story = []
        story.append(Paragraph(self._safe(report_title), self.title_style))

        records_total = len((self.analyzer.data or {}).get('records') or [])
        meta = (
            f"Период: {self._meta_period()} | Записей: {records_total} | "
            f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        story.append(Paragraph(self._safe(meta), self.meta_style))
        story.append(Spacer(1, 0.5 * cm))

        handlers = {
            'summary': self._add_summary,
            'financial': self._add_financial,
            'operational': self._add_operational,
            'quality': self._add_quality,
            'timeliness': self._add_timeliness,
            'anomalies': self._add_anomalies,
            'recommendations': self._add_recommendations,
            'analyst_notes': self._add_analyst_notes,
        }

        added_any = False
        for section in sections or []:
            handler = handlers.get(section)
            if handler is None:
                continue
            # Каждый раздел начинаем с новой страницы, но только после первого добавленного блока.
            if added_any:
                story.append(PageBreak())
            handler(story)
            added_any = True

        try:
            doc.build(story)
        finally:
            self._cleanup_tmp_images()

    def _add_summary(self, story):
        story.append(Paragraph('Ключевые показатели', self.h1_style))
        cards = self.analyzer.get_summary_cards() or []
        if not cards:
            story.append(Paragraph('Нет данных для формирования сводки.', self.p_style))
            return

        rows = [[], []]
        backgrounds = []
        for i in range(8):
            row, col = divmod(i, 4)
            if i < len(cards):
                card = cards[i]
                label = self._safe(card.get('label', ''))
                value = self._safe(card.get('value', '—'))
                comment = self._safe(card.get('comment', ''))
                cell = (
                    f"<para><font size='8'>{label}</font><br/>"
                    f"<font size='12'><b>{value}</b></font><br/>"
                    f"<font size='7'>{comment}</font></para>"
                )
                rows[row].append(Paragraph(cell, self.p_style))
                status = str(card.get('status', 'neutral'))
                backgrounds.append((row, col, self.CARD_STATUS_COLORS.get(status, self.CARD_STATUS_COLORS['neutral'])))
            else:
                rows[row].append(Paragraph('', self.p_style))

        table = Table(rows, colWidths=[4 * cm] * 4, rowHeights=[3 * cm] * 2)
        style = [
            ('FONTNAME', (0, 0), (-1, -1), self.main_font),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d6dc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]
        for row, col, color in backgrounds:
            style.append(('BACKGROUND', (col, row), (col, row), color))
        table.setStyle(TableStyle(style))
        story.append(table)

    def _add_financial(self, story):
        story.append(Paragraph('1. Финансовый анализ', self.h1_style))
        kpi = self.analyzer.calculate_financial_kpi() or {}
        if not kpi:
            story.append(Paragraph('Нет данных для финансового анализа.', self.p_style))
            return

        story.append(Paragraph(f"<b>Выручка:</b> {self.format_money(kpi.get('total_revenue'))}", self.p_style))
        story.append(Paragraph(f"<b>Маржа:</b> {self.format_money(kpi.get('total_margin'))}", self.p_style))
        story.append(
            Paragraph(f"<b>Маржинальность:</b> {float(kpi.get('margin_pct_total') or 0):.1f}%", self.p_style)
        )
        story.append(Paragraph(f"<b>Средний чек:</b> {self.format_money(kpi.get('avg_check'))}", self.p_style))
        story.append(Spacer(1, 0.2 * cm))

        by_branch = kpi.get('by_branch') or {}
        if by_branch:
            data = [['Филиал', 'Заявок', 'Выручка', 'Маржа', 'Маржинальность']]
            for branch, row in by_branch.items():
                data.append([
                    self._safe(branch),
                    str(int(row.get('count') or 0)),
                    self.format_money(row.get('revenue')),
                    self.format_money(row.get('margin')),
                    f"{float(row.get('margin_pct') or 0):.1f}%",
                ])
            t = Table(data, colWidths=[3.5 * cm, 2 * cm, 3.5 * cm, 3.5 * cm, 3 * cm])
            t.setStyle(self._table_style())
            story.append(t)

        fig = self.visualizer.chart_margin_by_branch()
        self._append_figure(story, fig, 'fin_margin')

    def _add_operational(self, story):
        story.append(Paragraph('2. Операционный анализ', self.h1_style))
        kpi = self.analyzer.calculate_operational_kpi() or {}
        if not kpi:
            story.append(Paragraph('Нет данных для операционного анализа.', self.p_style))
            return

        empty_share = float(kpi.get('empty_km_share_pct') or 0.0)
        story.append(Paragraph(f"<b>Доля холостого пробега:</b> {empty_share:.1f}%", self.p_style))
        story.append(
            Paragraph(
                f"<b>Гружёный пробег:</b> {float(kpi.get('total_loaded_km') or 0):,.0f} км".replace(',', ' '),
                self.p_style,
            )
        )
        story.append(
            Paragraph(
                f"<b>Холостой пробег:</b> {float(kpi.get('total_empty_km') or 0):,.0f} км".replace(',', ' '),
                self.p_style,
            )
        )
        top = kpi.get('top_managers') or {}
        if top:
            story.append(Spacer(1, 0.2 * cm))
            data = [['Менеджер', 'Заявок', 'Выручка']]
            for name, row in list(top.items())[:10]:
                data.append([
                    self._safe(name),
                    str(int(row.get('orders') or 0)),
                    self.format_money(row.get('revenue')),
                ])
            t = Table(data, colWidths=[6 * cm, 3 * cm, 5 * cm])
            t.setStyle(self._table_style())
            story.append(t)

        fig = self.visualizer.chart_top_managers()
        self._append_figure(
            story,
            fig,
            'ops_top',
            width=self.SQUARE_IMG_WIDTH,
            height=self.SQUARE_IMG_HEIGHT,
        )

    def _add_quality(self, story):
        story.append(Paragraph('3. Анализ качества', self.h1_style))
        kpi = self.analyzer.calculate_quality_kpi() or {}
        if not kpi:
            story.append(Paragraph('Нет данных для анализа качества.', self.p_style))
            return

        story.append(
            Paragraph(
                f"<b>Success rate:</b> {float(kpi.get('success_rate_total') or 0):.1f}% "
                f"({int(kpi.get('successful_count') or 0)} из {int(kpi.get('total_count') or 0)})",
                self.p_style,
            )
        )
        story.append(
            Paragraph(
                f"<b>Доля отмен:</b> {float(kpi.get('cancel_rate_pct') or 0):.1f}% "
                f"(всего {int(kpi.get('cancel_count') or 0)})",
                self.p_style,
            )
        )

        reasons = kpi.get('cancellation_reasons') or {}
        if reasons:
            story.append(Spacer(1, 0.2 * cm))
            data = [['Причина', 'Количество', 'Доля']]
            for reason, row in reasons.items():
                data.append([
                    self._safe(reason),
                    str(int(row.get('count') or 0)),
                    f"{float(row.get('pct') or 0):.1f}%",
                ])
            t = Table(data, colWidths=[8 * cm, 3 * cm, 3 * cm])
            t.setStyle(self._table_style())
            story.append(t)

        fig = self.visualizer.chart_cancellation_reasons()
        self._append_figure(
            story,
            fig,
            'quality_reasons',
            width=self.SQUARE_IMG_WIDTH,
            height=self.SQUARE_IMG_HEIGHT,
        )

    def _add_timeliness(self, story):
        story.append(Paragraph('4. Анализ своевременности', self.h1_style))
        kpi = self.analyzer.calculate_timeliness_kpi() or {}
        if not kpi:
            story.append(Paragraph('Нет данных для анализа своевременности.', self.p_style))
            return

        story.append(
            Paragraph(
                f"<b>Средняя длительность сделки:</b> {float(kpi.get('duration_h_avg') or 0):.1f} ч",
                self.p_style,
            )
        )
        story.append(
            Paragraph(
                f"<b>Медиана длительности:</b> {float(kpi.get('duration_h_median') or 0):.1f} ч",
                self.p_style,
            )
        )
        story.append(
            Paragraph(
                f"<b>В срок на погрузке:</b> {float(kpi.get('on_time_load_pct') or 0):.1f}% "
                f"(опозданий: {int(kpi.get('late_count') or 0)})",
                self.p_style,
            )
        )

        fig = self.visualizer.chart_duration_distribution()
        self._append_figure(story, fig, 'time_duration')

    def _add_anomalies(self, story):
        story.append(Paragraph('5. Проблемные заявки', self.h1_style))
        thresholds = self.settings.get('thresholds', {}) if self.settings else {}
        limit = int(self.settings.get('analysis.anomalies_limit', 10)) if self.settings else 10
        anomalies = self.analyzer.find_anomalies(thresholds, limit_per_category=limit)
        category_titles = {
            'low_margin': 'Низкая маржинальность',
            'loss': 'Убыточные заявки',
            'late_load': 'Опоздания на погрузку',
            'long_processing': 'Долгая обработка',
            'high_empty_km': 'Высокий холостой пробег',
            'cancelled_by_us': 'Отмены по нашей вине',
        }

        data = [['Категория', 'Количество']]
        total = 0
        for key, title in category_titles.items():
            count = len(anomalies.get(key) or [])
            total += count
            data.append([title, str(count)])
        t = Table(data, colWidths=[11 * cm, 3 * cm])
        t.setStyle(self._table_style())
        story.append(Paragraph(f"<b>Найдено проблемных заявок:</b> {total}", self.p_style))
        story.append(t)

        top_examples = []
        for key in category_titles:
            items = anomalies.get(key) or []
            if items:
                top_examples = items[:5]
                break
        if top_examples:
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph('<b>Примеры заявок:</b>', self.p_style))
            sample = [['№ заявки', 'Филиал', 'Менеджер', 'Маржа']]
            for item in top_examples:
                sample.append([
                    self._safe(item.get('case_id', '')),
                    self._safe(item.get('филиал', '')),
                    self._safe(item.get('менеджер', '')),
                    self.format_money(item.get('маржа')),
                ])
            st = Table(sample, colWidths=[3 * cm, 4 * cm, 4 * cm, 3 * cm])
            st.setStyle(self._table_style())
            story.append(st)

    def _add_recommendations(self, story):
        story.append(Paragraph('Автоматические рекомендации', self.h1_style))
        story.append(Spacer(1, 0.3 * cm))

        recs = self.analyzer.get_auto_recommendations() or []
        if not recs:
            story.append(
                Paragraph(
                    'Программа не нашла критичных инсайтов. Основные показатели в норме.',
                    self.p_style,
                )
            )
            return

        colors_map = {
            'critical': colors.HexColor('#e74c3c'),
            'warning': colors.HexColor('#f39c12'),
            'info': colors.HexColor('#3498db'),
        }

        for rec in recs:
            severity_color = colors_map.get(rec.get('severity'), colors.gray)
            severity_hex = (
                f"#{int(severity_color.red * 255):02x}"
                f"{int(severity_color.green * 255):02x}"
                f"{int(severity_color.blue * 255):02x}"
            )
            title_text = f'<font color="{severity_hex}">●</font> '
            title_text += f'<b>{self._safe(rec.get("title", "Без названия"))}</b>'
            title_text += (
                f' <font size="8" color="#7f8c8d">'
                f'— {self._safe(rec.get("category", "Общее"))}</font>'
            )
            story.append(Paragraph(title_text, self.p_style))
            story.append(Paragraph(self._safe(rec.get('text', '')), self.p_style))
            story.append(Spacer(1, 0.3 * cm))

    def _add_analyst_notes(self, story):
        story.append(Paragraph('Заметки аналитика', self.h1_style))
        story.append(Spacer(1, 0.3 * cm))

        notes = ''
        if self.file_hash:
            # Привязываем заметки к конкретному загруженному файлу по его хешу.
            if self.settings and hasattr(self.settings, 'load_notes'):
                notes = self.settings.load_notes(self.file_hash)
            else:
                from core.settings import get_settings
                notes = get_settings().load_notes(self.file_hash)

        if not notes or not notes.strip():
            story.append(Paragraph('Аналитик не оставил заметок к этим данным.', self.p_style))
            return

        # Пустая строка в заметках = новый абзац в PDF.
        paragraphs = notes.strip().split('\n\n')
        for para in paragraphs:
            text = self._safe(para).replace('\n', '<br/>')
            story.append(Paragraph(text, self.p_style))
            story.append(Spacer(1, 0.2 * cm))
