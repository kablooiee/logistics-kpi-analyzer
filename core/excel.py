# -*- coding: utf-8 -*-
"""
Парсер Excel-файлов логистических данных.
Экспортирует функции парсинга в JSON и получения информации о структуре файла.
"""

import json
from datetime import datetime

import pandas as pd


# ============================================================
# Константы
# ============================================================

DATETIME_FORMATS = [
    '%Y-%m-%d %H:%M:%S',
    '%d.%m.%Y %H:%M:%S',
    '%Y-%m-%d',
    '%d.%m.%Y',
]

CASE_ID_HEADERS = ['номер заявки', 'case id', 'заявка', 'order id']
ACTION_HEADERS = ['статус', 'action', 'операция', 'тип рейса']
DATETIME_HEADERS = [
    'дата  загрузки', 'дата загрузки', 'datetime', 'date', 'time',
    'дата закрытия', 'дата отмены заявки', 'дата подачи заявки',
    'дата фактич',
]
NUMERIC_HEADERS = [
    'фактич. км', 'фактический км', 'сумма заказчика', 'сумма перевозчика',
    'холостой пробег', 'расстояние', 'прибыль', 'предоплата',
    'ставка', 'вес груза', 'платон', 'средняя за км',
    'заказчик-выставлено', 'заказчик-оплачено',
    'перевозчик-выставлено', 'перевозчик-оплачено',
]


class ParseError(Exception):
    """Исключение для ошибок парсинга Excel файла."""


# ============================================================
# Парсинг дат и определение столбцов
# ============================================================

def parse_datetime(dt_raw):
    """Парсит дату/время из ячейки Excel."""
    if pd.isna(dt_raw):
        raise ParseError("Пустое значение даты")

    if isinstance(dt_raw, (int, float)):
        try:
            return pd.to_datetime(dt_raw, unit='D', origin='1899-12-30').to_pydatetime()
        except (ValueError, OverflowError):
            pass

    try:
        return pd.to_datetime(dt_raw, dayfirst=True).to_pydatetime()
    except (ValueError, TypeError):
        pass

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(str(dt_raw).strip(), fmt)
        except ValueError:
            continue

    raise ParseError(f'Некорректная дата/время: "{dt_raw}"')


def detect_column_indices(headers):
    """Определяет индексы ключевых столбцов по названиям."""
    headers_lower = [h.strip().lower() if isinstance(h, str) else '' for h in headers]

    case_id_idx = None
    action_idx = None
    datetime_idx = None
    numeric_cols = []

    for i, header in enumerate(headers_lower):
        if case_id_idx is None and any(keyword in header for keyword in CASE_ID_HEADERS):
            case_id_idx = i
        elif action_idx is None and any(keyword in header for keyword in ACTION_HEADERS):
            action_idx = i
        elif datetime_idx is None and any(keyword in header for keyword in DATETIME_HEADERS):
            datetime_idx = i
        if any(keyword in header for keyword in NUMERIC_HEADERS):
            numeric_cols.append(i)

    if case_id_idx is None and len(headers) > 0:
        case_id_idx = 0
    if action_idx is None and len(headers) > 1:
        action_idx = 1
    if datetime_idx is None and len(headers) > 2:
        datetime_idx = 2

    if case_id_idx is None:
        raise ParseError("Не найден столбец с ID заявки")
    if datetime_idx is None:
        raise ParseError("Не найден столбец с датой/временем")

    return {
        'case_id': case_id_idx,
        'action': action_idx,
        'datetime': datetime_idx,
        'numeric_cols': numeric_cols,
    }


def _coerce_value(value, is_numeric: bool):
    """Приводит значение для JSON с защитой от NaN."""
    if pd.isna(value):
        return None
    if is_numeric:
        try:
            return float(value)
        except (ValueError, TypeError):
            s = str(value).strip()
            return s if s else None
    if isinstance(value, (int, float, bool)):
        return value
    return str(value)


# ============================================================
# Основные функции парсинга
# ============================================================

