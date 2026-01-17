"""
Status classification utilities for orders.
"""


def is_completed(status: str) -> bool:
    """
    Check if status indicates completed order.
    Patterns: заверш, достав, получ, выдан
    """
    if not status:
        return False
    status_lower = status.lower()
    return any(pattern in status_lower for pattern in ['заверш', 'достав', 'получ', 'выдан'])


def is_cancelled(status: str) -> bool:
    """
    Check if status indicates cancelled order.
    Patterns: отмен
    """
    if not status:
        return False
    status_lower = status.lower()
    return 'отмен' in status_lower


def is_processing(status: str) -> bool:
    """
    Check if status indicates processing order.
    Patterns: обработ
    """
    if not status:
        return False
    status_lower = status.lower()
    return 'обработ' in status_lower


def get_status_sql_condition(status_type: str) -> str:
    """
    Get SQL condition for status filtering.
    Returns SQL fragment for WHERE clause.
    
    Args:
        status_type: 'completed', 'cancelled', 'processing', or 'orders' (all except cancelled)
    
    Returns:
        SQL condition string for use in WHERE clause
    """
    if status_type == 'completed':
        return "status ILIKE '%заверш%' OR status ILIKE '%достав%' OR status ILIKE '%получ%' OR status ILIKE '%выдан%'"
    elif status_type == 'cancelled':
        return "status ILIKE '%отмен%'"
    elif status_type == 'processing':
        return "status ILIKE '%обработ%'"
    elif status_type == 'orders':
        # All orders except cancelled
        return "NOT (status ILIKE '%отмен%')"
    else:
        raise ValueError(f"Unknown status_type: {status_type}")
