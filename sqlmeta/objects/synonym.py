"""Synonym SQL model class."""

from typing import Any, Optional

from sqlmeta.base import SqlObject, SqlObjectType


class Synonym(SqlObject):
    """Represents a database synonym (alias for another object)."""

    def __init__(
        self,
        name: str,
        target_object: str,
        schema: Optional[str] = None,
        target_schema: Optional[str] = None,
        target_database: Optional[str] = None,
        db_link: Optional[str] = None,
        dialect: Optional[str] = None,
    ):
        """Initialize a synonym.

        Args:
            name: Synonym name
            target_object: Name of the target object this synonym points to
            schema: Schema where the synonym is defined (optional)
            target_schema: Schema of the target object (optional)
            target_database: Database of the target object (optional, SQL Server)
            db_link: Database link for remote objects (optional, Oracle)
            dialect: SQL dialect
        """
        super().__init__(name, SqlObjectType.SYNONYM, schema, dialect)
        self.target_object = target_object
        self.target_schema = target_schema
        self.target_database = target_database
        self.db_link = db_link

    @property
    def target_full_name(self) -> str:
        """
        Get the fully qualified name of the target object.

        Returns:
            Fully qualified target name including schema/database/link
        """
        parts = []

        # Add target database if present (SQL Server)
        if self.target_database:
            parts.append(self.format_identifier(self.target_database))

        # Add target schema if present
        if self.target_schema:
            parts.append(self.format_identifier(self.target_schema))

        # Add target object name
        parts.append(self.format_identifier(self.target_object))

        result = ".".join(parts)

        # Add database link if present (Oracle)
        if self.db_link:
            result += f"@{self.format_identifier(self.db_link)}"

        return result

    @property
    def create_statement(self) -> str:
        """
        Generate CREATE SYNONYM statement.

        The syntax varies by dialect.

        Returns:
            Dialect-specific CREATE SYNONYM statement
        """
        # Format synonym name with schema if present
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        synonym_name = self.format_identifier(self.name)
        schema_prefix = f"{schema_name}." if schema_name else ""

        # Use dialect-specific syntax
        if self.dialect and self.dialect.lower() == "oracle":
            # Oracle: CREATE [OR REPLACE] [PUBLIC] SYNONYM
            stmt = f"CREATE OR REPLACE SYNONYM {schema_prefix}{synonym_name}"
        elif self.dialect and self.dialect.lower() == "sqlserver":
            # SQL Server: CREATE SYNONYM
            stmt = f"CREATE SYNONYM {schema_prefix}{synonym_name}"
        elif self.dialect and self.dialect.lower() == "db2":
            # DB2: CREATE ALIAS (synonym equivalent)
            stmt = f"CREATE ALIAS {schema_prefix}{synonym_name}"
        else:
            # Generic syntax
            stmt = f"CREATE SYNONYM {schema_prefix}{synonym_name}"

        # Add FOR clause with target
        stmt += f"\nFOR {self.target_full_name}"

        return stmt

    @property
    def drop_statement(self) -> str:
        """
        Generate DROP SYNONYM statement.

        Returns:
            Dialect-specific DROP SYNONYM statement
        """
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        synonym_name = self.format_identifier(self.name)
        schema_prefix = f"{schema_name}." if schema_name else ""

        if self.dialect and self.dialect.lower() == "db2":
            return f"DROP ALIAS {schema_prefix}{synonym_name}"
        else:
            return f"DROP SYNONYM {schema_prefix}{synonym_name}"

    def __str__(self) -> str:
        """Return string representation of the synonym."""
        return f"{self.object_type.value} {self.name} -> {self.target_full_name}"

    def __eq__(self, other: Any) -> bool:
        """Check if two synonyms are equal."""
        if not isinstance(other, Synonym):
            return False
        return (
            super().__eq__(other)
            and self.target_object.lower() == other.target_object.lower()
            and (self.target_schema or "").lower() == (other.target_schema or "").lower()
            and (self.target_database or "").lower() == (other.target_database or "").lower()
            and (self.db_link or "").lower() == (other.db_link or "").lower()
        )

    def __hash__(self) -> int:
        """Return hash of the synonym."""
        return hash(
            (
                self.name.lower(),
                self.object_type,
                (self.schema or "").lower(),
                self.target_object.lower(),
                (self.target_schema or "").lower(),
            )
        )
