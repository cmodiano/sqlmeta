from typing import Any, Dict, List, Optional, Set

from sqlmeta.base import (
    ConstraintType,
    SqlColumn,
    SqlConstraint,
    SqlObject,
    SqlObjectType,
)


class Table(SqlObject):
    """Represents a database table."""

    def __init__(
        self,
        name: str,
        columns: List[SqlColumn] = None,
        schema: Optional[str] = None,
        constraints: List[SqlConstraint] = None,
        temporary: bool = False,
        tablespace: Optional[str] = None,
        dialect: Optional[str] = None,
        comment: Optional[str] = None,
        storage_engine: Optional[str] = None,
        partitions: Optional[List] = None,
        filegroup: Optional[str] = None,
        memory_optimized: bool = False,
        system_versioned: bool = False,
        history_table: Optional[str] = None,
        history_schema: Optional[str] = None,
        derived_from: Optional[str] = None,
    ):
        """Initialize a table.

        Args:
            name: Table name
            columns: List of columns
            schema: Schema name (optional)
            constraints: List of constraints
            temporary: Whether the table is temporary
            tablespace: Tablespace name (optional)
            dialect: SQL dialect
            comment: Table comment/description (optional)
            storage_engine: Storage engine (MySQL: InnoDB, MyISAM, etc.)
            partitions: List of Partition objects (optional)
            filegroup: Filegroup name (SQL Server T-SQL grammar-based)
            memory_optimized: Whether table is memory-optimized (SQL Server T-SQL grammar-based)
            system_versioned: Whether table is system-versioned temporal table (SQL Server T-SQL grammar-based)
            history_table: History table name for system-versioned tables (SQL Server T-SQL grammar-based)
            history_schema: History table schema for system-versioned tables (SQL Server T-SQL grammar-based)
            derived_from: Source for derived tables (e.g., "CTAS", "LIKE source_table", "SELECT")
        """
        super().__init__(name, SqlObjectType.TABLE, schema, dialect)
        self.columns = columns or []

        # Ensure columns inherit the dialect
        for col in self.columns:
            if not hasattr(col, "dialect") or not col.dialect:
                col.dialect = dialect

        self.constraints = constraints or []

        # Ensure constraints inherit the dialect
        for constraint in self.constraints:
            if not hasattr(constraint, "dialect") or not constraint.dialect:
                constraint.dialect = dialect

        self.temporary = temporary
        self.tablespace = tablespace
        self.comment = comment
        self.storage_engine = storage_engine
        self.partitions = partitions or []

        # T-SQL grammar-based: SQL Server-specific properties
        self.filegroup = filegroup
        self.memory_optimized = memory_optimized
        self.system_versioned = system_versioned
        self.history_table = history_table
        self.history_schema = history_schema

        # Derived table tracking (CTAS, LIKE, etc.)
        # Format: "CTAS" for AS SELECT, "LIKE:schema.table" for LIKE
        self.derived_from = derived_from

        # Partition scheme tracking (strategy only, not individual partitions)
        # partition_method: RANGE, LIST, HASH, KEY (MySQL), INTERVAL (Oracle auto-partitioning)
        # partition_columns: Column(s) used for partitioning (e.g., ["created_at"] or ["region", "year"])
        # Note: Individual partitions are NOT tracked to avoid drift from auto-created partitions
        self.partition_method: Optional[str] = None
        self.partition_columns: Optional[List[str]] = None

        self._column_map = {col.name.lower(): col for col in self.columns}

        # Track if tablespace was explicitly set
        if tablespace is not None:
            self.mark_property_explicit("tablespace")

        # Track if T-SQL-specific properties were explicitly set
        if filegroup is not None:
            self.mark_property_explicit("filegroup")
        if memory_optimized:
            self.mark_property_explicit("memory_optimized")
        if system_versioned:
            self.mark_property_explicit("system_versioned")
        if history_table is not None:
            self.mark_property_explicit("history_table")

    def add_column(self, column: SqlColumn) -> None:
        """Add a column to the table.

        Args:
            column: The column to add
        """
        # Inherit dialect if needed
        if not hasattr(column, "dialect") or not column.dialect:
            column.dialect = self.dialect

        self.columns.append(column)
        self._column_map[column.name.lower()] = column

    def get_column(self, name: str) -> Optional[SqlColumn]:
        """Get a column by name.

        Args:
            name: Column name

        Returns:
            The column or None if not found
        """
        return self._column_map.get(name.lower())

    def add_constraint(self, constraint: SqlConstraint) -> None:
        """Add a constraint to the table.

        Args:
            constraint: The constraint to add
        """
        # Inherit dialect if needed
        if not hasattr(constraint, "dialect") or not constraint.dialect:
            constraint.dialect = self.dialect

        self.constraints.append(constraint)

    def get_primary_key(self) -> Optional[SqlConstraint]:
        """Get the primary key constraint.

        Returns:
            The primary key constraint or None if not found
        """
        for constraint in self.constraints:
            if constraint.constraint_type.value == "PRIMARY KEY":
                return constraint
        return None

    def get_foreign_keys(self) -> List[SqlConstraint]:
        """Get all foreign key constraints.

        Returns:
            List of foreign key constraints
        """
        return [c for c in self.constraints if c.constraint_type.value == "FOREIGN KEY"]

    def get_unique_constraints(self) -> List[SqlConstraint]:
        """Get all unique constraints.

        Returns:
            List of unique constraints
        """
        return [c for c in self.constraints if c.constraint_type.value == "UNIQUE"]

    def get_check_constraints(self) -> List[SqlConstraint]:
        """Get all check constraints.

        Returns:
            List of check constraints
        """
        return [c for c in self.constraints if c.constraint_type.value == "CHECK"]

    @property
    def create_statement(self) -> str:
        """Generate CREATE TABLE statement.

        Returns:
            SQL CREATE TABLE statement for this table
        """
        # Format identifiers properly for the dialect
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        table_name = self.format_identifier(self.name)
        schema_prefix = f"{schema_name}." if schema_name else ""

        # Start the CREATE TABLE statement with dialect-specific temporary table syntax
        if self.temporary:
            if self.dialect == "oracle":
                stmt = f"CREATE GLOBAL TEMPORARY TABLE {schema_prefix}{table_name}"
            elif self.dialect == "sqlserver":
                # SQL Server uses # prefix for temporary tables
                # Format: #tablename (unquoted) or [#tablename] (quoted with # inside brackets)
                # NOT #[tablename] (invalid - # must be inside or outside brackets, not split)
                if self.name.startswith("#"):
                    # Already has # prefix, format the whole thing with brackets if needed
                    formatted_temp_name = self.format_identifier(self.name)
                else:
                    # Add # prefix outside any bracketing: #tablename
                    formatted_temp_name = f"#{self.name}"
                stmt = f"CREATE TABLE {schema_prefix}{formatted_temp_name}"
            else:
                # Default to standard TEMPORARY for other dialects
                stmt = f"CREATE TEMPORARY TABLE {schema_prefix}{table_name}"
        else:
            stmt = f"CREATE TABLE {schema_prefix}{table_name}"

        # Add columns
        if self.columns:
            column_definitions = []
            for col in self.columns:
                col_def = f"{self.format_identifier(col.name)} {col.data_type}"

                # Add nullable constraint
                if not col.nullable:
                    col_def += " NOT NULL"

                # Add default value
                if col.default_value is not None:
                    col_def += f" DEFAULT {col.default_value}"

                column_definitions.append(col_def)

            # Add constraints
            constraint_definitions = []
            for constraint in self.constraints:
                if constraint.constraint_type == ConstraintType.PRIMARY_KEY:
                    cols = ", ".join(self.format_identifier(col) for col in constraint.columns)
                    constraint_def = f"PRIMARY KEY ({cols})"
                    if constraint.name:
                        constraint_def = (
                            f"CONSTRAINT {self.format_identifier(constraint.name)} {constraint_def}"
                        )
                    constraint_definitions.append(constraint_def)

                elif constraint.constraint_type == ConstraintType.FOREIGN_KEY:
                    cols = ", ".join(self.format_identifier(col) for col in constraint.columns)
                    ref_cols = ", ".join(
                        self.format_identifier(col) for col in constraint.reference_columns
                    )
                    ref_table = constraint.reference_table
                    if constraint.reference_schema and ref_table:
                        ref_table = f"{self.format_identifier(constraint.reference_schema)}.{self.format_identifier(ref_table)}"
                    elif ref_table:
                        ref_table = self.format_identifier(ref_table)
                    else:
                        ref_table = "unknown_table"
                    constraint_def = f"FOREIGN KEY ({cols}) REFERENCES {ref_table} ({ref_cols})"
                    if constraint.name:
                        constraint_def = (
                            f"CONSTRAINT {self.format_identifier(constraint.name)} {constraint_def}"
                        )
                    constraint_definitions.append(constraint_def)

                elif constraint.constraint_type == ConstraintType.UNIQUE:
                    cols = ", ".join(self.format_identifier(col) for col in constraint.columns)
                    constraint_def = f"UNIQUE ({cols})"
                    if constraint.name:
                        constraint_def = (
                            f"CONSTRAINT {self.format_identifier(constraint.name)} {constraint_def}"
                        )
                    constraint_definitions.append(constraint_def)

                elif constraint.constraint_type == ConstraintType.CHECK:
                    # For check constraints, the columns list might contain the check expression
                    if constraint.columns:
                        check_expr = " ".join(constraint.columns)
                    else:
                        check_expr = "1=1"  # Default check expression
                    constraint_def = f"CHECK ({check_expr})"
                    if constraint.name:
                        constraint_def = (
                            f"CONSTRAINT {self.format_identifier(constraint.name)} {constraint_def}"
                        )
                    constraint_definitions.append(constraint_def)

            # Combine all definitions
            all_definitions = column_definitions + constraint_definitions
            definitions_text = ",\n    ".join(all_definitions)
            stmt += f" (\n    {definitions_text}\n)"
        else:
            stmt += " ()"

        # Add tablespace if specified (PostgreSQL, MySQL, etc.)
        if self.tablespace:
            stmt += f" TABLESPACE {self.tablespace}"

        # T-SQL grammar-based: Add filegroup if specified (SQL Server)
        if self.filegroup and self.dialect == "sqlserver":
            if self.filegroup.upper() == "PRIMARY":
                stmt += f" ON [PRIMARY]"
            else:
                stmt += f" ON {self.format_identifier(self.filegroup)}"

        # T-SQL grammar-based: Add memory-optimized table option (SQL Server)
        if self.memory_optimized and self.dialect == "sqlserver":
            stmt += " WITH (MEMORY_OPTIMIZED = ON)"

        # T-SQL grammar-based: Add system-versioned temporal table option (SQL Server)
        if self.system_versioned and self.dialect == "sqlserver":
            stmt += " WITH (SYSTEM_VERSIONING = ON"
            if self.history_table:
                history_schema = (
                    self.format_identifier(self.history_schema)
                    if self.history_schema
                    else (self.format_identifier(self.schema) if self.schema else "")
                )
                history_table = self.format_identifier(self.history_table)
                if history_schema:
                    stmt += f" (HISTORY_TABLE = {history_schema}.{history_table})"
                else:
                    stmt += f" (HISTORY_TABLE = {history_table})"
            stmt += ")"

        return stmt

    @property
    def drop_statement(self) -> str:
        """Generate DROP TABLE statement.

        Returns:
            SQL DROP TABLE statement for this table
        """
        schema_prefix = self.format_identifier(self.schema) + "." if self.schema else ""
        table_name = self.format_identifier(self.name)

        if self.dialect and self.dialect.lower() == "oracle":
            return f"DROP TABLE {schema_prefix}{table_name} CASCADE CONSTRAINTS"
        elif self.dialect and self.dialect.lower() == "mysql":
            return f"DROP TABLE IF EXISTS {schema_prefix}{table_name}"
        else:
            # PostgreSQL, SQL Server, DB2
            return f"DROP TABLE IF EXISTS {schema_prefix}{table_name} CASCADE"

    def __str__(self) -> str:
        """Return string representation of the table."""
        return self.create_statement

    def compare_with_defaults(
        self, other: "SqlObject", schema_defaults: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Compare two tables, taking into account schema defaults.

        This method extends the base class method to handle table-specific properties.

        Args:
            other: The other table to compare with
            schema_defaults: Dictionary of schema default values

        Returns:
            Dictionary of differences between the tables
        """
        # Get basic property differences from parent class
        differences = super().compare_with_defaults(other, schema_defaults)
        if "error" in differences:
            return differences

        schema_defaults = schema_defaults or {}

        # Only compare Table-specific properties if 'other' is a Table
        if not isinstance(other, Table):
            differences["error"] = "Cannot compare Table with non-Table object"
            return differences

        other_table = other

        # Compare tablespace only if explicitly set in one of the tables
        if self.is_property_explicit("tablespace") or (
            hasattr(other_table, "is_property_explicit")
            and other_table.is_property_explicit("tablespace")
        ):
            if self.tablespace != other_table.tablespace:
                differences["tablespace"] = {
                    "self": self.tablespace,
                    "other": other_table.tablespace,
                }

        # Compare temporary property
        if self.temporary != other_table.temporary:
            differences["temporary"] = {"self": self.temporary, "other": other_table.temporary}

        # T-SQL grammar-based: Compare filegroup (SQL Server)
        if self.dialect == "sqlserver" or other_table.dialect == "sqlserver":
            if self.is_property_explicit("filegroup") or (
                hasattr(other_table, "is_property_explicit")
                and other_table.is_property_explicit("filegroup")
            ):
                if self.filegroup != other_table.filegroup:
                    differences["filegroup"] = {
                        "self": self.filegroup,
                        "other": other_table.filegroup,
                    }

            # Compare memory-optimized property
            if self.is_property_explicit("memory_optimized") or (
                hasattr(other_table, "is_property_explicit")
                and other_table.is_property_explicit("memory_optimized")
            ):
                if self.memory_optimized != other_table.memory_optimized:
                    differences["memory_optimized"] = {
                        "self": self.memory_optimized,
                        "other": other_table.memory_optimized,
                    }

            # Compare system-versioned property
            if self.is_property_explicit("system_versioned") or (
                hasattr(other_table, "is_property_explicit")
                and other_table.is_property_explicit("system_versioned")
            ):
                if self.system_versioned != other_table.system_versioned:
                    differences["system_versioned"] = {
                        "self": self.system_versioned,
                        "other": other_table.system_versioned,
                    }
                # Also compare history table if system-versioned
                if self.system_versioned and other_table.system_versioned:
                    if self.history_table != other_table.history_table:
                        differences["history_table"] = {
                            "self": self.history_table,
                            "other": other_table.history_table,
                        }
                    if self.history_schema != other_table.history_schema:
                        differences["history_schema"] = {
                            "self": self.history_schema,
                            "other": other_table.history_schema,
                        }

        # Compare columns
        self_columns = {col.name.lower(): col for col in self.columns}
        other_columns = {col.name.lower(): col for col in other_table.columns}

        # Find columns only in self
        for name, col in self_columns.items():
            if name not in other_columns:
                if "columns_only_in_self" not in differences:
                    differences["columns_only_in_self"] = []
                differences["columns_only_in_self"].append(col.name)

        # Find columns only in other
        for name, col in other_columns.items():
            if name not in self_columns:
                if "columns_only_in_other" not in differences:
                    differences["columns_only_in_other"] = []
                differences["columns_only_in_other"].append(col.name)

        # Compare columns that exist in both
        column_differences: Dict[str, Dict[str, Any]] = {}
        for name, self_col in self_columns.items():
            if name in other_columns:
                other_col = other_columns[name]
                # Compare data types (required property)
                if self_col.data_type.lower() != other_col.data_type.lower():
                    if name not in column_differences:
                        column_differences[name] = {}
                    column_differences[name]["data_type"] = {
                        "self": self_col.data_type,
                        "other": other_col.data_type,
                    }

                # Compare nullable property if explicitly set in either column
                if (
                    hasattr(self_col, "is_property_explicit")
                    and self_col.is_property_explicit("nullable")
                    or hasattr(other_col, "is_property_explicit")
                    and other_col.is_property_explicit("nullable")
                ):
                    if self_col.nullable != other_col.nullable:
                        if name not in column_differences:
                            column_differences[name] = {}
                        column_differences[name]["nullable"] = {
                            "self": self_col.nullable,
                            "other": other_col.nullable,
                        }

                # Compare default value if explicitly set in either column
                if (
                    hasattr(self_col, "is_property_explicit")
                    and self_col.is_property_explicit("default_value")
                    or hasattr(other_col, "is_property_explicit")
                    and other_col.is_property_explicit("default_value")
                ):
                    if self_col.default_value != other_col.default_value:
                        if name not in column_differences:
                            column_differences[name] = {}
                        column_differences[name]["default_value"] = {
                            "self": self_col.default_value,
                            "other": other_col.default_value,
                        }

        if column_differences:
            differences["column_differences"] = column_differences

        # TODO: Add constraint comparison logic here

        return differences

    def to_dict(self) -> Dict[str, Any]:
        """Convert table to dictionary representation.

        Returns:
            Dictionary with table attributes
        """
        return {
            "name": self.name,
            "schema": self.schema,
            "object_type": self.object_type.value,
            "dialect": self.dialect,
            "columns": [
                {
                    "name": col.name,
                    "data_type": col.data_type,
                    "nullable": col.nullable,
                    "default_value": col.default_value,
                    "is_identity": getattr(col, "is_identity", False),
                    "identity_generation": getattr(col, "identity_generation", None),
                    "identity_seed": getattr(col, "identity_seed", None),
                    "identity_increment": getattr(col, "identity_increment", None),
                    "is_computed": getattr(col, "is_computed", False),
                    "computed_expression": getattr(col, "computed_expression", None),
                    "computed_stored": getattr(col, "computed_stored", False),
                    "comment": getattr(col, "comment", None),
                    "ordinal_position": getattr(col, "ordinal_position", None),
                    "explicit_properties": getattr(col, "explicit_properties", {}),
                }
                for col in self.columns
            ],
            "constraints": [
                {
                    "name": c.name,
                    "constraint_type": c.constraint_type,
                    "columns": c.columns,
                    "reference_table": c.reference_table,
                    "reference_schema": c.reference_schema,
                    "reference_columns": c.reference_columns,
                    "explicit_properties": getattr(c, "explicit_properties", {}),
                }
                for c in self.constraints
            ],
            "temporary": self.temporary,
            "tablespace": self.tablespace,
            "comment": self.comment,
            "storage_engine": self.storage_engine,
            "filegroup": self.filegroup,
            "memory_optimized": self.memory_optimized,
            "system_versioned": self.system_versioned,
            "history_table": self.history_table,
            "history_schema": self.history_schema,
            "explicit_properties": self.explicit_properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Table":
        """Create table from dictionary representation.

        Args:
            data: Dictionary with table attributes

        Returns:
            Table object
        """
        dialect = data.get("dialect")

        # Create columns
        columns = []
        for col_data in data.get("columns", []):
            col = SqlColumn(
                name=col_data["name"],
                data_type=col_data["data_type"],
                is_nullable=col_data.get("nullable", True),
                default_value=col_data.get("default_value"),
                is_identity=col_data.get("is_identity", False),
                identity_generation=col_data.get("identity_generation"),
                identity_seed=col_data.get("identity_seed"),
                identity_increment=col_data.get("identity_increment"),
                is_computed=col_data.get("is_computed", False),
                computed_expression=col_data.get("computed_expression"),
                computed_stored=col_data.get("computed_stored", False),
                comment=col_data.get("comment"),
                ordinal_position=col_data.get("ordinal_position"),
                dialect=dialect,
            )
            # Restore explicit properties
            if col_data.get("explicit_properties"):
                for prop, is_explicit in col_data["explicit_properties"].items():
                    if is_explicit:
                        col.mark_property_explicit(prop)
            columns.append(col)

        # Create constraints
        constraints = []
        for c_data in data.get("constraints", []):
            constraint = SqlConstraint(
                name=c_data.get("name"),
                constraint_type=c_data["constraint_type"],
                column_names=c_data["columns"],
                reference_table=c_data.get("reference_table"),
                reference_columns=c_data.get("reference_columns"),
                dialect=dialect,
            )
            # Restore explicit properties
            if c_data.get("explicit_properties"):
                for prop, is_explicit in c_data["explicit_properties"].items():
                    if is_explicit:
                        constraint.mark_property_explicit(prop)
            constraints.append(constraint)

        table = cls(
            name=data["name"],
            schema=data.get("schema"),
            columns=columns,
            constraints=constraints,
            temporary=data.get("temporary", False),
            tablespace=data.get("tablespace"),
            comment=data.get("comment"),
            storage_engine=data.get("storage_engine"),
            filegroup=data.get("filegroup"),
            memory_optimized=data.get("memory_optimized", False),
            system_versioned=data.get("system_versioned", False),
            history_table=data.get("history_table"),
            history_schema=data.get("history_schema"),
            dialect=dialect,
        )

        # Restore explicit properties
        if data.get("explicit_properties"):
            for prop, is_explicit in data["explicit_properties"].items():
                if is_explicit:
                    table.mark_property_explicit(prop)

        return table

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Table):
            return False
        return (
            self.name == other.name
            and self.schema == other.schema
            and self.temporary == other.temporary
            and self.tablespace == other.tablespace
            and self.dialect == other.dialect
            and self.columns == other.columns
            and self.constraints == other.constraints
            and self.filegroup == other.filegroup
            and self.memory_optimized == other.memory_optimized
            and self.system_versioned == other.system_versioned
            and self.history_table == other.history_table
            and self.history_schema == other.history_schema
        )
