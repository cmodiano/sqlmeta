"""SQL object comparison and schema drift detection.

This module provides functionality to compare SQL objects from different sources
and detect schema drift.

Example:
    >>> from sqlmeta.comparison import ObjectComparator, DataTypeNormalizer
    >>> normalizer = DataTypeNormalizer("postgresql")
    >>> comparator = ObjectComparator(normalizer)
    >>> diff = comparator.compare_tables(table1, table2)
"""

from sqlmeta.comparison.comparator import ObjectComparator
from sqlmeta.comparison.diff_models import (
    ColumnDiff,
    ConstraintDiff,
    DiffResult,
    SchemaDiff,
    TableDiff,
)
from sqlmeta.comparison.type_normalizer import DataTypeNormalizer

__all__ = [
    "ObjectComparator",
    "DataTypeNormalizer",
    "DiffResult",
    "TableDiff",
    "ColumnDiff",
    "ConstraintDiff",
    "SchemaDiff",
]
