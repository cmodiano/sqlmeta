"""
Trigger SQL Model.

Represents a database trigger with its definition, timing, and events.
"""

from typing import Any, Dict, Optional

from sqlmeta.base import SqlObject, SqlObjectType


class Trigger(SqlObject):
    """Represents a database trigger."""

    def __init__(
        self,
        name: str,
        table_name: str,
        schema: Optional[str] = None,
        timing: Optional[str] = None,
        events: Optional[list[str]] = None,
        orientation: Optional[str] = None,
        definition: Optional[str] = None,
        enabled: bool = True,
        dialect: Optional[str] = None,
        # Grammar-based: MySQL-specific trigger properties
        definer: Optional[str] = None,  # user@host (MySQL)
    ):
        """Initialize a trigger.

        Args:
            name: Trigger name
            table_name: Name of the table the trigger is on
            schema: Schema name (optional)
            timing: When trigger fires (BEFORE, AFTER, INSTEAD OF)
            events: List of events that fire the trigger (INSERT, UPDATE, DELETE, TRUNCATE)
            orientation: Trigger level (ROW, STATEMENT)
            definition: Trigger body/definition
            enabled: Whether trigger is enabled
            dialect: SQL dialect
            definer: Definer user - user@host (MySQL grammar-based)
        """
        super().__init__(name, SqlObjectType.TRIGGER, schema, dialect)
        self.table_name = table_name
        self.timing = timing  # BEFORE, AFTER, INSTEAD OF
        self.events = events or []  # INSERT, UPDATE, DELETE, TRUNCATE (grammar-based)
        self.orientation = orientation  # ROW, STATEMENT
        self.definition = definition
        self.enabled = enabled
        # Grammar-based: CONSTRAINT TRIGGER support (PostgreSQL)
        self.is_constraint_trigger = "CONSTRAINT TRIGGER" in (definition or "").upper()
        # Grammar-based: MySQL-specific trigger properties
        self.definer = definer

    @property
    def qualified_table_name(self) -> str:
        """Get the qualified table name (schema.table).

        Returns:
            Qualified table name
        """
        if self.schema:
            return (
                f"{self.format_identifier(self.schema)}.{self.format_identifier(self.table_name)}"
            )
        return self.format_identifier(self.table_name)

    @property
    def event_str(self) -> str:
        """Get events as a formatted string.

        Returns:
            Events joined by ' OR ' (e.g., 'INSERT OR UPDATE')
        """
        return " OR ".join(self.events) if self.events else ""

    @property
    def create_statement(self) -> str:
        """Generate CREATE TRIGGER statement.

        The syntax varies by dialect.

        Returns:
            Dialect-specific CREATE TRIGGER statement
        """
        # Format identifiers properly for the dialect
        trigger_name = self.format_identifier(self.name)

        # Grammar-based: MySQL DEFINER clause
        definer_clause = ""
        if self.dialect and self.dialect.lower() in ("mysql", "mariadb") and self.definer:
            definer_clause = f"DEFINER = {self.definer} "

        # Build the statement
        stmt = f"CREATE {definer_clause}TRIGGER {trigger_name}\n"

        # Add timing
        if self.timing:
            stmt += f"  {self.timing}\n"

        # Add events
        if self.events:
            stmt += f"  {self.event_str}\n"

        # Add table reference
        stmt += f"  ON {self.qualified_table_name}\n"

        # Add orientation (for row-level triggers)
        if self.orientation == "ROW":
            if self.dialect and self.dialect.lower() in ("postgresql", "postgres"):
                stmt += "  FOR EACH ROW\n"
            elif self.dialect and self.dialect.lower() == "oracle":
                stmt += "  FOR EACH ROW\n"
            elif self.dialect and self.dialect.lower() in ("sqlserver", "mssql"):
                # SQL Server doesn't have FOR EACH ROW syntax
                pass
            else:
                stmt += "  FOR EACH ROW\n"
        elif self.orientation == "STATEMENT":
            if self.dialect and self.dialect.lower() == "oracle":
                # Oracle defaults to statement level if FOR EACH ROW is omitted
                pass

        # Add definition
        if self.definition:
            stmt += self.definition

        return stmt

    def __str__(self) -> str:
        """Return string representation of the trigger."""
        return f"Trigger {self.name} on {self.table_name}"

    def __eq__(self, other: Any) -> bool:
        """Check if two triggers are equal.

        Args:
            other: Other object to compare

        Returns:
            True if triggers are equal
        """
        if not isinstance(other, Trigger):
            return False
        return (
            super().__eq__(other)
            and self.table_name == other.table_name
            and self.timing == other.timing
            and self.events == other.events
            and self.orientation == other.orientation
            and self.definition == other.definition
            # Grammar-based: MySQL-specific properties
            and self.definer == other.definer
        )

    def __repr__(self) -> str:
        """Return detailed representation of the trigger."""
        return (
            f"Trigger(name={self.name!r}, table={self.table_name!r}, "
            f"timing={self.timing!r}, events={self.events!r}, "
            f"orientation={self.orientation!r})"
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trigger":
        """Create trigger from dictionary representation.

        Args:
            data: Dictionary with trigger attributes

        Returns:
            Trigger object
        """
        return cls(
            name=data["name"],
            table_name=data["table_name"],
            schema=data.get("schema"),
            timing=data.get("timing"),
            events=data.get("events", []),
            orientation=data.get("orientation"),
            definition=data.get("definition"),
            enabled=data.get("enabled", True),
            dialect=data.get("dialect"),
            definer=data.get("definer"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert trigger to dictionary representation.

        Returns:
            Dictionary with trigger attributes
        """
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema": self.schema,
            "object_type": self.object_type.value,
            "dialect": self.dialect,
            "timing": self.timing,
            "events": self.events,
            "orientation": self.orientation,
            "definition": self.definition,
            "enabled": self.enabled,
            "definer": self.definer,
        }
