from typing import Any, Dict, List, Optional

from sqlmeta.base import SqlObject, SqlObjectType


class Index(SqlObject):
    """Represents a database index."""

    def __init__(
        self,
        name: str,
        table_name: str,
        columns: List[str],
        schema: Optional[str] = None,
        table_schema: Optional[str] = None,
        unique: bool = False,
        type: str = "BTREE",
        condition: Optional[str] = None,
        include_columns: Optional[List[str]] = None,
        sort_directions: Optional[List[str]] = None,
        dialect: Optional[str] = None,
        # Grammar-based: MySQL-specific index properties
        online: Optional[bool] = None,  # True for ONLINE, False for OFFLINE (MySQL)
        # Grammar-based: PostgreSQL-specific index properties
        concurrently: bool = False,  # CONCURRENTLY keyword (PostgreSQL)
        # Grammar-based: Oracle-specific index properties
        tablespace: Optional[str] = None,  # TABLESPACE clause (Oracle)
    ):
        """Initialize an index.

        Args:
            name: Index name
            table_name: Name of the table being indexed
            columns: List of indexed columns
            schema: Schema name for the index
            table_schema: Schema name for the table (if different from index schema)
            unique: Whether this is a unique index
            type: Index type (BTREE, HASH, FULLTEXT, SPATIAL, etc.)
            condition: Optional WHERE condition
            include_columns: Optional INCLUDE columns (SQL Server)
            sort_directions: Optional sort directions (ASC/DESC) for each column
            dialect: SQL dialect
            online: Whether index was created with ONLINE (True) or OFFLINE (False) (MySQL grammar-based)
            concurrently: Whether index was created CONCURRENTLY (PostgreSQL grammar-based)
            tablespace: Tablespace name for the index (Oracle grammar-based)
        """
        super().__init__(name, SqlObjectType.INDEX, schema, dialect)
        self.table_name = table_name
        self.columns = columns
        # If table_schema is not provided, use the index schema
        self.table_schema = table_schema if table_schema is not None else schema
        self.unique = unique
        self.type = type
        self.condition = condition
        self.include_columns = include_columns or []
        self.sort_directions = sort_directions or []
        # Grammar-based: MySQL-specific index properties
        self.online = online
        # Grammar-based: PostgreSQL-specific index properties
        self.concurrently = concurrently
        # Grammar-based: Oracle-specific index properties
        self.tablespace = tablespace

    @property
    def create_statement(self) -> str:
        """Generate CREATE INDEX statement.

        The syntax varies by dialect.

        Returns:
            Dialect-specific CREATE INDEX statement
        """

        # Provide a default syntax dictionary
        def get_index_syntax(dialect):
            # This can be expanded for real dialects
            return {
                "supports_sort_direction": True,
                "supports_include": True,
                "supports_filtered_index": True,
            }

        syntax = get_index_syntax(self.dialect)

        # Format identifiers properly for the dialect
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        idx_name = self.format_identifier(self.name)
        table_schema_name = self.format_identifier(self.table_schema) if self.table_schema else ""
        table_name = self.format_identifier(self.table_name)

        schema_prefix = f"{schema_name}." if schema_name else ""
        table_schema_prefix = f"{table_schema_name}." if table_schema_name else ""

        stmt = "CREATE "
        # Grammar-based: MySQL ONLINE/OFFLINE clause
        if self.dialect and self.dialect.lower() in ("mysql", "mariadb"):
            if self.online is True:
                stmt += "ONLINE "
            elif self.online is False:
                stmt += "OFFLINE "
        if self.unique:
            stmt += "UNIQUE "
        # Grammar-based: PostgreSQL CONCURRENTLY clause
        if (
            self.concurrently
            and self.dialect
            and self.dialect.lower() in ("postgresql", "postgres")
        ):
            stmt += "CONCURRENTLY "
        # Add index type if supported by dialect
        if self.dialect and self.dialect.lower() == "mysql":
            # MySQL supports FULLTEXT and SPATIAL as index types
            if self.type.upper() in ("FULLTEXT", "SPATIAL"):
                stmt += f"{self.type.upper()} "
            elif self.type.upper() != "BTREE":
                stmt += f"{self.type} "

        stmt += f"INDEX {schema_prefix}{idx_name} ON {table_schema_prefix}{table_name}"

        # Add columns with sort directions if specified
        supports_sort = syntax.get("supports_sort_direction", True)

        if (
            supports_sort
            and self.sort_directions
            and len(self.sort_directions) == len(self.columns)
        ):
            column_list = [
                f"{self.format_identifier(col)} {direction}"
                for col, direction in zip(self.columns, self.sort_directions)
            ]
        else:
            column_list = [self.format_identifier(col) for col in self.columns]

        stmt += f" ({', '.join(column_list)})"

        # Add INCLUDE clause for SQL Server style indexes if supported
        if syntax.get("supports_include", False) and self.include_columns:
            include_columns = [self.format_identifier(col) for col in self.include_columns]
            stmt += f" INCLUDE ({', '.join(include_columns)})"

        # Add WHERE clause for filtered indexes if supported
        if syntax.get("supports_filtered_index", False) and self.condition:
            stmt += f" WHERE {self.condition}"

        # Add index type if Oracle
        if self.dialect and self.dialect.lower() == "oracle" and self.type != "BTREE":
            if self.type == "BITMAP":
                stmt = stmt.replace("INDEX", "BITMAP INDEX")

        # Grammar-based: Add TABLESPACE clause for Oracle
        if self.dialect and self.dialect.lower() == "oracle" and self.tablespace:
            stmt += f" TABLESPACE {self.format_identifier(self.tablespace)}"

        return stmt

    @property
    def drop_statement(self) -> str:
        """Generate DROP INDEX statement.

        Returns:
            SQL DROP INDEX statement for this index
        """
        schema_prefix = self.format_identifier(self.schema) + "." if self.schema else ""
        idx_name = self.format_identifier(self.name)
        table_name = self.format_identifier(self.table_name)
        table_schema_prefix = (
            self.format_identifier(self.table_schema) + "." if self.table_schema else ""
        )

        if self.dialect and self.dialect.lower() == "sqlserver":
            # SQL Server requires table name in DROP INDEX
            return f"DROP INDEX IF EXISTS {idx_name} ON {table_schema_prefix}{table_name}"
        else:
            # PostgreSQL, Oracle, MySQL, DB2
            return f"DROP INDEX IF EXISTS {schema_prefix}{idx_name}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Index":
        """Create index from dictionary representation.

        Args:
            data: Dictionary with index attributes

        Returns:
            Index object
        """
        return cls(
            name=data["name"],
            table_name=data["table_name"],
            columns=data["columns"],
            schema=data.get("schema"),
            table_schema=data.get("table_schema"),
            unique=data.get("unique", False),
            type=data.get("type", "BTREE"),
            condition=data.get("condition"),
            include_columns=data.get("include_columns"),
            sort_directions=data.get("sort_directions"),
            dialect=data.get("dialect"),
            online=data.get("online"),
            concurrently=data.get("concurrently", False),
            tablespace=data.get("tablespace"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert index to dictionary representation.

        Returns:
            Dictionary with index attributes
        """
        return {
            "name": self.name,
            "schema": self.schema,
            "object_type": self.object_type.value,
            "dialect": self.dialect,
            "table_name": self.table_name,
            "table_schema": self.table_schema,
            "columns": self.columns,
            "unique": self.unique,
            "type": self.type,
            "condition": self.condition,
            "include_columns": self.include_columns,
            "sort_directions": self.sort_directions,
            "online": self.online,
            "concurrently": self.concurrently,
            "tablespace": self.tablespace,
        }
