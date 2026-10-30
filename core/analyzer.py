# -*- coding: utf-8 -*-
"""
Аналитика табличных отчётов для логистических заявок.
Экспортирует класс `Analyzer` и функцию `analyze_kpi`.
"""

import json
import math
from datetime import datetime

import pandas as pd
import numpy as np
from core.formulas import (
    average_check,
    cancel_rate,
    empty_km_share,
    format_money,
    format_percentage,
    loss_orders_share,
    margin_percentage,
    on_time_percentage,
    success_rate,
)
from core.settings import get_settings


# ============================================================
# Константы и хелперы
# ============================================================

# Список колонок, которые мы умеем находить под разными именами.
# Используется и в analyzer'е, и в внешних модулях — позволяет в будущем
# легко переключиться на «универсальный режим» (другой Excel — те же ключи).
COLUMN_ALIASES = {
    'branch_customer':  ['Филиал (заказчик)', 'Филиал заказчик', 'Branch customer'],
    'branch_carrier':   ['Филиал (перевозчик)', 'Филиал перевозчик'],
    'manager':          ['Менеджер', 'Manager'],
    'dispatcher':       ['Диспетчер', 'Dispatcher'],
    'carrier_type':     ['Тип перевозчика'],
    'cancel_reason':    ['Причина отмены'],
    'geocontrol':       ['Геоконтроль'],
    'region_unload':    ['Регион выгрузки'],

    'sum_customer':     ['Сумма заказчика', 'Customer amount'],
    'sum_carrier':      ['Сумма перевозчика', 'Carrier amount'],
    'distance':         ['Расстояние'],                    # плановое расстояние, заполнено в 100% случаев
    'fact_km':          ['Фактич. КМ', 'Фактический КМ'],  # часто не заполнено, держим как опциональный
    'empty_km':         ['Холостой пробег'],

    'date_load':        ['Дата  загрузки', 'Дата загрузки', 'Date load'],      # плановая
    'date_fact_load':   ['Дата фактич. загрузки'],
    'date_fact_unload': ['Дата фактич. разгрузки'],
    'date_submit':      ['Дата подачи заявки'],
    'date_close':       ['Дата закрытия'],
    'date_cancel':      ['Дата отмены заявки'],
}


def _find_column(df: pd.DataFrame, alias_key: str):
    """Возвращает имя столбца из df, подходящего под один из алиасов, либо None.
    Нормализует двойные пробелы, регистр и края — устойчиво к опечаткам в исходниках.
    """
    import re
    candidates = COLUMN_ALIASES.get(alias_key, [])

    def normalize(s: str) -> str:
        return re.sub(r'\s+', ' ', str(s).strip().lower())

    cols_norm = {normalize(c): c for c in df.columns if isinstance(c, str)}
    for cand in candidates:
        key = normalize(cand)
        if key in cols_norm:
            return cols_norm[key]
    return None


def _to_numeric(s: pd.Series) -> pd.Series:
    """Безопасное приведение к числам: всё нечисловое → NaN, NaN → 0."""
    return pd.to_numeric(s, errors='coerce').fillna(0)


def _to_datetime(s: pd.Series) -> pd.Series:
    """Безопасное приведение к datetime."""
    return pd.to_datetime(s, errors='coerce')



