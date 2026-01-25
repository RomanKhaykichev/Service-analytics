"""
Helper functions for barcode normalization in SQL queries.

This module provides utilities for generating SQL expressions to normalize barcodes
without storing normalized values as physical columns in stg_* or fact_* tables.
"""


def barcode_norm_sql(col: str) -> str:
    """
    Generate SQL expression for barcode normalization.
    
    This function returns a SQL expression string that normalizes a barcode column
    by removing all whitespace and trimming edges. The result is NULL if empty.
    
    Canonical formula:
        NULLIF(TRIM(regexp_replace(CAST(col AS text), '\\s+', '', 'g')), '')
    
    Args:
        col: Column name or SQL expression (e.g., 'fs.barcode', 'barcode_raw')
    
    Returns:
        SQL expression string ready to be inserted into text() queries
    
    Examples:
        >>> barcode_norm_sql('fs.barcode')
        "NULLIF(TRIM(regexp_replace(CAST(fs.barcode AS text), '\\\\s+', '', 'g')), '')"
        
        >>> barcode_norm_sql('barcode_raw')
        "NULLIF(TRIM(regexp_replace(CAST(barcode_raw AS text), '\\\\s+', '', 'g')), '')"
    
    Usage:
        from app.utils.barcode import barcode_norm_sql
        
        db.execute(text(f'''
            SELECT {barcode_norm_sql('fs.barcode')} AS barcode_norm
            FROM fact_sales fs
        '''))
    """
    return f"NULLIF(TRIM(regexp_replace(CAST({col} AS text), '\\s+', '', 'g')), '')"
