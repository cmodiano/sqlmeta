from typing import Any, Dict, Optional

from sqlmeta.base import SqlObject, SqlObjectType


class Sequence(SqlObject):
    """Represents a database sequence."""

    def __init__(
        self,
        name: str,
        schema: Optional[str] = None,
        start_with: Optional[int] = None,
        increment_by: Optional[int] = None,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        cycle: bool = False,
        cache: Optional[int] = None,
        dialect: Optional[str] = None,
        # Grammar-based: PostgreSQL-specific sequence properties
        temp: bool = False,  # TEMP or TEMPORARY keyword (PostgreSQL)
    ):
        """Initialize a sequence.

        Args:
            name: Sequence name
            schema: Schema name
            start_with: Starting value
            increment_by: Increment value
            min_value: Minimum value
            max_value: Maximum value
            cycle: Whether to cycle when reaching max_value
            cache: Cache size
            dialect: SQL dialect
            temp: Whether sequence is TEMPORARY (PostgreSQL grammar-based)
        """
        super().__init__(name, SqlObjectType.SEQUENCE, schema, dialect)
        self.start_with = start_with
        self.increment_by = increment_by or 1
        self.min_value = min_value
        self.max_value = max_value
        self.cycle = cycle
        self.cache = cache
        # Grammar-based: PostgreSQL-specific sequence properties
        self.temp = temp

    @property
    def create_statement(self) -> str:
        """Generate CREATE SEQUENCE statement.

        The syntax varies by dialect.

        Returns:
            Dialect-specific CREATE SEQUENCE statement
        """
        # Format identifiers properly for the dialect
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        seq_name = self.format_identifier(self.name)
        schema_prefix = f"{schema_name}." if schema_name else ""

        # Grammar-based: PostgreSQL TEMP/TEMPORARY sequence support
        temp_prefix = ""
        if self.temp and self.dialect and self.dialect.lower() in ("postgresql", "postgres"):
            temp_prefix = "TEMPORARY "

        stmt = f"CREATE {temp_prefix}SEQUENCE {schema_prefix}{seq_name}"

        # Add START WITH clause
        if self.start_with is not None:
            stmt += f" START WITH {self.start_with}"

        # Add INCREMENT BY clause
        if self.increment_by is not None and self.increment_by != 1:
            stmt += f" INCREMENT BY {self.increment_by}"

        # Add MINVALUE clause
        if self.min_value is not None:
            stmt += f" MINVALUE {self.min_value}"

        # Add MAXVALUE clause
        if self.max_value is not None:
            stmt += f" MAXVALUE {self.max_value}"

        # Add CYCLE clause
        if self.cycle:
            stmt += " CYCLE"
        else:
            stmt += " NOCYCLE"

        # Add CACHE clause
        if self.cache is not None:
            stmt += f" CACHE {self.cache}"

        return stmt

    @property
    def drop_statement(self) -> str:
        """Generate DROP SEQUENCE statement.

        Returns:
            SQL DROP SEQUENCE statement for this sequence
        """
        schema_prefix = self.format_identifier(self.schema) + "." if self.schema else ""
        seq_name = self.format_identifier(self.name)

        if self.dialect and self.dialect.lower() == "oracle":
            return f"DROP SEQUENCE {schema_prefix}{seq_name}"
        else:
            # PostgreSQL, SQL Server, MySQL, DB2
            return f"DROP SEQUENCE IF EXISTS {schema_prefix}{seq_name}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Sequence":
        """Create sequence from dictionary representation.

        Args:
            data: Dictionary with sequence attributes

        Returns:
            Sequence object
        """
        return cls(
            name=data["name"],
            schema=data.get("schema"),
            start_with=data.get("start_with"),
            increment_by=data.get("increment_by", 1),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            cycle=data.get("cycle", False),
            cache=data.get("cache"),
            dialect=data.get("dialect"),
            temp=data.get("temp", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert sequence to dictionary representation.

        Returns:
            Dictionary with sequence attributes
        """
        return {
            "name": self.name,
            "schema": self.schema,
            "object_type": self.object_type.value,
            "dialect": self.dialect,
            "start_with": self.start_with,
            "increment_by": self.increment_by,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "cycle": self.cycle,
            "cache": self.cache,
            "temp": self.temp,
        }
