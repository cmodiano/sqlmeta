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


class SqlStatementType(Enum):
    """SQL statement types."""

    CREATE = "CREATE"
    ALTER = "ALTER"
    DROP = "DROP"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SELECT = "SELECT"
    MERGE = "MERGE"
    TRUNCATE = "TRUNCATE"
    GRANT = "GRANT"
    REVOKE = "REVOKE"
    COMMENT = "COMMENT"
    DECLARE = "DECLARE"
    BEGIN = "BEGIN"
    CALL = "CALL"
    EXECUTE = "EXECUTE"
    DDL = "DDL"
    DML = "DML"
    QUERY = "QUERY"
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


class SqlStatement:
    """Represents a parsed SQL statement."""

    sql_text: str
    statement_type: SqlStatementType
    objects: List[SqlObject]
    affected_objects: List[SqlObject]
    dialect: Optional[str]
    schema: Optional[str]

    def __init__(
        self,
        sql_text: str,
        statement_type: Union[SqlStatementType, str],
        objects: Optional[List[SqlObject]] = None,
        affected_objects: Optional[List[SqlObject]] = None,
        dialect: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> None:
        """Initialize a SQL statement.

        Args:
            sql_text: Raw SQL text
            statement_type: Type of statement
            objects: SQL objects in the statement
            affected_objects: Objects affected by the statement
            dialect: SQL dialect used
            schema: Default schema
        """
        self.sql_text = sql_text

        # Handle both enum and string statement types
        if isinstance(statement_type, str):
            try:
                self.statement_type = SqlStatementType[statement_type.upper()]
            except KeyError:
                self.statement_type = SqlStatementType.UNKNOWN
        else:
            self.statement_type = statement_type

        self.objects = objects or []
        self.affected_objects = affected_objects or []
        self.dialect = dialect
        self.schema = schema

    def get_primary_object(self) -> Optional[SqlObject]:
        """Get the primary object in the statement.

        Returns:
            The primary object or None if no objects are found.
        """
        if self.objects:
            return self.objects[0]
        return None

    def __str__(self) -> str:
        """Return string representation of the statement."""
        return (
            f"{self.statement_type.value} statement affecting {len(self.affected_objects)} objects"
        )


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


@dataclass
class ParseResult:
    """Result of SQL parsing operation.

    This class provides comprehensive parsing results including:
    - Basic statements list (existing)
    - Rich SQL Model objects (tables, views, indexes, etc.)
    - Dependency information between objects
    - Enhanced metadata for validation and analysis
    """

    success: bool
    statements: Optional[List[SqlStatement]] = None
    errors: Optional[List[str]] = None

    # Enhanced: Rich SQL Model objects
    tables: Optional[List["Table"]] = None
    views: Optional[List["View"]] = None
    indexes: Optional[List["Index"]] = None
    sequences: Optional[List["Sequence"]] = None
    procedures: Optional[List["Procedure"]] = None
    triggers: Optional[List["Trigger"]] = None
    functions: Optional[List["Procedure"]] = None  # Functions are stored as procedures
    synonyms: Optional[List["Synonym"]] = None
    user_defined_types: Optional[List["UserDefinedType"]] = None
    packages: Optional[List["Package"]] = None
    events: Optional[List["Event"]] = None
    extensions: Optional[List["Extension"]] = None
    foreign_data_wrappers: Optional[List["ForeignDataWrapper"]] = None
    foreign_servers: Optional[List["ForeignServer"]] = None
    partitions: Optional[List["Partition"]] = None
    database_links: Optional[List["DatabaseLink"]] = None

    # Enhanced: Dependency tracking
    dependencies: Optional[Dict[str, List[str]]] = None

    def __init__(
        self,
        success: bool,
        statements: Optional[List[SqlStatement]] = None,
        errors: Optional[List[str]] = None,
    ):
        """Initialize a parse result.

        Args:
            success: Whether parsing was successful
            statements: Parsed statements (if successful)
            errors: Error messages (if unsuccessful)
        """
        self.success = success
        self.statements = statements or []
        self.errors = errors or []

        # Initialize rich SQL Model collections
        self.tables = []
        self.views = []
        self.indexes = []
        self.sequences = []
        self.procedures = []
        self.triggers = []
        self.functions = []
        self.synonyms = []
        self.user_defined_types = []
        self.packages = []
        self.events = []
        self.extensions = []
        self.foreign_data_wrappers = []
        self.foreign_servers = []
        self.database_links = []

        # Initialize dependency tracking
        self.dependencies = {}

    def __bool__(self) -> bool:
        """Return success status."""
        return self.success

    # Enhanced: Methods to add SQL Model objects

    def add_table(self, table: "Table") -> None:
        """Add a table to the parse result.

        Args:
            table: Table object to add
        """
        if self.tables is None:
            self.tables = []
        self.tables.append(table)

    def add_view(self, view: "View") -> None:
        """Add a view to the parse result.

        Args:
            view: View object to add
        """
        if self.views is None:
            self.views = []
        self.views.append(view)

    def add_index(self, index: "Index") -> None:
        """Add an index to the parse result.

        Args:
            index: Index object to add
        """
        if self.indexes is None:
            self.indexes = []
        self.indexes.append(index)

    def add_sequence(self, sequence: "Sequence") -> None:
        """Add a sequence to the parse result.

        Args:
            sequence: Sequence object to add
        """
        if self.sequences is None:
            self.sequences = []
        self.sequences.append(sequence)

    def add_procedure(self, procedure: "Procedure") -> None:
        """Add a procedure to the parse result.

        Args:
            procedure: Procedure object to add
        """
        if self.procedures is None:
            self.procedures = []
        self.procedures.append(procedure)

    def add_trigger(self, trigger: "Trigger") -> None:
        """Add a trigger to the parse result.

        Args:
            trigger: Trigger object to add
        """
        if self.triggers is None:
            self.triggers = []

        # Check for duplicates based on name and table
        for existing in self.triggers:
            if existing.name == trigger.name and existing.table_name == trigger.table_name:
                return  # Trigger already exists, don't add duplicate

        self.triggers.append(trigger)

    def add_function(self, function: "Procedure") -> None:
        """Add a function to the parse result.

        Args:
            function: Function object to add (stored as Procedure)
        """
        if self.functions is None:
            self.functions = []

        # Check for duplicates based on name and schema
        for existing in self.functions:
            if existing.name == function.name and existing.schema == function.schema:
                return  # Function already exists, don't add duplicate

        self.functions.append(function)

    def add_synonym(self, synonym: "Synonym") -> None:
        """Add a synonym to the parse result.

        Args:
            synonym: Synonym object to add
        """
        if self.synonyms is None:
            self.synonyms = []
        self.synonyms.append(synonym)

    def add_user_defined_type(self, user_type: "UserDefinedType") -> None:
        """Add a user-defined type to the parse result.

        Args:
            user_type: UserDefinedType object to add
        """
        if self.user_defined_types is None:
            self.user_defined_types = []
        self.user_defined_types.append(user_type)

    def add_package(self, package: "Package") -> None:
        """Add a package to the parse result.

        Args:
            package: Package object to add
        """
        if self.packages is None:
            self.packages = []
        self.packages.append(package)

    def add_event(self, event: "Event") -> None:
        """Add an event to the parse result.

        Args:
            event: Event object to add
        """
        if self.events is None:
            self.events = []
        self.events.append(event)

    def add_extension(self, extension: "Extension") -> None:
        """Add an extension to the parse result.

        Args:
            extension: Extension object to add
        """
        if self.extensions is None:
            self.extensions = []
        self.extensions.append(extension)

    def add_foreign_data_wrapper(self, fdw: "ForeignDataWrapper") -> None:
        """Add a foreign data wrapper to the parse result.

        Args:
            fdw: ForeignDataWrapper object to add
        """
        if self.foreign_data_wrappers is None:
            self.foreign_data_wrappers = []
        self.foreign_data_wrappers.append(fdw)

    def add_foreign_server(self, foreign_server: "ForeignServer") -> None:
        """Add a foreign server to the parse result.

        Args:
            foreign_server: ForeignServer object to add
        """
        if self.foreign_servers is None:
            self.foreign_servers = []
        self.foreign_servers.append(foreign_server)

    def add_database_link(self, database_link: "DatabaseLink") -> None:
        """Add a database link to the parse result.

        Args:
            database_link: DatabaseLink object to add
        """
        if self.database_links is None:
            self.database_links = []
        self.database_links.append(database_link)

    def add_partition(self, partition: "Partition") -> None:
        """Add a partition to the parse result.

        Args:
            partition: Partition object to add
        """
        if self.partitions is None:
            self.partitions = []
        self.partitions.append(partition)

    def add_dependency(self, obj_name: str, depends_on: str) -> None:
        """Add a dependency relationship between objects.

        Args:
            obj_name: Name of the dependent object
            depends_on: Name of the object it depends on
        """
        if self.dependencies is None:
            self.dependencies = {}

        if obj_name not in self.dependencies:
            self.dependencies[obj_name] = []

        if depends_on not in self.dependencies[obj_name]:
            self.dependencies[obj_name].append(depends_on)

    def get_table(self, name: str) -> Optional["Table"]:
        """Get a table by name (case-insensitive).

        Args:
            name: Table name to search for

        Returns:
            Table object if found, None otherwise
        """
        if not self.tables:
            return None

        name_lower = name.lower()
        for table in self.tables:
            if table.name.lower() == name_lower:
                return table
        return None

    def get_view(self, name: str) -> Optional["View"]:
        """Get a view by name (case-insensitive).

        Args:
            name: View name to search for

        Returns:
            View object if found, None otherwise
        """
        if not self.views:
            return None

        name_lower = name.lower()
        for view in self.views:
            if view.name.lower() == name_lower:
                return view
        return None

    def get_all_objects(self) -> List[SqlObject]:
        """Get all SQL objects from this parse result.

        Returns:
            Combined list of all SQL objects (tables, views, indexes, etc.)
        """
        objects: List[SqlObject] = []

        if self.tables:
            objects.extend(self.tables)
        if self.views:
            objects.extend(self.views)
        if self.indexes:
            objects.extend(self.indexes)
        if self.sequences:
            objects.extend(self.sequences)
        if self.procedures:
            objects.extend(self.procedures)
        if self.triggers:
            objects.extend(self.triggers)
        if self.functions:
            objects.extend(self.functions)
        if self.synonyms:
            objects.extend(self.synonyms)
        if self.user_defined_types:
            objects.extend(self.user_defined_types)
        if self.packages:
            objects.extend(self.packages)
        if self.events:
            objects.extend(self.events)
        if self.extensions:
            objects.extend(self.extensions)

        return objects

    def get_dependencies_for(self, obj_name: str) -> List[str]:
        """Get all objects that the specified object depends on.

        Args:
            obj_name: Name of the object

        Returns:
            List of object names that obj_name depends on
        """
        if not self.dependencies:
            return []

        return self.dependencies.get(obj_name, [])

    def has_circular_dependencies(self) -> bool:
        """Check if there are circular dependencies in the parsed SQL.

        Returns:
            True if circular dependencies exist, False otherwise
        """
        if not self.dependencies:
            return False

        # Use depth-first search to detect cycles
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            # Type guard for mypy
            deps = self.dependencies
            if deps is not None:
                for neighbor in deps.get(node, []):
                    if neighbor not in visited:
                        if has_cycle(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True

            rec_stack.remove(node)
            return False

        for node in self.dependencies.keys():
            if node not in visited:
                if has_cycle(node):
                    return True

        return False

    def get_summary(self) -> str:
        """Get a summary of the parse result.

        Returns:
            Human-readable summary string
        """
        summary_parts = []

        if self.statements:
            summary_parts.append(f"{len(self.statements)} statements")

        if self.tables:
            summary_parts.append(f"{len(self.tables)} tables")

        if self.views:
            summary_parts.append(f"{len(self.views)} views")

        if self.indexes:
            summary_parts.append(f"{len(self.indexes)} indexes")

        if self.sequences:
            summary_parts.append(f"{len(self.sequences)} sequences")

        if self.procedures:
            summary_parts.append(f"{len(self.procedures)} procedures")

        if self.triggers:
            summary_parts.append(f"{len(self.triggers)} triggers")

        if self.functions:
            summary_parts.append(f"{len(self.functions)} functions")

        if self.synonyms:
            summary_parts.append(f"{len(self.synonyms)} synonyms")

        if self.user_defined_types:
            summary_parts.append(f"{len(self.user_defined_types)} user-defined types")

        if self.packages:
            summary_parts.append(f"{len(self.packages)} packages")

        if self.events:
            summary_parts.append(f"{len(self.events)} events")

        if self.extensions:
            summary_parts.append(f"{len(self.extensions)} extensions")

        if self.dependencies:
            summary_parts.append(f"{len(self.dependencies)} dependencies")

        if self.errors:
            summary_parts.append(f"{len(self.errors)} errors")

        return ", ".join(summary_parts) if summary_parts else "Empty result"
