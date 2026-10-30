# -*- coding: utf-8 -*-
"""Чистые формулы и форматтеры KPI без зависимостей от pandas."""

from datetime import datetime


def margin(revenue, cost) -> float:
    """Маржа.

    Формула: выручка - затраты.
    """
    try:
        return float(revenue or 0) - float(cost or 0)
    except (TypeError, ValueError):
        return 0.0


def margin_percentage(revenue, cost) -> float:
    """Маржинальность в процентах.

    Формула: (выручка - затраты) / выручка * 100.
    """
    try:
        revenue = float(revenue or 0)
        cost = float(cost or 0)
    except (TypeError, ValueError):
        return 0.0
    if revenue <= 0:
        return 0.0
    return (revenue - cost) / revenue * 100.0


def average_check(total_revenue, orders_count) -> float:
    """Средний чек.

    Формула: общая выручка / количество заявок.
    """
    try:
        total_revenue = float(total_revenue or 0)
        orders_count = float(orders_count or 0)
    except (TypeError, ValueError):
        return 0.0
    if orders_count <= 0:
        return 0.0
    return total_revenue / orders_count


def margin_per_km(margin_value, distance) -> float:
    """Маржа на километр.

    Формула: маржа / расстояние.
    """
    try:
        margin_value = float(margin_value or 0)
        distance = float(distance or 0)
    except (TypeError, ValueError):
        return 0.0
    if distance <= 0:
        return 0.0
    return margin_value / distance


def loss_orders_share(loss_count, total) -> float:
    """Доля убыточных заявок в процентах.

    Формула: loss_count / total * 100.
    """
    try:
        loss_count = float(loss_count or 0)
        total = float(total or 0)
    except (TypeError, ValueError):
        return 0.0
    if total <= 0:
        return 0.0
    return loss_count / total * 100.0


def success_rate(successful, total) -> float:
    """Success rate в процентах.

    Формула: successful / total * 100.
    """
    try:
        successful = float(successful or 0)
        total = float(total or 0)
    except (TypeError, ValueError):
        return 0.0
    if total <= 0:
        return 0.0
    return successful / total * 100.0


def cancel_rate(cancelled, total) -> float:
    """Доля отмен в процентах.

    Формула: cancelled / total * 100.
    """
    try:
        cancelled = float(cancelled or 0)
        total = float(total or 0)
    except (TypeError, ValueError):
        return 0.0
    if total <= 0:
        return 0.0
    return cancelled / total * 100.0


def empty_km_share(empty, total) -> float:
    """Доля холостого пробега в процентах.

    Формула: empty / total * 100.
    """
    try:
        empty = float(empty or 0)
        total = float(total or 0)
    except (TypeError, ValueError):
        return 0.0
    if total <= 0:
        return 0.0
    return empty / total * 100.0


def duration_hours(date_start, date_end) -> float:
    """Длительность в часах между датами.

    Формула: (date_end - date_start).total_seconds() / 3600.
    """
    if not isinstance(date_start, datetime) or not isinstance(date_end, datetime):
        return 0.0
    return (date_end - date_start).total_seconds() / 3600.0


def on_time_percentage(on_time_count, total) -> float:
    """Доля своевременных операций в процентах.

    Формула: on_time_count / total * 100.
    """
    return success_rate(on_time_count, total)


def load_delay_hours(planned, actual) -> float:
    """Отклонение фактической погрузки от плановой в часах.

    Формула: (actual - planned).total_seconds() / 3600.
    """
    if not isinstance(planned, datetime) or not isinstance(actual, datetime):
        return 0.0
    return (actual - planned).total_seconds() / 3600.0


def format_money(value) -> str:
    """Форматирует денежное значение в рублях."""
    try:
        return f"{float(value):,.0f}".replace(",", " ") + " ₽"
    except (TypeError, ValueError):
        return "—"


def format_percentage(value) -> str:
    """Форматирует значение процента с одним знаком после запятой."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "—"
