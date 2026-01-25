"""
Tests for barcode normalization helper.

These tests verify that the barcode normalization SQL expression
is generated correctly and matches the canonical formula.
"""
import pytest
from app.utils.barcode import barcode_norm_sql


def test_barcode_norm_sql_basic():
    """Test basic barcode normalization SQL generation."""
    result = barcode_norm_sql('barcode')
    expected = "NULLIF(TRIM(regexp_replace(CAST(barcode AS text), '\\s+', '', 'g')), '')"
    assert result == expected


def test_barcode_norm_sql_with_table_prefix():
    """Test barcode normalization with table prefix."""
    result = barcode_norm_sql('fs.barcode')
    expected = "NULLIF(TRIM(regexp_replace(CAST(fs.barcode AS text), '\\s+', '', 'g')), '')"
    assert result == expected


def test_barcode_norm_sql_with_raw_column():
    """Test barcode normalization with raw column name."""
    result = barcode_norm_sql('barcode_raw')
    expected = "NULLIF(TRIM(regexp_replace(CAST(barcode_raw AS text), '\\s+', '', 'g')), '')"
    assert result == expected


def test_barcode_norm_sql_contains_canonical_expression():
    """Test that generated SQL contains canonical normalization expression."""
    result = barcode_norm_sql('x')
    # Should contain the canonical formula components
    assert 'NULLIF' in result
    assert 'TRIM' in result
    assert 'regexp_replace' in result
    assert 'CAST' in result
    assert "\\s+" in result  # Escaped regex pattern
    assert "''" in result  # Empty string replacement


def test_barcode_norm_sql_no_physical_column_reference():
    """Test that helper does not reference physical barcode_norm columns."""
    result = barcode_norm_sql('barcode')
    # Should NOT contain references to physical columns
    assert 'barcode_norm' not in result.lower()
    assert 'barcode_key' not in result.lower()


def test_barcode_norm_sql_usage_in_sql_query():
    """Test that helper can be used in f-string SQL queries."""
    col = 'fs.barcode'
    sql = f"SELECT {barcode_norm_sql(col)} AS barcode_norm FROM fact_sales fs"
    
    # Should generate valid SQL expression
    assert 'barcode_norm' in sql
    assert 'fs.barcode' in sql
    assert 'NULLIF' in sql


def test_barcode_norm_sql_join_example():
    """Test helper usage in JOIN condition."""
    sql = f"""
        SELECT * FROM fact_sales s
        LEFT JOIN map_shop_barcode m
            ON m.barcode_norm = {barcode_norm_sql('s.barcode')}
    """
    
    # Should generate valid JOIN condition
    assert 'm.barcode_norm' in sql
    assert 's.barcode' in sql
    assert 'NULLIF' in sql


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
