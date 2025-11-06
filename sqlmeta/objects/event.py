"""MySQL Event SQL Model."""

from typing import Any, Dict, Optional

from sqlmeta.base import SqlObject, SqlObjectType


class Event(SqlObject):
    """Represents a MySQL scheduled event."""

    def __init__(
        self,
        name: str,
        schema: Optional[str] = None,
        definition: Optional[str] = None,
        schedule: Optional[str] = None,
        enabled: bool = True,
        comment: Optional[str] = None,
        definer: Optional[str] = None,
        event_type: str = "ONE TIME",  # ONE TIME or RECURRING
        dialect: Optional[str] = "mysql",
    ):
        """Initialize a MySQL event.

        Args:
            name: Event name
            schema: Schema/database name (optional)
            definition: Event body (DO clause)
            schedule: Schedule expression (AT or EVERY clause)
            enabled: Whether the event is enabled
            comment: Event comment/description
            definer: User who defined the event
            event_type: Event type (ONE TIME or RECURRING)
            dialect: SQL dialect (defaults to mysql)
        """
        super().__init__(name, SqlObjectType.EVENT, schema, dialect)
        self.definition = definition
        self.schedule = schedule
        self.enabled = enabled
        self.comment = comment
        self.definer = definer
        self.event_type = event_type

    @property
    def create_statement(self) -> str:
        """Generate CREATE EVENT statement.

        Returns:
            CREATE EVENT statement
        """
        # Format identifiers
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        event_name = self.format_identifier(self.name)
        schema_prefix = f"{schema_name}." if schema_name else ""

        stmt = f"CREATE EVENT {schema_prefix}{event_name}\n"

        # Add schedule
        if self.schedule:
            stmt += f"  ON SCHEDULE {self.schedule}\n"

        # Add status
        status = "ENABLE" if self.enabled else "DISABLE"
        stmt += f"  {status}\n"

        # Add comment
        if self.comment:
            stmt += f"  COMMENT '{self.comment}'\n"

        # Add definition
        if self.definition:
            stmt += f"  DO\n{self.definition}"

        return stmt

    def __str__(self) -> str:
        """Return string representation of the event."""
        qualified = f"{self.schema}.{self.name}" if self.schema else self.name
        status = "enabled" if self.enabled else "disabled"
        return f"Event {qualified} ({self.event_type}, {status})"

    def __eq__(self, other: Any) -> bool:
        """Check if two events are equal."""
        if not isinstance(other, Event):
            return False
        return (
            super().__eq__(other)
            and self.definition == other.definition
            and self.schedule == other.schedule
            and self.enabled == other.enabled
            and self.event_type == other.event_type
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary representation.

        Args:
            data: Dictionary with event attributes

        Returns:
            Event object
        """
        return cls(
            name=data["name"],
            schema=data.get("schema"),
            definition=data.get("definition"),
            schedule=data.get("schedule"),
            enabled=data.get("enabled", True),
            comment=data.get("comment"),
            definer=data.get("definer"),
            event_type=data.get("event_type", "ONE TIME"),
            dialect=data.get("dialect", "mysql"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation.

        Returns:
            Dictionary with event attributes
        """
        return {
            "name": self.name,
            "schema": self.schema,
            "object_type": self.object_type.value,
            "dialect": self.dialect,
            "definition": self.definition,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "comment": self.comment,
            "definer": self.definer,
            "event_type": self.event_type,
        }
