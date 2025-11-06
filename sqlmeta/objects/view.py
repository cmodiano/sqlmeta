from typing import Any, Dict, List, Optional

from sqlmeta.base import SqlObject, SqlObjectType


class View(SqlObject):
    """Represents a database view.

    Supports both regular views and materialized views with refresh options.
    """

    def __init__(
        self,
        name: str,
        schema: Optional[str] = None,
        query: Optional[str] = None,
        columns: Optional[List[str]] = None,
        materialized: bool = False,
        dialect: Optional[str] = None,
        # Materialized view specific properties
        is_populated: Optional[bool] = None,
        refresh_method: Optional[str] = None,
        refresh_mode: Optional[str] = None,
        fast_refreshable: Optional[bool] = None,
        last_refresh: Optional[str] = None,
        # Grammar-based: UNLOGGED materialized views (PostgreSQL)
        unlogged: Optional[bool] = None,
        # Grammar-based: MySQL-specific view properties
        algorithm: Optional[str] = None,  # MERGE, TEMPTABLE, UNDEFINED (MySQL)
        sql_security: Optional[str] = None,  # DEFINER, INVOKER (MySQL)
        definer: Optional[str] = None,  # user@host (MySQL)
        # Grammar-based: Oracle-specific view properties
        force: Optional[bool] = None,  # FORCE (True) or NOFORCE (False) (Oracle)
    ):
        """Initialize a view.

        Args:
            name: View name
            schema: Schema name (optional)
            query: SELECT query that defines the view
            columns: List of column names (optional)
            materialized: Whether the view is materialized
            dialect: SQL dialect
            is_populated: Whether the materialized view is populated (PostgreSQL, Oracle)
            refresh_method: Refresh method - FAST, COMPLETE, FORCE, MANUAL (Oracle, DB2)
            refresh_mode: Refresh mode - ON DEMAND, ON COMMIT (Oracle)
            fast_refreshable: Whether fast refresh is available (Oracle)
            last_refresh: Timestamp of last refresh (Oracle, DB2)
            unlogged: Whether the materialized view is UNLOGGED (PostgreSQL grammar-based)
            algorithm: View algorithm - MERGE, TEMPTABLE, UNDEFINED (MySQL grammar-based)
            sql_security: SQL security - DEFINER, INVOKER (MySQL grammar-based)
            definer: Definer user - user@host (MySQL grammar-based)
            force: Whether view is created with FORCE (True) or NOFORCE (False) (Oracle grammar-based)
        """
        object_type = SqlObjectType.MATERIALIZED_VIEW if materialized else SqlObjectType.VIEW
        super().__init__(name, object_type, schema, dialect)
        self.query = query
        self.columns = columns or []
        self.materialized = materialized

        # Materialized view specific properties
        self.is_populated = is_populated
        self.refresh_method = refresh_method
        self.refresh_mode = refresh_mode
        self.fast_refreshable = fast_refreshable
        self.last_refresh = last_refresh
        # Grammar-based: UNLOGGED materialized views (PostgreSQL)
        self.unlogged = unlogged
        # Grammar-based: MySQL-specific view properties
        self.algorithm = algorithm  # MERGE, TEMPTABLE, UNDEFINED
        self.sql_security = sql_security  # DEFINER, INVOKER
        self.definer = definer  # user@host
        # Grammar-based: Oracle-specific view properties
        self.force = force  # FORCE (True) or NOFORCE (False)

    @property
    def create_statement(self) -> str:
        """Generate CREATE VIEW statement.

        The syntax varies by dialect.

        Returns:
            Dialect-specific CREATE VIEW statement
        """
        # Format identifiers properly for the dialect
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        view_name = self.format_identifier(self.name)
        schema_prefix = f"{schema_name}." if schema_name else ""

        # Grammar-based: Use dialect-specific syntax
        create_keyword = "CREATE"
        force_clause = ""
        if self.dialect and self.dialect.lower() == "oracle":
            create_keyword = "CREATE OR REPLACE"
            # Grammar-based: Add FORCE/NOFORCE clause for Oracle
            if self.force is True:
                force_clause = "FORCE "
            elif self.force is False:
                force_clause = "NOFORCE "

        # Determine view type
        # Grammar-based: Support UNLOGGED for materialized views (PostgreSQL)
        unlogged_prefix = (
            "UNLOGGED "
            if (
                self.materialized
                and self.unlogged
                and self.dialect
                and self.dialect.lower() == "postgresql"
            )
            else ""
        )
        view_type = "MATERIALIZED VIEW" if self.materialized else "VIEW"

        # Grammar-based: MySQL-specific view options
        algorithm_clause = ""
        definer_clause = ""
        sql_security_clause = ""
        if self.dialect and self.dialect.lower() in ("mysql", "mariadb"):
            if self.algorithm:
                algorithm_clause = f"ALGORITHM = {self.algorithm} "
            if self.definer:
                definer_clause = f"DEFINER = {self.definer} "
            if self.sql_security:
                sql_security_clause = f"SQL SECURITY {self.sql_security} "

        # Build the statement
        mysql_prefix = (
            f"{algorithm_clause}{definer_clause}{sql_security_clause}"
            if self.dialect and self.dialect.lower() in ("mysql", "mariadb")
            else ""
        )
        stmt = f"{create_keyword} {force_clause}{mysql_prefix}{unlogged_prefix}{view_type} {schema_prefix}{view_name}"

        # Add columns if specified
        if self.columns:
            formatted_columns = [self.format_identifier(col) for col in self.columns]
            col_list = ", ".join(formatted_columns)
            stmt += f" ({col_list})"

        # Add query
        if self.query:
            stmt += f"\nAS\n{self.query}"

        # Add materialized view options by dialect
        if self.materialized:
            if self.dialect and self.dialect.lower() == "oracle":
                stmt += "\nBUILD IMMEDIATE"
            elif self.dialect and self.dialect.lower() == "postgres":
                stmt += "\nWITH DATA"

        return stmt

    @property
    def drop_statement(self) -> str:
        """Generate DROP VIEW statement.

        Returns:
            SQL DROP VIEW statement for this view
        """
        schema_prefix = self.format_identifier(self.schema) + "." if self.schema else ""
        view_name = self.format_identifier(self.name)
        view_type = "MATERIALIZED VIEW" if self.materialized else "VIEW"

        if self.dialect and self.dialect.lower() == "oracle":
            return f"DROP {view_type} {schema_prefix}{view_name}"
        else:
            # PostgreSQL, SQL Server, MySQL, DB2
            return f"DROP {view_type} IF EXISTS {schema_prefix}{view_name}"

    def __str__(self) -> str:
        """Return string representation of the view."""
        return self.create_statement

    def __eq__(self, other: Any) -> bool:
        """Check if two views are equal."""
        if not isinstance(other, View):
            return False
        return (
            super().__eq__(other)
            and self.query == other.query
            and self.columns == other.columns
            and self.materialized == other.materialized
            and self.is_populated == other.is_populated
            and self.refresh_method == other.refresh_method
            and self.refresh_mode == other.refresh_mode
            and self.fast_refreshable == other.fast_refreshable
            # Grammar-based: MySQL-specific properties
            and self.algorithm == other.algorithm
            and self.sql_security == other.sql_security
            and self.definer == other.definer
            # Grammar-based: Oracle-specific properties
            and self.force == other.force
            # Grammar-based: PostgreSQL-specific properties
            and self.unlogged == other.unlogged
            # Note: last_refresh is not compared as it changes with each refresh
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "View":
        """Create view from dictionary representation.

        Args:
            data: Dictionary with view attributes

        Returns:
            View object
        """
        return cls(
            name=data["name"],
            schema=data.get("schema"),
            query=data.get("query"),
            columns=data.get("columns", []),
            materialized=data.get("materialized", False),
            dialect=data.get("dialect"),
            is_populated=data.get("is_populated"),
            refresh_method=data.get("refresh_method"),
            refresh_mode=data.get("refresh_mode"),
            fast_refreshable=data.get("fast_refreshable"),
            last_refresh=data.get("last_refresh"),
            unlogged=data.get("unlogged"),
            algorithm=data.get("algorithm"),
            sql_security=data.get("sql_security"),
            definer=data.get("definer"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert view to dictionary representation.

        Returns:
            Dictionary with view attributes
        """
        result = {
            "name": self.name,
            "schema": self.schema,
            "object_type": self.object_type.value,
            "dialect": self.dialect,
            "query": self.query,
            "columns": self.columns,
            "materialized": self.materialized,
        }

        # Add materialized view specific properties if present
        if self.is_populated is not None:
            result["is_populated"] = self.is_populated
        if self.refresh_method:
            result["refresh_method"] = self.refresh_method
        if self.refresh_mode:
            result["refresh_mode"] = self.refresh_mode
        if self.fast_refreshable is not None:
            result["fast_refreshable"] = self.fast_refreshable
        if self.last_refresh:
            result["last_refresh"] = self.last_refresh
        # Grammar-based: MySQL-specific properties
        if self.algorithm:
            result["algorithm"] = self.algorithm
        if self.sql_security:
            result["sql_security"] = self.sql_security
        if self.definer:
            result["definer"] = self.definer
        # Grammar-based: Oracle-specific properties
        if self.force is not None:
            result["force"] = self.force
        # Grammar-based: PostgreSQL-specific properties
        if self.unlogged is not None:
            result["unlogged"] = self.unlogged

        return result
