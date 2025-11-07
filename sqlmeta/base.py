from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from sqlmeta.objects.database_link import DatabaseLink
    from sqlmeta.objects.event import Event
    from sqlmeta.objects.extension import Extension
    from sqlmeta.objects.foreign_data_wrapper import ForeignDataWrapper
    from sqlmeta.objects.foreign_server import ForeignServer
    from sqlmeta.objects.index import Index
    from sqlmeta.objects.package import Package
    from sqlmeta.objects.partition import Partition
    from sqlmeta.objects.procedure import Procedure
    from sqlmeta.objects.sequence import Sequence
    from sqlmeta.objects.synonym import Synonym
    from sqlmeta.objects.table import Table
    from sqlmeta.objects.trigger import Trigger
    from sqlmeta.objects.user_defined_type import UserDefinedType
    from sqlmeta.objects.view import View


class SqlObjectType(Enum):
    """SQL object types that can be created, modified, or dropped."""

    TABLE = "TABLE"
    VIEW = "VIEW"
    INDEX = "INDEX"
    SEQUENCE = "SEQUENCE"
    PROCEDURE = "PROCEDURE"
    FUNCTION = "FUNCTION"
    TRIGGER = "TRIGGER"
    CONSTRAINT = "CONSTRAINT"
    SCHEMA = "SCHEMA"
    DATABASE = "DATABASE"
    TYPE = "TYPE"
    ROLE = "ROLE"
    USER = "USER"
    MATERIALIZED_VIEW = "MATERIALIZED_VIEW"
    PACKAGE = "PACKAGE"
    PACKAGE_BODY = "PACKAGE_BODY"
    SYNONYM = "SYNONYM"
    EVENT = "EVENT"  # MySQL scheduled events
    PARTITION = "PARTITION"  # Table partitions
    DATABASE_LINK = "DATABASE_LINK"  # Oracle database links
    EXTENSION = "EXTENSION"  # PostgreSQL extensions
    FOREIGN_DATA_WRAPPER = "FOREIGN_DATA_WRAPPER"  # PostgreSQL foreign data wrappers
    FOREIGN_SERVER = "FOREIGN_SERVER"  # PostgreSQL foreign servers
    UNKNOWN = "UNKNOWN"


class ConstraintType(Enum):
    """Types of SQL constraints."""

    PRIMARY_KEY = "PRIMARY KEY"
    FOREIGN_KEY = "FOREIGN KEY"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    NOT_NULL = "NOT NULL"
    DEFAULT = "DEFAULT"
    EXCLUDE = "EXCLUDE"
    UNKNOWN = "UNKNOWN"