def parse_excel_to_json_with_progress(filepath, sheet_name=None, progress_callback=None):
    """Парсит Excel в JSON и сообщает прогресс через callback."""
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name or 0, engine='openpyxl')
    except Exception as e:
        raise ParseError(f'Ошибка при чтении Excel файла: {e}')

    if df.empty:
        raise ParseError("Файл пустой или не содержит данных")

    total_rows = len(df)
    five_percent = max(1, int(total_rows * 0.05))
    row_interval = min(100, five_percent)

    if progress_callback:
        progress_callback(0, total_rows)

    headers = list(df.columns)
    column_indices = detect_column_indices(headers)
    numeric_set = set(column_indices['numeric_cols'])

    records = []
    actions_set = set()

    case_id_pos = column_indices['case_id']
    action_pos = column_indices.get('action')
    datetime_pos = column_indices['datetime']

    processed_count = 0
    for row_idx, row in df.iterrows():
        try:
            case_id_val = row.iloc[case_id_pos]
            case_id = None if pd.isna(case_id_val) else str(case_id_val).strip()

            action = None
            if action_pos is not None:
                a = row.iloc[action_pos]
                if not pd.isna(a):
                    action = str(a).strip() or None

            dt_val = row.iloc[datetime_pos]
            dt_iso = parse_datetime(dt_val).isoformat()

            record = {
                'case_id': case_id,
                'action': action,
                'datetime': dt_iso,
            }

            for i, value in enumerate(row):
                if i in (case_id_pos, action_pos, datetime_pos):
                    continue
                col_name = headers[i]
                record[col_name] = _coerce_value(value, is_numeric=(i in numeric_set))

            if action:
                actions_set.add(action)

            records.append(record)
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(f'Ошибка обработки строки {row_idx + 2}: {e}')

        processed_count += 1
        if progress_callback and total_rows:
            if processed_count % row_interval == 0 or processed_count == total_rows:
                progress_callback(processed_count, total_rows)

    actions_list = sorted(list(actions_set), key=str) if actions_set else []

    metadata = {
        'total_records': len(records),
        'unique_actions': len(actions_list),
        'columns_detected': {
            'case_id_column': headers[case_id_pos],
            'action_column': headers[action_pos] if action_pos is not None else 'Не определено',
            'datetime_column': headers[datetime_pos],
            'numeric_columns': [headers[i] for i in column_indices['numeric_cols']],
        },
        'data_summary': {
            'total_columns': len(headers),
            'parsed_records': len(records),
            'avg_fields_per_record': (
                sum(len(r) for r in records) / len(records) if records else 0
            ),
        },
    }

    result = {
        'actions': [{'name': a} for a in actions_list],
        'records': records,
        'metadata': metadata,
    }

    return json.dumps(result, indent=2, ensure_ascii=False, default=str)


def parse_excel_to_json(filepath, sheet_name=None):
    """Совместимая обёртка без callback прогресса."""
    return parse_excel_to_json_with_progress(
        filepath,
        sheet_name,
        progress_callback=None,
    )


def get_excel_info(filepath, sheet_name=None):
    """Возвращает структуру Excel без полного парсинга."""
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name or 0, engine='openpyxl', nrows=5)
        full = pd.read_excel(
            filepath,
            sheet_name=sheet_name or 0,
            engine='openpyxl',
            usecols=[0],
        )
        total_rows = len(full)

        column_indices = detect_column_indices(df.columns)

        return {
            'columns': list(df.columns),
            'total_rows': total_rows,
            'detected_columns': {
                'case_id': df.columns[column_indices['case_id']],
                'action': (
                    df.columns[column_indices['action']]
                    if column_indices.get('action') is not None
                    else 'Не определено'
                ),
                'datetime': df.columns[column_indices['datetime']],
                'numeric_cols': [df.columns[i] for i in column_indices['numeric_cols']],
            },
            'sample_data': {
                'first_row': df.iloc[0].to_dict() if len(df) > 0 else None,
            },
        }
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f'Ошибка при анализе файла: {e}')
