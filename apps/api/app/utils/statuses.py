"""
Status classification utilities for orders.
Поддержка RU и UZ (сопоставление из выгрузок: Завершен=Yetkazilgan, В обработке=Qayta ishlanmoqda, Отменен=Bekor qilindi).
"""

# UZ эквиваленты для выкупов/выручки (completed): yetkazilgan, yakunlangan, yakunlandi (в выгрузке UZUM)
_COMPLETED_PATTERNS = (
    "status ILIKE '%заверш%' OR status ILIKE '%достав%' OR status ILIKE '%получ%' OR status ILIKE '%выдан%'"
    " OR status ILIKE '%yetkazilgan%' OR status ILIKE '%yakunlangan%' OR status ILIKE '%yakunlandi%'"
)
# UZ эквиваленты для отмены: bekor qilindi, rad etildi
_CANCELLED_PATTERNS = "status ILIKE '%отмен%' OR status ILIKE '%bekor qilindi%' OR status ILIKE '%rad etildi%'"
# UZ эквиваленты для «в обработке»: qayta ishlashda, qayta ishlanmoqda, jarayonda
_PROCESSING_PATTERNS = (
    "status ILIKE '%обработ%'"
    " OR status ILIKE '%qayta ishlashda%' OR status ILIKE '%qayta ishlanmoqda%' OR status ILIKE '%jarayonda%'"
)


def is_completed(status: str) -> bool:
    """
    Check if status indicates completed order.
    RU: заверш, достав, получ, выдан. UZ: yetkazilgan, yakunlangan.
    """
    if not status:
        return False
    status_lower = status.lower()
    return any(pattern in status_lower for pattern in ['заверш', 'достав', 'получ', 'выдан', 'yetkazilgan', 'yakunlangan'])


def is_cancelled(status: str) -> bool:
    """
    Check if status indicates cancelled order.
    RU: отмен. UZ: bekor qilindi, rad etildi.
    """
    if not status:
        return False
    status_lower = status.lower()
    return any(x in status_lower for x in ['отмен', 'bekor qilindi', 'rad etildi'])


def is_processing(status: str) -> bool:
    """
    Check if status indicates processing order.
    RU: обработ. UZ: qayta ishlashda, qayta ishlanmoqda, jarayonda.
    """
    if not status:
        return False
    status_lower = status.lower()
    return any(x in status_lower for x in ['обработ', 'qayta ishlashda', 'qayta ishlanmoqda', 'jarayonda'])


def get_status_sql_condition(status_type: str) -> str:
    """
    Get SQL condition for status filtering (RU + UZ).
    Returns SQL fragment for WHERE clause.
    
    Args:
        status_type: 'completed', 'cancelled', 'processing', or 'orders' (all except cancelled)
    
    Returns:
        SQL condition string for use in WHERE clause
    """
    if status_type == 'completed':
        return f"({_COMPLETED_PATTERNS})"
    elif status_type == 'cancelled':
        return f"({_CANCELLED_PATTERNS})"
    elif status_type == 'processing':
        return f"({_PROCESSING_PATTERNS})"
    elif status_type == 'orders':
        return f"NOT ({_CANCELLED_PATTERNS})"
    else:
        raise ValueError(f"Unknown status_type: {status_type}")