class SqlObject:
    """Base class for SQL objects."""

    name: str
    object_type: SqlObjectType
    schema: Optional[str]
    dialect: Optional[str]
    explicit_properties: Optional[Dict[str, bool]]

    def __init__(
        self,
        name: str,
        object_type: Union[SqlObjectType, str],
        schema: Optional[str] = None,
        dialect: Optional[str] = None,
    ) -> None:
        """Initialize a SQL object.

        Args:
            name: Object name
            object_type: Object type
            schema: Schema name (optional)
            dialect: SQL dialect (optional)
        """
        self.name = name

        # Handle both enum and string object types
        if isinstance(object_type, str):
            try:
                self.object_type = SqlObjectType[object_type.upper()]
            except KeyError:
                self.object_type = SqlObjectType.UNKNOWN
        else:
            self.object_type = object_type

        self.schema = schema
        self.dialect = dialect
        self.explicit_properties = {}

    def __str__(self) -> str:
        """Return string representation of the object."""
        if self.schema:
            return f"{self.object_type.value} {self.schema}.{self.name}"
        return f"{self.object_type.value} {self.name}"

    def __eq__(self, other: Any) -> bool:
        """Check if two SQL objects are equal."""
        if not isinstance(other, SqlObject):
            return False
        return (
            self.name.lower() == other.name.lower()
            and self.object_type == other.object_type
            and (self.schema or "").lower() == (other.schema or "").lower()
        )

    def __hash__(self) -> int:
        """Return hash of the object."""
        return hash((self.name.lower(), self.object_type, (self.schema or "").lower()))

    def format_identifier(self, identifier: str) -> str:
        """Format an identifier according to the SQL dialect.

        Args:
            identifier: The identifier to format

        Returns:
            Formatted identifier
        """
        if not identifier:
            return identifier

        # Default formatting - can be overridden by subclasses
        if self.dialect and self.dialect.lower() in ["postgresql", "oracle"]:
            # PostgreSQL and Oracle use double quotes for case-sensitive identifiers
            return f'"{identifier}"'
        elif self.dialect and self.dialect.lower() in ["mysql", "mariadb"]:
            # MySQL uses backticks
            return f"`{identifier}`"
        elif self.dialect and self.dialect.lower() == "sqlserver":
            # SQL Server uses square brackets
            return f"[{identifier}]"
        else:
            # Default: no quoting
            return identifier

    def mark_property_explicit(self, property_name: str) -> None:
        """Mark a property as explicitly defined (not using a schema default).

        Args:
            property_name: The name of the property
        """
        if self.explicit_properties is None:
            self.explicit_properties = {}
        self.explicit_properties[property_name] = True

    def is_property_explicit(self, property_name: str) -> bool:
        """Check if a property was explicitly defined.

        Args:
            property_name: The name of the property

        Returns:
            True if the property was explicitly defined, False otherwise
        """
        if self.explicit_properties is None:
            return False
        return self.explicit_properties.get(property_name, False)

    def compare_with_defaults(
        self, other: "SqlObject", schema_defaults: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Compare two SQL objects, taking into account schema defaults.

        Args:
            other: The other SQL object to compare with
            schema_defaults: Dictionary of schema default values

        Returns:
            Dictionary of differences between the objects
        """
        if not isinstance(other, SqlObject) or self.object_type != other.object_type:
            return {"error": "Cannot compare objects of different types"}

        schema_defaults = schema_defaults or {}
        differences = {}

        # Basic properties comparison
        if self.name.lower() != other.name.lower():
            differences["name"] = {"self": self.name, "other": other.name}

        if (self.schema or "").lower() != (other.schema or "").lower():
            # Use empty string if schema is None to satisfy type checker
            differences["schema"] = {"self": self.schema or "", "other": other.schema or ""}

        # Subclasses should override this method to compare specific properties
        return differences


class SqlColumn:
    """Represents a column in a database table."""

    def __init__(
        self,
        name: str,
        data_type: str,
        is_nullable: bool = True,
        default_value: Optional[str] = None,
        is_primary_key: bool = False,
        is_unique: bool = False,
        constraints: Optional[List["SqlConstraint"]] = None,
        dialect: Optional[str] = None,
        # Identity/Auto-increment metadata
        is_identity: bool = False,
        identity_generation: Optional[str] = None,
        identity_seed: Optional[int] = None,
        identity_increment: Optional[int] = None,
        # Computed/Generated column metadata
        is_computed: bool = False,
        computed_expression: Optional[str] = None,
        computed_stored: bool = False,
        # Comment metadata
        comment: Optional[str] = None,
        # Additional metadata
        ordinal_position: Optional[int] = None,
    ):
        """Initialize a SQL column.

        Args:
            name: Column name
            data_type: Data type of the column
            is_nullable: Whether the column can be NULL
            default_value: Default value of the column
            is_primary_key: Whether this column is a primary key
            is_unique: Whether this column has a unique constraint
            constraints: List of constraints on this column
            dialect: SQL dialect
            is_identity: Whether this is an identity/auto-increment column
            identity_generation: Identity generation strategy (ALWAYS, BY DEFAULT)
            identity_seed: Starting value for identity column
            identity_increment: Increment value for identity column
            is_computed: Whether this is a computed/generated column
            computed_expression: Expression used to compute the column value
            computed_stored: Whether computed column is physically stored (vs virtual)
            comment: Column comment/description
            ordinal_position: Position of column in table (1-based)
        """
        self.name = name
        self.data_type = data_type
        self.nullable = is_nullable
        self.default_value = default_value
        self.is_primary_key = is_primary_key
        self.is_unique = is_unique
        self.constraints = constraints or []
        self.dialect = dialect

        # Identity column metadata
        self.is_identity = is_identity
        self.identity_generation = identity_generation  # ALWAYS, BY DEFAULT
        self.identity_seed = identity_seed
        self.identity_increment = identity_increment

        # Computed column metadata
        self.is_computed = is_computed
        self.computed_expression = computed_expression
        self.computed_stored = computed_stored

        # Documentation
        self.comment = comment

        # Position metadata
        self.ordinal_position = ordinal_position

        self.explicit_properties: Dict[str, bool] = {}

    def __str__(self) -> str:
        """Return string representation of the column."""
        return f"{self.name} {self.data_type}" + (" NOT NULL" if not self.nullable else "")

    def __eq__(self, other: Any) -> bool:
        """Check if two columns are equal."""
        if not isinstance(other, SqlColumn):
            return False
        return (
            self.name.lower() == other.name.lower()
            and self.data_type.lower() == other.data_type.lower()
        )

    def __hash__(self) -> int:
        """Return hash of the column."""
        return hash((self.name.lower(), self.data_type.lower()))

    def mark_property_explicit(self, property_name: str) -> None:
        """Mark a property as explicitly defined (not using a schema default).

        Args:
            property_name: The name of the property
        """
        self.explicit_properties[property_name] = True

    def is_property_explicit(self, property_name: str) -> bool:
        """Check if a property was explicitly defined.

        Args:
            property_name: The name of the property

        Returns:
            True if the property was explicitly defined, False otherwise
        """
        return bool(self.explicit_properties.get(property_name, False))


class SqlConstraint:
    """Represents a constraint in a database table."""

    def __init__(
        self,
        constraint_type: Union[ConstraintType, str],
        name: Optional[str] = None,
        column_names: Optional[List[str]] = None,
        reference_table: Optional[str] = None,
        reference_columns: Optional[List[str]] = None,
        check_expression: Optional[str] = None,
        dialect: Optional[str] = None,
    ):
        """Initialize a SQL constraint.

        Args:
            constraint_type: Type of constraint
            name: Constraint name
            column_names: Names of the columns in the constraint
            reference_table: Table referenced by a foreign key
            reference_columns: Columns referenced by a foreign key
            check_expression: Expression used in a check constraint
            dialect: SQL dialect
        """
        # Handle both enum and string constraint types
        if isinstance(constraint_type, str):
            try:
                self.constraint_type = ConstraintType[constraint_type.upper().replace(" ", "_")]
            except KeyError:
                self.constraint_type = ConstraintType.UNKNOWN
        else:
            self.constraint_type = constraint_type

        self.name = name
        self.column_names = column_names or []
        self.columns = self.column_names  # Alias for compatibility
        self.reference_table = reference_table
        self.reference_columns = reference_columns or []
        self.reference_schema: Optional[str] = None  # Add reference_schema attribute
        self.check_expression = check_expression
        self.dialect = dialect
        self.explicit_properties: Dict[str, bool] = {}

    def __str__(self) -> str:
        """Return string representation of the constraint."""
        if self.name:
            return f"{self.constraint_type.value} {self.name} ({', '.join(self.column_names)})"
        return f"{self.constraint_type.value} ({', '.join(self.column_names)})"

    def __eq__(self, other: Any) -> bool:
        """Check if two constraints are equal."""
        if not isinstance(other, SqlConstraint):
            return False
        return (
            self.constraint_type == other.constraint_type
            and (self.name or "").lower() == (other.name or "").lower()
            and set(col.lower() for col in self.column_names)
            == set(col.lower() for col in other.column_names)
        )

    def __hash__(self) -> int:
        """Return hash of the constraint."""
        return hash(
            (
                self.constraint_type,
                (self.name or "").lower(),
                tuple(sorted(col.lower() for col in self.column_names)),
            )
        )

    def mark_property_explicit(self, property_name: str) -> None:
        """Mark a property as explicitly defined (not using a schema default).

        Args:
            property_name: The name of the property
        """
        self.explicit_properties[property_name] = True

    def is_property_explicit(self, property_name: str) -> bool:
        """Check if a property was explicitly defined.

        Args:
            property_name: The name of the property

        Returns:
            True if the property was explicitly defined, False otherwise
        """
        return bool(self.explicit_properties.get(property_name, False))