class Analyzer:
    """
    Анализатор отчётных данных для логистики.

    После создания доступны атрибуты:
      - self.df          — очищенный DataFrame
      - self.cols        — словарь {alias: real_column_name | None}
      - self.warnings    — список замечаний о данных (что недогружено, что вычищено)
    """

    def __init__(self, json_filepath: str, max_rows: int = 10000):
        self.json_filepath = json_filepath
        self.max_rows = max_rows
        self.data = None
        self.df = None
        self.cols = {}
        self.warnings = []
        self._load_data()
        self._prepare_data()
        self.df_filtered = self.df

    # ============================================================
    # Загрузка и подготовка
    # ============================================================

    def _load_data(self):
        """Загружает JSON и собирает DataFrame с ограничением по числу строк."""
        try:
            with open(self.json_filepath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            raise ValueError(f"Ошибка загрузки JSON файла: {e}")

        records = self.data.get('records', [])
        if len(records) > self.max_rows:
            records = records[:self.max_rows]
            self.warnings.append(
                f"Анализ ограничен {self.max_rows} записями из {len(self.data.get('records', []))}"
            )

        self.df = pd.DataFrame(records)
        if self.df.empty:
            return

        # datetime из парсера лежит в ISO-формате — пригодится для общих метрик
        if 'datetime' in self.df.columns:
            self.df['datetime'] = _to_datetime(self.df['datetime'])

    def _prepare_data(self):
        """Находит все нужные столбцы, приводит типы, делает базовую очистку."""
        if self.df is None or self.df.empty:
            return

        # Маппинг алиасов в реальные имена столбцов
        for alias in COLUMN_ALIASES:
            self.cols[alias] = _find_column(self.df, alias)

        # Парсер забирает поле «Дата загрузки» как опорное и кладёт его в специальный
        # столбец 'datetime'. Прокидываем эту связь, чтобы расчёт своевременности работал.
        if self.cols.get('date_load') is None and 'datetime' in self.df.columns:
            self.cols['date_load'] = 'datetime'

        # ---- Числовые поля
        for key in ('sum_customer', 'sum_carrier', 'distance', 'fact_km', 'empty_km'):
            col = self.cols.get(key)
            if col is not None:
                self.df[col] = _to_numeric(self.df[col])

        # ---- Очистка пробегов
        empty_km_col = self.cols.get('empty_km')
        if empty_km_col is not None:
            neg = (self.df[empty_km_col] < 0).sum()
            if neg:
                self.df.loc[self.df[empty_km_col] < 0, empty_km_col] = 0
                self.warnings.append(f"Обнаружено и обнулено {neg} отрицательных значений холостого пробега")

            # Обрезаем экстремальные значения, чтобы не портили среднее по холостому пробегу.
            p99 = self.df[empty_km_col].quantile(0.99)
            if p99 > 0:
                outliers = (self.df[empty_km_col] > p99 * 3).sum()
                if outliers:
                    self.df.loc[self.df[empty_km_col] > p99 * 3, empty_km_col] = p99 * 3
                    self.warnings.append(f"Обрезано {outliers} экстремальных выбросов холостого пробега")

        # ---- Эффективный пробег: фактический если есть, иначе плановое расстояние.
        # Фактический километраж обычно пустой, поэтому берём плановое расстояние.
        fact_col = self.cols.get('fact_km')
        dist_col = self.cols.get('distance')
        if dist_col is not None:
            if fact_col is not None:
                self.df['_km_effective'] = np.where(
                    self.df[fact_col] > 0,
                    self.df[fact_col],
                    self.df[dist_col]
                )
                fact_share = (self.df[fact_col] > 0).mean() * 100
                if fact_share < 50:
                    self.warnings.append(
                        f"Поле «Фактич. КМ» заполнено лишь в {fact_share:.1f}% записей — "
                        f"для расчёта пробега используется «Расстояние»"
                    )
            else:
                self.df['_km_effective'] = self.df[dist_col]

        # ---- Даты
        for key in ('date_load', 'date_fact_load', 'date_fact_unload',
                    'date_submit', 'date_close', 'date_cancel'):
            col = self.cols.get(key)
            if col is not None:
                self.df[col] = _to_datetime(self.df[col])

        # ---- Производные признаки
        cancel_col = self.cols.get('date_cancel')
        close_col = self.cols.get('date_close')
        if cancel_col is not None and close_col is not None:
            # Отмену считаем только когда в записи реально есть дата отмены.
            # Успешная: есть закрытие и нет отмены
            self.df['_successful'] = self.df[close_col].notna() & self.df[cancel_col].isna()
        elif cancel_col is not None:
            self.df['_successful'] = self.df[cancel_col].isna()
        else:
            self.df['_successful'] = True

        # Маржа и маржа на км — теперь на реальном пробеге
        sum_c = self.cols.get('sum_customer')
        sum_p = self.cols.get('sum_carrier')
        if sum_c and sum_p:
            self.df['_margin'] = self.df[sum_c] - self.df[sum_p]
            if '_km_effective' in self.df.columns:
                # Защита от деления на ноль для коротких или битых рейсов.
                km = self.df['_km_effective'].replace(0, np.nan)
                self.df['_margin_per_km'] = self.df['_margin'] / km
            self.df['_margin_pct'] = np.where(
                self.df[sum_c] > 0,
                self.df['_margin'] / self.df[sum_c] * 100,
                np.nan
            )

        # Длительность (часы): подача → закрытие
        submit_col = self.cols.get('date_submit')
        if submit_col and close_col:
            delta = (self.df[close_col] - self.df[submit_col]).dt.total_seconds() / 3600
            # Отрицательные / неадекватные значения отбрасываем
            self.df['_duration_h'] = delta.where((delta >= 0) & (delta < 24 * 60))

        # Опоздание на погрузку (часы): фактическая − плановая
        load_col = self.cols.get('date_load')
        fact_load_col = self.cols.get('date_fact_load')
        if load_col and fact_load_col:
            delta = (self.df[fact_load_col] - self.df[load_col]).dt.total_seconds() / 3600
            self.df['_load_delay_h'] = delta.where(delta.abs() < 24 * 14)

    # ============================================================
    # Фильтрация и поиск
    # ============================================================

    def _date_column_for_filter(self):
        col = self.cols.get('date_load')
        if col is None and self.df is not None and 'datetime' in self.df.columns:
            col = 'datetime'
        return col

    def apply_filters(self, filters: dict) -> None:
        """
        Фильтрует полный self.df по критериям, результат — self.df_filtered.
        Исходный self.df не изменяется.
        """
        if self.df is None or self.df.empty:
            self.df_filtered = self.df
            return

        mask = pd.Series(True, index=self.df.index)

        date_col = self._date_column_for_filter()
        if date_col is not None:
            ts = pd.to_datetime(self.df[date_col], errors='coerce')
            date_from = filters.get('date_from')
            date_to = filters.get('date_to')
            if date_from is not None:
                mask &= ts >= pd.Timestamp(date_from)
            if date_to is not None:
                mask &= ts <= pd.Timestamp(date_to)

        branch = filters.get('branch')
        if branch:
            col = self.cols.get('branch_customer')
            if col is not None:
                mask &= self.df[col].astype(str).str.strip() == str(branch).strip()

        manager = filters.get('manager')
        if manager:
            col = self.cols.get('manager')
            if col is not None:
                mask &= self.df[col].astype(str).str.strip() == str(manager).strip()

        carrier_type = filters.get('carrier_type')
        if carrier_type:
            col = self.cols.get('carrier_type')
            if col is not None:
                mask &= self.df[col].astype(str).str.strip() == str(carrier_type).strip()

        self.df_filtered = self.df.loc[mask].copy()

    def clear_filters(self) -> None:
        """Сбрасывает срез: дальнейшие расчёты по полному набору строк."""
        self.df_filtered = self.df

    def search(self, query: str, limit: int = 50) -> list:
        """
        Регистронезависимый поиск по ключевым текстовым полям заявок.
        Возвращает список словарей c агрегированными полями для UI.
        """
        if self.df is None or self.df.empty:
            return []

        q = str(query or '').strip().lower()
        if len(q) < 2:
            return []

        d = self.df
        case_col = 'case_id' if 'case_id' in d.columns else None

        search_candidates = [
            case_col,
            self.cols.get('manager'),
            self.cols.get('dispatcher'),
            'Перевозчик',
            'Водитель',
            'Заказчик',
            'Город загрузки',
            'Город выгрузки',
        ]
        search_cols = [c for c in search_candidates if c in d.columns]
        if not search_cols:
            return []

        mask = pd.Series(False, index=d.index)
        for col in search_cols:
            s = d[col].fillna('').astype(str).str.lower()
            mask |= s.str.contains(q, na=False, regex=False)

        matched = d.loc[mask].head(max(1, int(limit)))

        submit_col = self.cols.get('date_submit')
        branch_col = self.cols.get('branch_customer')
        manager_col = self.cols.get('manager')
        carrier_col = 'Перевозчик' if 'Перевозчик' in d.columns else None
        sum_c_col = self.cols.get('sum_customer')
        cancel_col = self.cols.get('date_cancel')
        close_col = self.cols.get('date_close')
        cancel_reason_col = self.cols.get('cancel_reason')
        margin_col = '_margin' if '_margin' in d.columns else None

        out = []
        for _, row in matched.iterrows():
            case_id = row.get(case_col) if case_col else None
            submit_val = row.get(submit_col) if submit_col else None
            if pd.isna(submit_val):
                submit_str = ''
            elif hasattr(submit_val, 'strftime'):
                submit_str = submit_val.strftime('%d.%m.%Y')
            else:
                submit_str = str(submit_val)

            cancel_val = row.get(cancel_col) if cancel_col else None
            close_val = row.get(close_col) if close_col else None
            if cancel_col and not pd.isna(cancel_val):
                status = 'Отменено'
            elif close_col and not pd.isna(close_val):
                status = 'Успешно'
            else:
                status = 'В работе'

            if margin_col:
                margin = row.get(margin_col)
            else:
                sc = row.get(sum_c_col) if sum_c_col else None
                sp = row.get(self.cols.get('sum_carrier')) if self.cols.get('sum_carrier') else None
                try:
                    margin = float(sc) - float(sp)
                except (TypeError, ValueError):
                    margin = None

            out.append({
                'case_id': '' if pd.isna(case_id) else str(case_id),
                'Дата подачи заявки': submit_str,
                'Филиал (заказчик)': '' if not branch_col or pd.isna(row.get(branch_col)) else str(row.get(branch_col)),
                'Менеджер': '' if not manager_col or pd.isna(row.get(manager_col)) else str(row.get(manager_col)),
                'Перевозчик': '' if not carrier_col or pd.isna(row.get(carrier_col)) else str(row.get(carrier_col)),
                'Сумма заказчика': (None if not sum_c_col or pd.isna(row.get(sum_c_col)) else float(row.get(sum_c_col))),
                'Маржа': (None if margin is None or pd.isna(margin) else float(margin)),
                'Статус': status,
                'Причина отмены': (
                    '' if not cancel_reason_col or pd.isna(row.get(cancel_reason_col))
                    else str(row.get(cancel_reason_col))
                ),
            })

        return out

    def find_anomalies(self, thresholds: dict, limit_per_category: int = 10) -> dict:
        """
        Ищет проблемные заявки по категориям и возвращает топ-N для каждой.
        """
        if self.df is None or self.df.empty:
            return {
                'low_margin': [],
                'loss': [],
                'late_load': [],
                'long_processing': [],
                'high_empty_km': [],
                'cancelled_by_us': [],
            }

        d = self.df
        lim = max(1, int(limit_per_category))

        margin_pct_critical = float(thresholds.get('margin_pct_critical', 20.0))
        load_delay_critical = float(thresholds.get('load_delay_hours_critical', 4.0))

        case_col = 'case_id' if 'case_id' in d.columns else None
        submit_col = self.cols.get('date_submit')
        branch_col = self.cols.get('branch_customer')
        manager_col = self.cols.get('manager')
        sum_c_col = self.cols.get('sum_customer')
        cancel_reason_col = self.cols.get('cancel_reason')
        margin_col = '_margin' if '_margin' in d.columns else None
        margin_pct_col = '_margin_pct' if '_margin_pct' in d.columns else None
        delay_col = '_load_delay_h' if '_load_delay_h' in d.columns else None
        duration_col = '_duration_h' if '_duration_h' in d.columns else None
        empty_km_col = self.cols.get('empty_km')
        distance_col = self.cols.get('distance')

        def to_float(val):
            try:
                f = float(val)
                if math.isnan(f) or math.isinf(f):
                    return None
                return f
            except (TypeError, ValueError):
                return None

        def fmt_date(val):
            if val is None or pd.isna(val):
                return ''
            if hasattr(val, 'strftime'):
                return val.strftime('%d.%m.%Y')
            return str(val)

        def base_record(row):
            margin_val = to_float(row.get(margin_col)) if margin_col else None
            if margin_val is None:
                sc = to_float(row.get(sum_c_col)) if sum_c_col else None
                sp = to_float(row.get(self.cols.get('sum_carrier'))) if self.cols.get('sum_carrier') else None
                if sc is not None and sp is not None:
                    margin_val = sc - sp

            margin_pct_val = to_float(row.get(margin_pct_col)) if margin_pct_col else None

            return {
                'case_id': '' if not case_col or pd.isna(row.get(case_col)) else str(row.get(case_col)),
                'дата': fmt_date(row.get(submit_col) if submit_col else None),
                'филиал': '' if not branch_col or pd.isna(row.get(branch_col)) else str(row.get(branch_col)),
                'менеджер': '' if not manager_col or pd.isna(row.get(manager_col)) else str(row.get(manager_col)),
                'сумма': to_float(row.get(sum_c_col)) if sum_c_col else None,
                'маржа': margin_val,
                'маржинальность_pct': margin_pct_val,
                'причина_отмены': (
                    '' if not cancel_reason_col or pd.isna(row.get(cancel_reason_col))
                    else str(row.get(cancel_reason_col))
                ),
            }

        def rows_from_frame(frame, extra_key=None, extra_val_func=None):
            out = []
            for _, row in frame.iterrows():
                rec = base_record(row)
                if extra_key and extra_val_func:
                    rec[extra_key] = extra_val_func(row)
                out.append(rec)
            return out

        anomalies = {
            'low_margin': [],
            'loss': [],
            'late_load': [],
            'long_processing': [],
            'high_empty_km': [],
            'cancelled_by_us': [],
        }

        if margin_pct_col:
            low_margin_df = d[d[margin_pct_col] < margin_pct_critical].sort_values(margin_pct_col, ascending=True).head(lim)
            anomalies['low_margin'] = rows_from_frame(low_margin_df)

        if margin_col:
            loss_df = d[d[margin_col] < 0].sort_values(margin_col, ascending=True).head(lim)
            anomalies['loss'] = rows_from_frame(loss_df)

        if delay_col:
            late_df = d[d[delay_col] > load_delay_critical].sort_values(delay_col, ascending=False).head(lim)
            anomalies['late_load'] = rows_from_frame(
                late_df,
                extra_key='задержка_погрузки_ч',
                extra_val_func=lambda r: to_float(r.get(delay_col)),
            )

        if duration_col:
            durations = d[duration_col].dropna()
            if not durations.empty:
                p90 = float(durations.quantile(0.9))
                long_df = d[d[duration_col] >= p90].sort_values(duration_col, ascending=False).head(lim)
                anomalies['long_processing'] = rows_from_frame(
                    long_df,
                    extra_key='длительность_ч',
                    extra_val_func=lambda r: to_float(r.get(duration_col)),
                )

        if empty_km_col and distance_col:
            dist = pd.to_numeric(d[distance_col], errors='coerce')
            empty = pd.to_numeric(d[empty_km_col], errors='coerce')
            with np.errstate(divide='ignore', invalid='ignore'):
                share = np.where(dist > 0, (empty / dist) * 100, np.nan)
            tmp = d.copy()
            tmp['_empty_share_pct'] = share
            high_empty_df = tmp[tmp['_empty_share_pct'] > 30].sort_values('_empty_share_pct', ascending=False).head(lim)
            anomalies['high_empty_km'] = rows_from_frame(
                high_empty_df,
                extra_key='холостой_пробег_pct',
                extra_val_func=lambda r: to_float(r.get('_empty_share_pct')),
            )

        if cancel_reason_col:
            reasons = d[cancel_reason_col].fillna('').astype(str).str.lower()
            cancel_us_df = d[reasons.str.contains('наш', regex=False)].head(lim)
            anomalies['cancelled_by_us'] = rows_from_frame(cancel_us_df)

        return anomalies

    def get_filter_options(self) -> dict:
        """Уникальные значения для UI и границы дат по полному self.df."""
        empty = {
            'branches': [],
            'managers': [],
            'carrier_types': [],
            'date_min': None,
            'date_max': None,
        }
        if self.df is None or self.df.empty:
            return empty

        out = {
            'branches': [],
            'managers': [],
            'carrier_types': [],
            'date_min': None,
            'date_max': None,
        }

        bc = self.cols.get('branch_customer')
        if bc is not None:
            s = self.df[bc].dropna().astype(str).str.strip()
            s = s[s != '']
            out['branches'] = sorted(s.unique().tolist(), key=str)

        mc = self.cols.get('manager')
        if mc is not None:
            s = self.df[mc].dropna().astype(str).str.strip()
            s = s[s != '']
            out['managers'] = sorted(s.unique().tolist(), key=str)

        ct = self.cols.get('carrier_type')
        if ct is not None:
            s = self.df[ct].dropna().astype(str).str.strip()
            s = s[s != '']
            out['carrier_types'] = sorted(s.unique().tolist(), key=str)

        date_col = self._date_column_for_filter()
        if date_col is not None:
            ser = pd.to_datetime(self.df[date_col], errors='coerce').dropna()
            if not ser.empty:
                dmin = ser.min()
                dmax = ser.max()
                # Для UI возвращаем только date/datetime-объекты (без pandas-типов).
                out['date_min'] = dmin.to_pydatetime() if hasattr(dmin, 'to_pydatetime') else dmin
                out['date_max'] = dmax.to_pydatetime() if hasattr(dmax, 'to_pydatetime') else dmax

        return out

    # ============================================================
    # Расчёт KPI по группам
    # ============================================================

    def calculate_financial_kpi(self) -> dict:
        """Финансовая группа: выручка, затраты, маржа, рентабельность, средний чек."""
        d = self.df_filtered
        if d is None or d.empty or '_margin' not in d.columns:
            return {}

        sum_c = self.cols.get('sum_customer')
        sum_p = self.cols.get('sum_carrier')
        branch = self.cols.get('branch_customer')

        total_revenue = float(d[sum_c].sum())
        total_cost = float(d[sum_p].sum())
        total_margin = float(d['_margin'].sum())
        loss_orders_count = int((d['_margin'] < 0).sum())
        result = {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_margin': total_margin,
            'avg_check': average_check(total_revenue, len(d)),
            'avg_margin': float(d['_margin'].mean()),
            'margin_pct_total': margin_percentage(total_revenue, total_cost),
            'loss_orders_count': loss_orders_count,
            'loss_orders_pct': loss_orders_share(loss_orders_count, len(d)),
        }

        # По филиалам
        if branch is not None:
            by_branch = d.groupby(branch).agg(
                revenue=(sum_c, 'sum'),
                cost=(sum_p, 'sum'),
                margin=('_margin', 'sum'),
                avg_check=(sum_c, 'mean'),
                margin_pct=('_margin_pct', 'mean'),
                count=(sum_c, 'count'),
            ).round(2).sort_values('margin', ascending=False)
            result['by_branch'] = by_branch.to_dict(orient='index')

        # Маржа на км — теперь честная
        if '_margin_per_km' in d.columns and branch is not None:
            mpkm = d.groupby(branch)['_margin_per_km'].mean().round(2)
            result['margin_per_km_by_branch'] = mpkm.to_dict()

        return result

    def calculate_operational_kpi(self) -> dict:
        """Операционная группа: нагрузка менеджеров, холостой пробег, разрезы по перевозчикам."""
        d = self.df_filtered
        if d is None or d.empty:
            return {}

        result = {}
        branch = self.cols.get('branch_customer')
        manager = self.cols.get('manager')
        carrier_type = self.cols.get('carrier_type')
        sum_c = self.cols.get('sum_customer')

        # Нагрузка менеджеров по филиалам (старый показатель сохранён)
        if branch and manager:
            load = (d.groupby([branch, manager])
                    .size()
                    .groupby(level=0)
                    .agg(['mean', 'min', 'max', 'count'])
                    .round(1))
            result['manager_load_by_branch'] = {
                idx: {'avg': row['mean'], 'min': int(row['min']),
                      'max': int(row['max']), 'managers_count': int(row['count'])}
                for idx, row in load.iterrows()
            }

        # ТОП менеджеров по объёму выручки
        if manager and sum_c:
            top = (d.groupby(manager)
                   .agg(orders=(sum_c, 'count'), revenue=(sum_c, 'sum'))
                   .sort_values('revenue', ascending=False)
                   .head(10)
                   .round(2))
            result['top_managers'] = top.to_dict(orient='index')

        # Доля холостого пробега в общем
        empty_km_col = self.cols.get('empty_km')
        if empty_km_col and '_km_effective' in d.columns:
            total_loaded = d['_km_effective'].sum()
            total_empty = d[empty_km_col].sum()
            total_all = total_loaded + total_empty
            if total_all > 0:
                result['empty_km_share_pct'] = empty_km_share(total_empty, total_all)
                result['total_loaded_km'] = float(total_loaded)
                result['total_empty_km'] = float(total_empty)

        # Разрез по типам перевозчиков
        if carrier_type and sum_c:
            grp = d.groupby(carrier_type).agg(
                orders=(sum_c, 'count'),
                revenue=(sum_c, 'sum'),
                avg_margin_pct=('_margin_pct', 'mean'),
            ).round(2)
            result['by_carrier_type'] = grp.to_dict(orient='index')

        return result

    def calculate_quality_kpi(self) -> dict:
        """Качество и надёжность: успешность, структура отмен, геоконтроль."""
        d = self.df_filtered
        if d is None or d.empty:
            return {}

        result = {}
        branch = self.cols.get('branch_customer')
        cancel_col = self.cols.get('date_cancel')
        reason_col = self.cols.get('cancel_reason')
        geo_col = self.cols.get('geocontrol')

        # Общий success rate
        if '_successful' in d.columns:
            successful_count = int(d['_successful'].sum())
            total_count = int(len(d))
            result['success_rate_total'] = success_rate(successful_count, total_count)
            result['successful_count'] = int(d['_successful'].sum())
            result['total_count'] = int(len(d))

        # Success rate по филиалам
        if branch and '_successful' in d.columns:
            sr = d.groupby(branch)['_successful'].agg(['mean', 'count']).round(4)
            sr['mean'] = sr['mean'] * 100
            result['success_rate_by_branch'] = {
                idx: {'success_pct': round(row['mean'], 1), 'orders': int(row['count'])}
                for idx, row in sr.iterrows()
            }

        # Структура отмен
        if cancel_col is not None and reason_col is not None:
            canceled = d[d[cancel_col].notna()]
            if not canceled.empty:
                reasons = canceled[reason_col].value_counts()
                total_cancel = len(canceled)
                result['cancellation_reasons'] = {
                    str(k): {'count': int(v), 'pct': round(v / total_cancel * 100, 1)}
                    for k, v in reasons.items()
                }
                result['cancel_count'] = total_cancel
                result['cancel_rate_pct'] = round(cancel_rate(total_cancel, len(d)), 2)

                # Разделение «по нашей вине» vs «не по нашей»
                our_fault_keywords = ['наш', 'отказ', 'срыв']
                client_fault_keywords = ['клиент']
                our_fault = 0
                client_fault = 0
                for reason, cnt in reasons.items():
                    r = str(reason).lower()
                    if any(k in r for k in our_fault_keywords) and 'клиент' not in r:
                        our_fault += cnt
                    elif any(k in r for k in client_fault_keywords):
                        client_fault += cnt
                result['cancel_our_fault'] = int(our_fault)
                result['cancel_client_fault'] = int(client_fault)

        # Геоконтроль
        if geo_col is not None:
            with_geo = d[geo_col].notna() & (d[geo_col].astype(str).str.strip() != '')
            result['geocontrol_share_pct'] = float(with_geo.mean() * 100)

        return result

    def calculate_timeliness_kpi(self) -> dict:
        """Своевременность: длительность сделки, опоздания, статистика по филиалам."""
        d = self.df_filtered
        if d is None or d.empty:
            return {}

        result = {}
        branch = self.cols.get('branch_customer')

        if '_duration_h' in d.columns:
            dur = d['_duration_h'].dropna()
            if not dur.empty:
                result['duration_h_avg'] = float(dur.mean())
                result['duration_h_median'] = float(dur.median())
                result['duration_h_p90'] = float(dur.quantile(0.9))
                # Доля быстрых (закрытых менее чем за 24 ч)
                result['fast_close_pct'] = float((dur < 24).mean() * 100)

        if '_load_delay_h' in d.columns:
            delay = d['_load_delay_h'].dropna()
            if not delay.empty:
                result['load_delay_h_avg'] = float(delay.mean())
                result['load_delay_h_median'] = float(delay.median())
                # KPI «своевременность погрузки»: считаем опозданием расхождение > 2 ч
                # (1–2 часа — нормальный диапазон по фактическим данным)
                on_time_count = int((delay <= 2).sum())
                on_time = on_time_percentage(on_time_count, len(delay))
                result['on_time_load_pct'] = float(on_time)
                result['late_count'] = int((delay > 2).sum())

        # Длительность по филиалам
        if branch and '_duration_h' in d.columns:
            grp = d.groupby(branch)['_duration_h'].agg(['mean', 'median', 'count']).round(1)
            result['duration_by_branch'] = {
                idx: {'avg_h': row['mean'], 'median_h': row['median'], 'count': int(row['count'])}
                for idx, row in grp.iterrows()
                if pd.notna(row['mean'])
            }

        return result

    def get_data_quality(self) -> list[dict]:
        """Возвращает карточки качества данных для главной страницы."""
        d = self.df_filtered
        if d is None or d.empty:
            return []

        cards: list[dict] = []
        total_rows = len(d)

        key_cols = [
            self.cols.get('sum_customer'),
            self.cols.get('branch_customer'),
            self.cols.get('date_load'),
            self.cols.get('manager'),
        ]
        key_cols = [c for c in key_cols if c is not None]
        complete_pct = 0.0
        if key_cols:
            complete_mask = pd.Series(True, index=d.index)
            for col in key_cols:
                if pd.api.types.is_datetime64_any_dtype(d[col]):
                    complete_mask &= d[col].notna()
                elif pd.api.types.is_numeric_dtype(d[col]):
                    complete_mask &= d[col].notna()
                else:
                    s = d[col].astype(str).str.strip()
                    complete_mask &= d[col].notna() & (s != '') & (s.str.lower() != 'nan')
            complete_pct = float(complete_mask.mean() * 100)
        if complete_pct >= 90:
            completeness_status = 'good'
        elif complete_pct >= 75:
            completeness_status = 'warning'
        else:
            completeness_status = 'critical'
        cards.append({
            'label': 'Полнота данных',
            'value': f'{complete_pct:.0f}%',
            'raw_value': round(complete_pct, 1),
            'status': completeness_status,
            'comment': 'из обязательных полей',
        })

        load_col = self._date_column_for_filter()
        years_span = 0.0
        period_comment = 'нет дат'
        period_value = '—'
        period_status = 'warning'
        if load_col is not None:
            dates = pd.to_datetime(d[load_col], errors='coerce').dropna()
            if not dates.empty:
                dmin = dates.min()
                dmax = dates.max()
                days = max((dmax - dmin).days, 0)
                years_span = days / 365.25
                years_display = max(1, int(round(years_span)))
                period_value = f'{years_display} лет'
                period_comment = f'с {dmin.year} по {dmax.year}'
                if years_span >= 3:
                    period_status = 'good'
                elif years_span >= 1:
                    period_status = 'warning'
                else:
                    period_status = 'critical'
        cards.append({
            'label': 'Покрытие периода',
            'value': period_value,
            'raw_value': round(years_span, 2),
            'status': period_status,
            'comment': period_comment,
        })

        cleaned_rows = 0
        for warning in self.warnings or []:
            text = str(warning or '')
            if text.startswith('Обнаружено и обнулено '):
                number = text.replace('Обнаружено и обнулено ', '').split(' ', 1)[0]
                if number.isdigit():
                    cleaned_rows += int(number)
            elif text.startswith('Обрезано '):
                number = text.replace('Обрезано ', '').split(' ', 1)[0]
                if number.isdigit():
                    cleaned_rows += int(number)
        cards.append({
            'label': 'Очищено выбросов',
            'value': f'{cleaned_rows} записи' if cleaned_rows == 1 else f'{cleaned_rows} записей',
            'raw_value': cleaned_rows,
            'status': 'neutral' if cleaned_rows < 100 else 'warning',
            'comment': 'отрицательные пробеги и аномалии',
        })

        recognized = len([k for k, v in self.cols.items() if v is not None])
        semantic_total = len(COLUMN_ALIASES)
        recognized_ratio = (recognized / semantic_total) if semantic_total else 0.0
        cards.append({
            'label': 'Распознано столбцов',
            'value': f'{recognized} из {semantic_total} семантических полей',
            'raw_value': recognized,
            'status': 'good' if recognized_ratio >= 0.7 else 'warning',
            'comment': 'автоопределение структуры',
        })
        return cards

    def get_summary_cards(self) -> list[dict]:
        """Возвращает 8 ключевых KPI-карточек для главной страницы."""
        d = self.df_filtered
        if d is None or d.empty:
            return []

        settings = get_settings()
        thresholds = settings.get('thresholds', {}) or {}
        fin = self.calculate_financial_kpi()
        qual = self.calculate_quality_kpi()
        tim = self.calculate_timeliness_kpi()
        total = max(len(d), 1)
        full_total = len(self.df) if self.df is not None else total

        revenue = float(fin.get('total_revenue', 0.0))
        margin = float(fin.get('total_margin', 0.0))
        margin_pct = float(fin.get('margin_pct_total', 0.0))
        avg_check = float(fin.get('avg_check', 0.0)) if fin else 0.0
        success_rate = float(qual.get('success_rate_total', 0.0))
        cancel_rate = float(qual.get('cancel_rate_pct', 0.0))
        on_time = float(tim.get('on_time_load_pct', 0.0))
        avg_duration = float(tim.get('duration_h_avg', 0.0))
        successful_count = int(qual.get('successful_count', 0) or 0)
        cancel_count = int(qual.get('cancel_count', 0) or 0)

        success_warn = float(thresholds.get('success_rate_warning', 80.0))
        success_crit = float(thresholds.get('success_rate_critical', 70.0))
        cancel_crit = float(thresholds.get('cancel_rate_critical', 15.0))
        margin_warn = float(thresholds.get('margin_pct_warning', 25.0))
        margin_crit = float(thresholds.get('margin_pct_critical', 20.0))

        def status_by_high(value, warning, critical):
            if value >= warning:
                return 'good'
            if value >= critical:
                return 'warning'
            return 'critical'

        def status_by_low(value, warning, critical):
            if value <= warning:
                return 'good'
            if value <= critical:
                return 'warning'
            return 'critical'

        card_revenue_status = 'good' if revenue > 0 else 'neutral'
        card_margin_status = 'good' if margin >= 0 else 'critical'
        card_margin_pct_status = status_by_high(margin_pct, margin_warn, margin_crit)
        card_avg_check_status = 'good' if avg_check > 0 else 'neutral'
        card_success_status = status_by_high(success_rate, success_warn, success_crit)
        card_cancel_status = status_by_low(cancel_rate, 10.0, cancel_crit)
        card_on_time_status = status_by_high(on_time, 85.0, 70.0)
        card_duration_status = status_by_low(avg_duration, 48.0, 72.0)

        return [
            {
                'label': 'Выручка',
                'value': format_money(revenue),
                'raw_value': revenue,
                'status': card_revenue_status,
                'comment': f'по {full_total} заявкам',
            },
            {
                'label': 'Маржа',
                'value': format_money(margin),
                'raw_value': margin,
                'status': card_margin_status,
                'comment': 'до вычета прочих расходов',
            },
            {
                'label': 'Маржинальность %',
                'value': format_percentage(margin_pct),
                'raw_value': margin_pct,
                'status': card_margin_pct_status,
                'comment': f'порог warning {margin_warn:.0f}%',
            },
            {
                'label': 'Средний чек',
                'value': format_money(avg_check),
                'raw_value': avg_check,
                'status': card_avg_check_status,
                'comment': f'по {full_total} заявкам',
            },
            {
                'label': 'Success rate',
                'value': format_percentage(success_rate),
                'raw_value': success_rate,
                'status': card_success_status,
                'comment': f'успешных {successful_count}',
            },
            {
                'label': 'Доля отмен %',
                'value': format_percentage(cancel_rate),
                'raw_value': cancel_rate,
                'status': card_cancel_status,
                'comment': f'отменено {cancel_count} из {total}',
            },
            {
                'label': 'В срок на погрузке %',
                'value': format_percentage(on_time),
                'raw_value': on_time,
                'status': card_on_time_status,
                'comment': 'допуск до 2 часов',
            },
            {
                'label': 'Средняя длительность сделки',
                'value': f'{avg_duration:.1f} ч' if avg_duration > 0 else '—',
                'raw_value': avg_duration,
                'status': card_duration_status if avg_duration > 0 else 'neutral',
                'comment': 'от подачи до закрытия',
            },
        ]

    def get_funnel_data(self) -> dict:
        """
        Возвращает данные процессной воронки:
        - stages: этапы и потери между этапами;
        - cancellations_by_stage: отмены по зонам процесса и причинам.
        """
        d = self.df_filtered
        if d is None or d.empty:
            return {'stages': [], 'cancellations_by_stage': {}}

        load_col = self.cols.get('date_load')
        fact_load_col = self.cols.get('date_fact_load')
        fact_unload_col = self.cols.get('date_fact_unload')
        close_col = self.cols.get('date_close')
        cancel_col = self.cols.get('date_cancel')
        reason_col = self.cols.get('cancel_reason')

        stages: list[dict] = []
        stage_counts: list[tuple[str, int]] = [('Подано', int(len(d)))]
        for stage_name, col in (
            ('Принято', load_col),
            ('Загружено', fact_load_col),
            ('Доставлено', fact_unload_col),
            ('Закрыто', close_col),
        ):
            if col is not None and col in d.columns:
                count = int(pd.to_datetime(d[col], errors='coerce').notna().sum())
                stage_counts.append((stage_name, count))

        previous = None
        for stage_name, count in stage_counts:
            if previous is None:
                loss = 0
                loss_pct = 0.0
            else:
                loss = max(previous - count, 0)
                loss_pct = (loss / previous * 100.0) if previous > 0 else 0.0
            stages.append({
                'name': stage_name,
                'count': int(count),
                'loss': int(loss),
                'loss_pct': round(float(loss_pct), 1),
            })
            previous = count

        cancellations_by_stage = {
            'После подачи': {'count': 0, 'by_reason': {}},
            'После загрузки': {'count': 0, 'by_reason': {}},
            'После доставки': {'count': 0, 'by_reason': {}},
        }
        if cancel_col is None or cancel_col not in d.columns:
            return {'stages': stages, 'cancellations_by_stage': cancellations_by_stage}

        canceled = d.copy()
        canceled['_cancel_ts'] = pd.to_datetime(canceled[cancel_col], errors='coerce')
        canceled = canceled[canceled['_cancel_ts'].notna()].copy()
        if canceled.empty:
            return {'stages': stages, 'cancellations_by_stage': cancellations_by_stage}

        canceled['_fact_load_ts'] = (
            pd.to_datetime(canceled[fact_load_col], errors='coerce')
            if fact_load_col is not None and fact_load_col in canceled.columns
            else pd.NaT
        )
        canceled['_fact_unload_ts'] = (
            pd.to_datetime(canceled[fact_unload_col], errors='coerce')
            if fact_unload_col is not None and fact_unload_col in canceled.columns
            else pd.NaT
        )

        def _bucket(row):
            cancel_ts = row['_cancel_ts']
            fact_load_ts = row.get('_fact_load_ts')
            fact_unload_ts = row.get('_fact_unload_ts')
            if pd.notna(fact_unload_ts) and cancel_ts >= fact_unload_ts:
                return 'После доставки'
            if pd.notna(fact_load_ts) and cancel_ts >= fact_load_ts:
                return 'После загрузки'
            return 'После подачи'

        canceled['_bucket'] = canceled.apply(_bucket, axis=1)
        if reason_col is not None and reason_col in canceled.columns:
            reasons = canceled[reason_col].fillna('').astype(str).str.strip()
            canceled['_reason'] = reasons.where(reasons != '', 'Не указана причина')
        else:
            canceled['_reason'] = 'Не указана причина'

        for bucket in ('После подачи', 'После загрузки', 'После доставки'):
            frame = canceled[canceled['_bucket'] == bucket]
            if frame.empty:
                continue
            reason_counts = frame['_reason'].value_counts()
            cancellations_by_stage[bucket] = {
                'count': int(len(frame)),
                'by_reason': {str(k): int(v) for k, v in reason_counts.items()},
            }

        return {'stages': stages, 'cancellations_by_stage': cancellations_by_stage}

    def _make_rec(self, category: str, severity: str, title: str, text: str) -> dict:
        return {
            'category': category,
            'severity': severity,
            'title': title,
            'text': text,
        }

    # --- Правила рекомендаций: финансы
    def _rec_branch_margin_gap(self, fin: dict):
        by_branch = fin.get('by_branch') or {}
        if len(by_branch) < 2:
            return []
        ranked = sorted(
            ((name, float(vals.get('margin_pct') or 0.0)) for name, vals in by_branch.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        top_name, top_pct = ranked[0]
        low_name, low_pct = ranked[-1]
        gap = top_pct - low_pct
        if gap <= 5:
            return []
        return [
            self._make_rec(
                'Финансы',
                'info',
                f'Высокая маржинальность филиала {top_name}',
                (
                    f'Филиал {top_name} показывает маржинальность {top_pct:.1f}%, '
                    f'что выше аутсайдера на {gap:.1f} п.п. Рекомендуется изучить '
                    'и тиражировать практики этого филиала.'
                ),
            ),
            self._make_rec(
                'Финансы',
                'warning',
                f'Низкая маржинальность филиала {low_name}',
                (
                    f'Филиал {low_name} имеет маржинальность {low_pct:.1f}%, '
                    f'отставание от лидера {gap:.1f} п.п. Требуется разбор структуры '
                    'себестоимости и тарифов.'
                ),
            ),
        ]

    def _rec_top_manager_revenue_share(self, fin: dict, ops: dict):
        top_managers = ops.get('top_managers') or {}
        if not top_managers:
            return None
        total_revenue = float(fin.get('total_revenue') or 0.0)
        if total_revenue <= 0:
            return None
        name = next(iter(top_managers.keys()))
        revenue = float((top_managers.get(name) or {}).get('revenue') or 0.0)
        share = revenue / total_revenue * 100
        if share <= 20:
            return None
        severity = 'warning' if share < 30 else 'critical'
        return self._make_rec(
            'Финансы',
            severity,
            f'Высокая концентрация выручки на менеджере {name}',
            (
                f'Менеджер {name} формирует {share:.1f}% общей выручки. '
                'Рекомендуется снизить зависимость от одного исполнителя '
                'и перераспределить клиентский портфель.'
            ),
        )

    def _rec_loss_orders_share(self, fin: dict):
        loss_pct = float(fin.get('loss_orders_pct') or 0.0)
        if loss_pct <= 5:
            return None
        severity = 'critical' if loss_pct > 10 else 'warning'
        return self._make_rec(
            'Финансы',
            severity,
            'Повышенная доля убыточных заявок',
            (
                f'Убыточные заявки составляют {loss_pct:.1f}% портфеля. '
                'Рекомендуется пересмотреть тарифы, контроль закупочных ставок '
                'и условия по проблемным сегментам.'
            ),
        )

    # --- Правила рекомендаций: операции
    def _rec_carrier_type_margin_gap(self, ops: dict):
        by_type = ops.get('by_carrier_type') or {}
        if len(by_type) < 2:
            return None
        ranked = sorted(
            ((name, float(vals.get('avg_margin_pct') or 0.0)) for name, vals in by_type.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        top_name, top_pct = ranked[0]
        low_name, low_pct = ranked[-1]
        gap = top_pct - low_pct
        if gap <= 3:
            return None
        return self._make_rec(
            'Операции',
            'info',
            f'Разница эффективности типов перевозчика ({gap:.1f} п.п.)',
            (
                f'Тип "{top_name}" даёт среднюю маржинальность {top_pct:.1f}%, '
                f'а "{low_name}" — {low_pct:.1f}%. Рекомендуется масштабировать '
                'лучшие практики и пересмотреть условия по менее эффективному типу.'
            ),
        )

    def _rec_overloaded_manager(self):
        d = self.df_filtered
        manager_col = self.cols.get('manager')
        if d is None or d.empty or manager_col is None:
            return None
        counts = d[manager_col].dropna().astype(str).str.strip()
        counts = counts[counts != '']
        if counts.empty:
            return None
        vc = counts.value_counts()
        avg_load = float(vc.mean()) if not vc.empty else 0.0
        top_name = str(vc.index[0])
        top_count = int(vc.iloc[0])
        if avg_load <= 0 or top_count <= avg_load * 2:
            return None
        return self._make_rec(
            'Операции',
            'warning',
            f'Перегрузка менеджера {top_name}',
            (
                f'На менеджера {top_name} приходится {top_count} заявок, '
                f'что более чем в 2 раза выше среднего ({avg_load:.1f}). '
                'Рекомендуется перераспределить нагрузку по команде.'
            ),
        )

    def _rec_high_empty_km(self, ops: dict):
        share = float(ops.get('empty_km_share_pct') or 0.0)
        if share <= 15:
            return None
        severity = 'critical' if share > 25 else 'warning'
        return self._make_rec(
            'Операции',
            severity,
            'Высокая доля холостого пробега',
            (
                f'Холостой пробег составляет {share:.1f}% общего километража. '
                'Рекомендуется оптимизировать маршрутизацию и планирование обратных загрузок.'
            ),
        )

    # --- Правила рекомендаций: качество
    def _rec_top_cancel_reason(self, qual: dict):
        reasons = qual.get('cancellation_reasons') or {}
        if not reasons:
            return None
        top_reason, payload = max(reasons.items(), key=lambda x: int((x[1] or {}).get('count') or 0))
        top_pct = float((payload or {}).get('pct') or 0.0)
        if top_pct <= 30:
            return None
        return self._make_rec(
            'Качество',
            'warning',
            f'Основная причина отмен: {top_reason}',
            (
                f'Причина "{top_reason}" формирует {top_pct:.1f}% всех отмен. '
                'Рекомендуется сфокусировать корректирующие действия в этой зоне.'
            ),
        )

    def _rec_cancel_our_fault(self, qual: dict):
        cancel_count = int(qual.get('cancel_count') or 0)
        our_fault = int(qual.get('cancel_our_fault') or 0)
        if cancel_count <= 0:
            return None
        share = our_fault / cancel_count * 100
        if share <= 20:
            return None
        return self._make_rec(
            'Качество',
            'critical',
            'Высокая доля отмен по нашей вине',
            (
                f'Отмены по нашей вине составляют {share:.1f}% от всех отмен. '
                'Нужны срочные меры по устранению внутренних причин срывов.'
            ),
        )

    def _rec_cancel_seasonality(self):
        d = self.df_filtered
        cancel_col = self.cols.get('date_cancel')
        if d is None or d.empty or cancel_col is None:
            return None
        cancel_ts = pd.to_datetime(d[cancel_col], errors='coerce').dropna()
        if cancel_ts.empty:
            return None
        by_month = cancel_ts.dt.to_period('M').value_counts().sort_index()
        if len(by_month) < 2:
            return None
        max_v = int(by_month.max())
        min_v = int(by_month.min())
        if min_v <= 0:
            return None
        ratio = max_v / min_v
        if ratio <= 3:
            return None
        max_month = str(by_month.idxmax())
        min_month = str(by_month.idxmin())
        return self._make_rec(
            'Качество',
            'warning',
            'Выраженная сезонность отмен',
            (
                f'В пиковый месяц ({max_month}) отмен в {ratio:.1f} раза больше, '
                f'чем в минимальный ({min_month}). Рекомендуется заранее готовить '
                'ресурсы под сезонные периоды риска.'
            ),
        )

    # --- Правила рекомендаций: время
    def _rec_on_time_share(self, tim: dict):
        on_time = float(tim.get('on_time_load_pct') or 0.0)
        if on_time >= 80:
            return None
        severity = 'critical' if on_time < 60 else 'warning'
        return self._make_rec(
            'Время',
            severity,
            'Низкая доля заявок в срок на погрузке',
            (
                f'Показатель "в срок" составляет {on_time:.1f}%. '
                'Требуется усилить контроль планирования окон погрузки '
                'и работу с перевозчиками.'
            ),
        )

    def _rec_load_delay(self, tim: dict):
        avg_delay = float(tim.get('load_delay_h_avg') or 0.0)
        settings = get_settings()
        warning_thr = float(settings.get('thresholds.load_delay_hours_warning', 2.0))
        critical_thr = float(settings.get('thresholds.load_delay_hours_critical', 4.0))
        if avg_delay <= warning_thr:
            return None
        severity = 'critical' if avg_delay > critical_thr else 'warning'
        return self._make_rec(
            'Время',
            severity,
            'Высокая средняя задержка погрузки',
            (
                f'Среднее отклонение от плановой погрузки: {avg_delay:.1f} ч '
                f'(порог warning {warning_thr:.1f} ч, critical {critical_thr:.1f} ч). '
                'Рекомендуется пересмотреть процесс подтверждения слотов и диспетчеризацию.'
            ),
        )

    def get_auto_recommendations(self) -> list[dict]:
        """Формирует список автоматических инсайтов и рекомендаций по данным."""
        d = self.df_filtered
        if d is None or d.empty:
            return []

        fin = self.calculate_financial_kpi()
        ops = self.calculate_operational_kpi()
        qual = self.calculate_quality_kpi()
        tim = self.calculate_timeliness_kpi()

        recs: list[dict] = []

        recs.extend(self._rec_branch_margin_gap(fin))
        for item in (
            self._rec_top_manager_revenue_share(fin, ops),
            self._rec_loss_orders_share(fin),
            self._rec_carrier_type_margin_gap(ops),
            self._rec_overloaded_manager(),
            self._rec_high_empty_km(ops),
            self._rec_top_cancel_reason(qual),
            self._rec_cancel_our_fault(qual),
            self._rec_cancel_seasonality(),
            self._rec_on_time_share(tim),
            self._rec_load_delay(tim),
        ):
            if item:
                recs.append(item)

        severity_rank = {'critical': 0, 'warning': 1, 'info': 2}
        recs.sort(key=lambda x: (severity_rank.get(x.get('severity', 'info'), 9), x.get('category', '')))
        return recs

    # ============================================================
    # Общий API
    # ============================================================

    def calculate_all_kpi(self) -> dict:
        """Главная точка входа — возвращает структурированный словарь по 4 группам."""
        return {
            'financial': self.calculate_financial_kpi(),
            'operational': self.calculate_operational_kpi(),
            'quality': self.calculate_quality_kpi(),
            'timeliness': self.calculate_timeliness_kpi(),
            'warnings': self.warnings,
            'rows_analyzed': int(len(self.df_filtered)) if self.df_filtered is not None else 0,
        }

    def get_statistics(self) -> dict:
        """Общая статистика по файлу (сохранён старый интерфейс для UI)."""
        d = self.df_filtered
        if d is None or d.empty:
            return {}

        branch = self.cols.get('branch_customer')
        manager = self.cols.get('manager')
        sum_c = self.cols.get('sum_customer')
        sum_p = self.cols.get('sum_carrier')

        total = len(d)
        successful = int(d['_successful'].sum()) if '_successful' in d.columns else total

        stats = {
            'total_requests': total,
            'unique_branches': int(d[branch].nunique()) if branch else 0,
            'avg_km': float(d['_km_effective'].mean()) if '_km_effective' in d.columns else 0.0,
            'total_income': float(d[sum_c].sum()) if sum_c else 0.0,
            'total_expenses': float(d[sum_p].sum()) if sum_p else 0.0,
            'success_rate': successful / total * 100 if total else 0.0,
            'successful_requests': successful,
        }
        stats['total_profit'] = stats['total_income'] - stats['total_expenses']
        if branch:
            stats['branch_stats'] = d[branch].value_counts().to_dict()
        if manager:
            stats['top_managers'] = d[manager].value_counts().head(10).to_dict()

        return stats

def analyze_kpi(json_filepath: str, max_rows: int = 10000) -> str:
    """
    Основная функция для анализа KPI. Возвращает Markdown-отчёт.
    Сигнатура полностью совместима с предыдущей версией.
    """
    try:
        analyzer = Analyzer(json_filepath, max_rows)
        from core.reports import Reports

        formatter = Reports(analyzer)
        return formatter.get_kpi_report()
    except Exception as e:
        return f"# ОШИБКА АНАЛИЗА\n\nПроизошла ошибка при анализе файла: {e}"
