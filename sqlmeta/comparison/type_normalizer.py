"""Data Type Normalization for Cross-Dialect Comparison.

This module provides data type normalization to handle dialect-specific type
equivalences and variations when comparing SQL objects from different sources.

Key Features:
- Normalize type names (INT → INTEGER, VARCHAR2 → VARCHAR)
- Handle precision and scale variations
- Support cross-dialect equivalences (TEXT vs CLOB)
- Dialect-specific transformations

Supported Dialects:
- PostgreSQL
- Oracle
- MySQL
- SQL Server
- DB2
"""

import re
from typing import Dict, Optional, Tuple


class DataTypeNormalizer:
    """Normalizes data types across SQL dialects for comparison.

    This class handles dialect-specific type equivalences, precision/scale
    normalization, and cross-dialect type mapping to enable accurate
    comparison of SQL Model objects from different sources.

    Example:
        >>> normalizer = DataTypeNormalizer()
        >>> normalizer.normalize("INT", "postgresql")
        'INTEGER'
        >>> normalizer.normalize("VARCHAR2(100)", "oracle")
        'VARCHAR(100)'
        >>> normalizer.normalize("TINYINT(1)", "mysql")
        'BOOLEAN'
    """

    def __init__(self):
        """Initialize the data type normalizer."""
        self.type_equivalents = self._build_type_equivalents()
        self.cross_dialect_equivalents = self._build_cross_dialect_equivalents()

    def _build_type_equivalents(self) -> Dict[str, Dict[str, str]]:
        """Build type equivalence mappings for each dialect.

        Returns:
            Dict mapping dialect -> {original_type: normalized_type}
        """
        return {
            "postgresql": {
                # Integer types
                "INT": "INTEGER",
                "INT2": "SMALLINT",
                "INT4": "INTEGER",
                "INT8": "BIGINT",
                "SERIAL": "INTEGER",
                "SERIAL2": "SMALLINT",
                "SERIAL4": "INTEGER",
                "SERIAL8": "BIGINT",
                "BIGSERIAL": "BIGINT",
                "SMALLSERIAL": "SMALLINT",
                # Character types
                "CHARACTER VARYING": "VARCHAR",
                "CHARACTER": "CHAR",
                # Numeric types
                "DECIMAL": "NUMERIC",
                # Floating point
                "FLOAT4": "REAL",
                "FLOAT8": "DOUBLE PRECISION",
                "DOUBLE": "DOUBLE PRECISION",
                # Boolean
                "BOOL": "BOOLEAN",
                # Date/Time
                "TIMESTAMPTZ": "TIMESTAMP WITH TIME ZONE",
                "TIMETZ": "TIME WITH TIME ZONE",
            },
            "oracle": {
                # Character types
                "VARCHAR2": "VARCHAR",
                "NVARCHAR2": "NVARCHAR",
                "CHAR": "CHAR",
                "NCHAR": "NCHAR",
                # Integer types (NUMBER with no scale)
                "INTEGER": "NUMBER",
                "INT": "NUMBER",
                "SMALLINT": "NUMBER",
                "BIGINT": "NUMBER",
                # Floating point
                "FLOAT": "NUMBER",
                "DOUBLE PRECISION": "NUMBER",
                "REAL": "NUMBER",
                # Large objects
                "LONG": "CLOB",
                "LONG RAW": "BLOB",
            },
            "mysql": {
                # Integer types
                "INT": "INTEGER",
                "TINYINT": "TINYINT",
                "SMALLINT": "SMALLINT",
                "MEDIUMINT": "MEDIUMINT",
                "BIGINT": "BIGINT",
                # Boolean (MySQL uses TINYINT(1))
                "BOOL": "BOOLEAN",
                "BOOLEAN": "TINYINT",
                # Character types
                "CHARACTER VARYING": "VARCHAR",
                "CHARACTER": "CHAR",
                # Text types
                "LONG": "MEDIUMTEXT",
                "LONG VARCHAR": "MEDIUMTEXT",
                # Floating point
                "DOUBLE": "DOUBLE",
                "DOUBLE PRECISION": "DOUBLE",
            },
            "sqlserver": {
                # Integer types
                "INT": "INTEGER",
                # Character types
                "CHARACTER VARYING": "VARCHAR",
                "CHARACTER": "CHAR",
                "NATIONAL CHARACTER VARYING": "NVARCHAR",
                "NATIONAL CHARACTER": "NCHAR",
                "NATIONAL CHAR VARYING": "NVARCHAR",
                # Date/Time
                "DATETIME2": "DATETIME2",
                "SMALLDATETIME": "DATETIME",
                # Large objects
                "TEXT": "VARCHAR",
                "NTEXT": "NVARCHAR",
                "IMAGE": "VARBINARY",
            },
            "db2": {
                # Integer types
                "INT": "INTEGER",
                # Character types
                "CHARACTER VARYING": "VARCHAR",
                "CHARACTER": "CHAR",
                "LONG VARCHAR": "VARCHAR",
                # Large objects
                "LONG VARGRAPHIC": "DBCLOB",
                # Floating point
                "DOUBLE": "DOUBLE",
                "DOUBLE PRECISION": "DOUBLE",
            },
        }

    def _build_cross_dialect_equivalents(self) -> Dict[str, set]:
        """Build cross-dialect type equivalences.

        Returns:
            Dict mapping canonical type -> set of equivalent types
        """
        return {
            # Integer types
            "INTEGER": {"INTEGER", "INT", "NUMBER", "INT4"},
            "SMALLINT": {"SMALLINT", "INT2", "NUMBER"},
            "BIGINT": {"BIGINT", "INT8", "NUMBER"},
            # Text types
            "TEXT": {"TEXT", "CLOB", "LONGTEXT", "MEDIUMTEXT", "NTEXT"},
            "VARCHAR": {"VARCHAR", "VARCHAR2", "CHARACTER VARYING"},
            "CHAR": {"CHAR", "CHARACTER"},
            # Binary types
            "BLOB": {"BLOB", "BYTEA", "VARBINARY", "IMAGE", "LONG RAW"},
            # Floating point
            "DOUBLE": {"DOUBLE", "DOUBLE PRECISION", "FLOAT8", "NUMBER"},
            "REAL": {"REAL", "FLOAT4", "FLOAT", "NUMBER"},
            # Boolean
            "BOOLEAN": {"BOOLEAN", "BOOL", "TINYINT"},
        }

    def normalize(
        self,
        data_type: str,
        dialect: str,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
    ) -> str:
        """Normalize a data type for the given dialect.

        Args:
            data_type: The data type to normalize (e.g., "INT", "VARCHAR2")
            dialect: The SQL dialect (postgresql, oracle, mysql, sqlserver, db2)
            precision: Optional precision value
            scale: Optional scale value

        Returns:
            Normalized data type string

        Example:
            >>> normalizer.normalize("INT", "postgresql")
            'INTEGER'
            >>> normalizer.normalize("NUMBER", "oracle", 10, 2)
            'NUMBER(10,2)'
        """
        if not data_type:
            return data_type

        # Extract precision/scale from type string if not provided
        if precision is None and scale is None:
            extracted_precision, extracted_scale = self.extract_precision_scale(data_type)
            if extracted_precision is not None:
                precision = extracted_precision
                scale = extracted_scale

        # Remove precision/scale from type string for normalization
        base_type = self._extract_base_type(data_type).upper()

        # Apply dialect-specific normalization
        dialect_mappings = self.type_equivalents.get(dialect, {})
        normalized_type = dialect_mappings.get(base_type, base_type)

        # Add precision/scale back if present, except for date/time families where we ignore precision
        if precision is not None:
            base_for_precision = self._extract_base_type(normalized_type).upper()
            if base_for_precision not in {
                "TIMESTAMP",
                "TIMESTAMP WITH TIME ZONE",
                "TIME",
                "TIME WITH TIME ZONE",
                "DATETIME",
                "DATETIME2",
                "SMALLDATETIME",
            }:
                if scale is not None:
                    normalized_type = f"{normalized_type}({precision},{scale})"
                else:
                    normalized_type = f"{normalized_type}({precision})"

        base_normalized = self._extract_base_type(normalized_type).upper()
        if base_normalized in {
            "TIMESTAMP",
            "TIMESTAMP WITH TIME ZONE",
            "TIME",
            "TIME WITH TIME ZONE",
            "DATETIME",
            "DATETIME2",
            "SMALLDATETIME",
        }:
            # Collapse SQL Server datetime family to DATETIME, and drop precision
            if base_normalized in {"DATETIME2", "SMALLDATETIME"}:
                normalized_type = "DATETIME"
            else:
                normalized_type = base_normalized

        return normalized_type

    def are_equivalent(self, type1: str, type2: str, dialect1: str, dialect2: str) -> bool:
        """Check if two data types are equivalent across dialects.

        Args:
            type1: First data type
            type2: Second data type
            dialect1: Dialect of first type
            dialect2: Dialect of second type

        Returns:
            True if types are equivalent, False otherwise

        Example:
            >>> normalizer.are_equivalent("TEXT", "CLOB", "postgresql", "oracle")
            True
            >>> normalizer.are_equivalent("INT", "VARCHAR", "mysql", "mysql")
            False
        """
        # Normalize both types
        norm_type1 = self.normalize(type1, dialect1)
        norm_type2 = self.normalize(type2, dialect2)

        # Direct match after normalization
        if norm_type1 == norm_type2:
            return True

        # Check cross-dialect equivalents
        base1 = self._extract_base_type(norm_type1).upper()
        base2 = self._extract_base_type(norm_type2).upper()

        for equivalent_set in self.cross_dialect_equivalents.values():
            if base1 in equivalent_set and base2 in equivalent_set:
                return True

        return False

    def extract_precision_scale(self, data_type: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract precision and scale from a data type string.

        Args:
            data_type: Data type with optional precision/scale (e.g., "NUMBER(10,2)")

        Returns:
            Tuple of (precision, scale), both may be None

        Example:
            >>> normalizer.extract_precision_scale("VARCHAR(100)")
            (100, None)
            >>> normalizer.extract_precision_scale("NUMBER(10,2)")
            (10, 2)
        """
        # Pattern to match: TYPE(precision) or TYPE(precision, scale)
        # More specific pattern that captures precision/scale in parentheses
        pattern = r"\((\d+)(?:,\s*(\d+))?\)"
        match = re.search(pattern, data_type)

        if match:
            precision = int(match.group(1))
            scale = int(match.group(2)) if match.group(2) else None
            return (precision, scale)

        return (None, None)

    def _extract_base_type(self, data_type: str) -> str:
        """Extract base type name without precision/scale.

        Args:
            data_type: Full data type string

        Returns:
            Base type name

        Example:
            >>> normalizer._extract_base_type("VARCHAR(100)")
            'VARCHAR'
            >>> normalizer._extract_base_type("NUMBER(10,2)")
            'NUMBER'
        """
        # Remove precision/scale in parentheses
        base_type = re.sub(r"\(.*?\)", "", data_type).strip()
        return base_type
