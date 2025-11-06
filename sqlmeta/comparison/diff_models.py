"""Diff Models for SQL Object Comparison Results.

This module defines structured classes to represent differences between
SQL Model objects, enabling precise tracking of schema drift.

Key Classes:
- DiffResult: Base class for all diff results
- TableDiff: Table-level differences
- ColumnDiff: Column-level differences
- ConstraintDiff: Constraint differences
- SchemaDiff: Schema-level summary
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DiffSeverity(Enum):
    """Severity levels for differences."""

    ERROR = "error"  # Breaking changes (column removed, type incompatible)
    WARNING = "warning"  # Non-breaking but important (nullable changed)
    INFO = "info"  # Cosmetic differences (comments, formatting)


@dataclass
class DiffResult:
    """Base class for comparison results.

    Attributes:
        object_name: Name of the object being compared
        object_type: Type of object (table, view, procedure, etc.)
        severity: Highest severity of differences found
        has_diffs: Whether any differences were found
    """

    object_name: str
    object_type: str = ""
    severity: DiffSeverity = DiffSeverity.INFO
    has_diffs: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the diff result
        """
        return {
            "object_name": self.object_name,
            "object_type": self.object_type,
            "severity": self.severity.value,
            "has_diffs": self.has_diffs,
        }

    def __str__(self) -> str:
        """Human-readable string representation.

        Returns:
            Formatted string describing the diff
        """
        if not self.has_diffs:
            return f"{self.object_type} '{self.object_name}': No differences"

        return f"{self.object_type} '{self.object_name}': {self.severity.value.upper()} - Differences found"

    def get_summary(self) -> str:
        """Get a brief summary of differences.

        Returns:
            Brief summary string
        """
        status = "MATCH" if not self.has_diffs else f"DIFF ({self.severity.value})"
        return f"{self.object_type} '{self.object_name}': {status}"


@dataclass
class ColumnDiff(DiffResult):
    """Represents differences in a column definition.

    Attributes:
        column_name: Name of the column
        data_type_diff: Data type differences (expected vs actual)
        nullable_diff: Nullability differences
        default_diff: Default value differences
        identity_diff: Identity column differences
        computed_diff: Computed column differences
    """

    column_name: str = ""
    data_type_diff: Optional[tuple] = None  # (expected, actual)
    nullable_diff: Optional[tuple] = None  # (expected, actual)
    default_diff: Optional[tuple] = None  # (expected, actual)
    identity_diff: Optional[tuple] = None  # (expected, actual)
    computed_diff: Optional[tuple] = None  # (expected, actual)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.column_name:
            self.column_name = self.object_name

        self.object_type = "column"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        diffs = []

        if self.data_type_diff:
            diffs.append(("data_type", DiffSeverity.ERROR))
        if self.nullable_diff:
            diffs.append(("nullable", DiffSeverity.WARNING))
        if self.default_diff:
            diffs.append(("default", DiffSeverity.WARNING))
        if self.identity_diff:
            diffs.append(("identity", DiffSeverity.ERROR))
        if self.computed_diff:
            diffs.append(("computed", DiffSeverity.WARNING))

        self.has_diffs = len(diffs) > 0

        if diffs:
            # Set severity to highest level
            severities = [sev for _, sev in diffs]
            if DiffSeverity.ERROR in severities:
                self.severity = DiffSeverity.ERROR
            elif DiffSeverity.WARNING in severities:
                self.severity = DiffSeverity.WARNING
            else:
                self.severity = DiffSeverity.INFO

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update(
            {
                "column_name": self.column_name,
                "differences": {},
            }
        )

        if self.data_type_diff:
            result["differences"]["data_type"] = {
                "expected": self.data_type_diff[0],
                "actual": self.data_type_diff[1],
            }
        if self.nullable_diff:
            result["differences"]["nullable"] = {
                "expected": self.nullable_diff[0],
                "actual": self.nullable_diff[1],
            }
        if self.default_diff:
            result["differences"]["default"] = {
                "expected": self.default_diff[0],
                "actual": self.default_diff[1],
            }
        if self.identity_diff:
            result["differences"]["identity"] = {
                "expected": self.identity_diff[0],
                "actual": self.identity_diff[1],
            }
        if self.computed_diff:
            result["differences"]["computed"] = {
                "expected": self.computed_diff[0],
                "actual": self.computed_diff[1],
            }

        return result

    def __str__(self) -> str:
        """Human-readable string representation."""
        if not self.has_diffs:
            return f"Column '{self.column_name}': No differences"

        diff_parts = []
        if self.data_type_diff:
            diff_parts.append(f"type: {self.data_type_diff[0]} → {self.data_type_diff[1]}")
        if self.nullable_diff:
            diff_parts.append(f"nullable: {self.nullable_diff[0]} → {self.nullable_diff[1]}")
        if self.default_diff:
            diff_parts.append(f"default: {self.default_diff[0]} → {self.default_diff[1]}")
        if self.identity_diff:
            diff_parts.append(f"identity: {self.identity_diff[0]} → {self.identity_diff[1]}")
        if self.computed_diff:
            diff_parts.append(f"computed: {self.computed_diff[0]} → {self.computed_diff[1]}")

        return f"Column '{self.column_name}' [{self.severity.value}]: {', '.join(diff_parts)}"


@dataclass
class ConstraintDiff(DiffResult):
    """Represents differences in a constraint definition.

    Attributes:
        constraint_name: Name of the constraint
        constraint_type: Type of constraint (PK, FK, UNIQUE, CHECK)
        columns_diff: Differences in constrained columns
        references_diff: Differences in foreign key references
        check_clause_diff: Differences in CHECK constraint expressions
    """

    constraint_name: str = ""
    constraint_type: str = ""
    columns_diff: Optional[tuple] = None  # (expected, actual)
    references_diff: Optional[tuple] = None  # (expected, actual)
    check_clause_diff: Optional[tuple] = None  # (expected, actual)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.constraint_name:
            self.constraint_name = self.object_name

        self.object_type = "constraint"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = any([self.columns_diff, self.references_diff, self.check_clause_diff])

        if self.has_diffs:
            # Constraint differences are typically errors
            self.severity = DiffSeverity.ERROR

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update(
            {
                "constraint_name": self.constraint_name,
                "constraint_type": self.constraint_type,
                "differences": {},
            }
        )

        if self.columns_diff:
            result["differences"]["columns"] = {
                "expected": self.columns_diff[0],
                "actual": self.columns_diff[1],
            }
        if self.references_diff:
            result["differences"]["references"] = {
                "expected": self.references_diff[0],
                "actual": self.references_diff[1],
            }
        if self.check_clause_diff:
            result["differences"]["check_clause"] = {
                "expected": self.check_clause_diff[0],
                "actual": self.check_clause_diff[1],
            }

        return result

    def __str__(self) -> str:
        """Human-readable string representation."""
        if not self.has_diffs:
            return f"Constraint '{self.constraint_name}' ({self.constraint_type}): No differences"

        diff_parts = []
        if self.columns_diff:
            diff_parts.append(f"columns: {self.columns_diff[0]} → {self.columns_diff[1]}")
        if self.references_diff:
            diff_parts.append(f"references: {self.references_diff[0]} → {self.references_diff[1]}")
        if self.check_clause_diff:
            diff_parts.append("check clause differs")

        return f"Constraint '{self.constraint_name}' ({self.constraint_type}) [{self.severity.value}]: {', '.join(diff_parts)}"


@dataclass
class TableDiff(DiffResult):
    """Represents differences in a table definition.

    Attributes:
        table_name: Name of the table
        missing_columns: Columns in expected but not in actual
        extra_columns: Columns in actual but not in expected
        modified_columns: Columns with differences
        missing_constraints: Constraints in expected but not in actual
        extra_constraints: Constraints in actual but not in expected
        modified_constraints: Constraints with differences
        missing_indexes: Indexes in expected but not in actual
        extra_indexes: Indexes in actual but not in expected
        temporary_changed: Whether temporary property changed (grammar-based enhancement)
        filegroup_changed: Whether filegroup changed (T-SQL grammar-based)
        memory_optimized_changed: Whether memory-optimized property changed (T-SQL grammar-based)
        system_versioned_changed: Whether system-versioned property changed (T-SQL grammar-based)
        history_table_changed: Whether history table changed (T-SQL grammar-based)
        partition_method_changed: Whether partition method changed (partition scheme tracking)
        partition_columns_changed: Whether partition columns changed (partition scheme tracking)
        compress_changed: Whether compress property changed (DB2 grammar-based)
        compress_type_changed: Whether compress type changed (DB2 grammar-based)
        logged_changed: Whether logged property changed (DB2 grammar-based)
        organize_by_changed: Whether organize_by property changed (DB2 grammar-based)
    """

    table_name: str = ""
    missing_columns: List[str] = field(default_factory=list)
    extra_columns: List[str] = field(default_factory=list)
    modified_columns: List[ColumnDiff] = field(default_factory=list)
    missing_constraints: List[str] = field(default_factory=list)
    extra_constraints: List[str] = field(default_factory=list)
    modified_constraints: List[ConstraintDiff] = field(default_factory=list)
    missing_indexes: List[str] = field(default_factory=list)
    extra_indexes: List[str] = field(default_factory=list)
    temporary_changed: bool = False
    filegroup_changed: bool = False
    memory_optimized_changed: bool = False
    system_versioned_changed: bool = False
    history_table_changed: bool = False
    partition_method_changed: bool = False
    partition_columns_changed: bool = False
    compress_changed: bool = False
    compress_type_changed: bool = False
    logged_changed: bool = False
    organize_by_changed: bool = False

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.table_name:
            self.table_name = self.object_name

        self.object_type = "table"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        # Check if any differences exist
        # Grammar-based: Added temporary_changed to track temporary property differences
        # T-SQL grammar-based: Added filegroup, memory_optimized, system_versioned, history_table tracking
        # Partition tracking: Added partition_method_changed, partition_columns_changed
        # DB2 grammar-based: Added compress, compress_type, logged, organize_by tracking
        self.has_diffs = any(
            [
                self.missing_columns,
                self.extra_columns,
                self.modified_columns,
                self.missing_constraints,
                self.extra_constraints,
                self.modified_constraints,
                self.missing_indexes,
                self.extra_indexes,
                self.temporary_changed,
                self.filegroup_changed,
                self.memory_optimized_changed,
                self.system_versioned_changed,
                self.history_table_changed,
                self.partition_method_changed,
                self.partition_columns_changed,
                self.compress_changed,
                self.compress_type_changed,
                self.logged_changed,
                self.organize_by_changed,
            ]
        )

        if not self.has_diffs:
            return

        # Calculate severity based on type of differences
        if self.missing_columns or self.missing_constraints:
            # Missing columns/constraints are errors
            self.severity = DiffSeverity.ERROR
        elif self.modified_columns:
            # Check modified column severities
            for col_diff in self.modified_columns:
                if col_diff.severity == DiffSeverity.ERROR:
                    self.severity = DiffSeverity.ERROR
                    return
            self.severity = DiffSeverity.WARNING
        elif self.extra_columns or self.extra_constraints:
            # Extra columns/constraints are warnings
            self.severity = DiffSeverity.WARNING
        else:
            # Index differences are info
            self.severity = DiffSeverity.INFO

    def get_diff_count(self) -> Dict[str, int]:
        """Get count of each type of difference.

        Returns:
            Dictionary with counts of different types
        """
        return {
            "missing_columns": len(self.missing_columns),
            "extra_columns": len(self.extra_columns),
            "modified_columns": len(self.modified_columns),
            "missing_constraints": len(self.missing_constraints),
            "extra_constraints": len(self.extra_constraints),
            "modified_constraints": len(self.modified_constraints),
            "missing_indexes": len(self.missing_indexes),
            "extra_indexes": len(self.extra_indexes),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update(
            {
                "table_name": self.table_name,
                "missing_columns": self.missing_columns,
                "extra_columns": self.extra_columns,
                "modified_columns": [col.to_dict() for col in self.modified_columns],
                "missing_constraints": self.missing_constraints,
                "extra_constraints": self.extra_constraints,
                "modified_constraints": [const.to_dict() for const in self.modified_constraints],
                "missing_indexes": self.missing_indexes,
                "extra_indexes": self.extra_indexes,
                "temporary_changed": self.temporary_changed,
                "filegroup_changed": self.filegroup_changed,
                "memory_optimized_changed": self.memory_optimized_changed,
                "system_versioned_changed": self.system_versioned_changed,
                "history_table_changed": self.history_table_changed,
                "diff_count": self.get_diff_count(),
            }
        )
        return result

    def __str__(self) -> str:
        """Human-readable string representation."""
        if not self.has_diffs:
            return f"Table '{self.table_name}': No differences"

        parts = []
        counts = self.get_diff_count()

        if counts["missing_columns"]:
            parts.append(f"{counts['missing_columns']} missing column(s)")
        if counts["extra_columns"]:
            parts.append(f"{counts['extra_columns']} extra column(s)")
        if counts["modified_columns"]:
            parts.append(f"{counts['modified_columns']} modified column(s)")
        if counts["missing_constraints"]:
            parts.append(f"{counts['missing_constraints']} missing constraint(s)")
        if counts["extra_constraints"]:
            parts.append(f"{counts['extra_constraints']} extra constraint(s)")
        if counts["modified_constraints"]:
            parts.append(f"{counts['modified_constraints']} modified constraint(s)")
        if counts["missing_indexes"]:
            parts.append(f"{counts['missing_indexes']} missing index(es)")
        if counts["extra_indexes"]:
            parts.append(f"{counts['extra_indexes']} extra index(es)")
        if self.temporary_changed:
            parts.append("temporary property changed")
        if self.filegroup_changed:
            parts.append("filegroup changed")
        if self.memory_optimized_changed:
            parts.append("memory-optimized property changed")
        if self.system_versioned_changed:
            parts.append("system-versioned property changed")
        if self.history_table_changed:
            parts.append("history table changed")

        return f"Table '{self.table_name}' [{self.severity.value}]: {', '.join(parts)}"


@dataclass
class ViewDiff(DiffResult):
    """Represents differences in a view definition.

    Attributes:
        view_name: Name of the view
        definition_changed: Whether the view definition changed
        expected_definition: Expected view definition SQL
        actual_definition: Actual view definition SQL
        materialized_changed: Whether materialized status changed (PostgreSQL)
        unlogged_changed: Whether UNLOGGED status changed (PostgreSQL materialized views, grammar-based)
        algorithm_changed: Whether algorithm changed (MySQL grammar-based: MERGE, TEMPTABLE, UNDEFINED)
        sql_security_changed: Whether SQL SECURITY changed (MySQL grammar-based: DEFINER, INVOKER)
        definer_changed: Whether definer changed (MySQL grammar-based: user@host)
        force_changed: Whether FORCE/NOFORCE changed (Oracle grammar-based)
        is_populated_changed: Whether populated status changed (materialized views)
        refresh_method_changed: Whether refresh method changed (Oracle, DB2)
        refresh_mode_changed: Whether refresh mode changed (Oracle)
        fast_refreshable_changed: Whether fast refresh capability changed (Oracle)
    """

    view_name: str = ""
    definition_changed: bool = False
    expected_definition: Optional[str] = None
    actual_definition: Optional[str] = None
    materialized_changed: Optional[tuple] = None  # (expected, actual)
    unlogged_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: PostgreSQL UNLOGGED materialized views
    )
    algorithm_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: MySQL view algorithm
    )
    sql_security_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: MySQL SQL SECURITY
    )
    definer_changed: Optional[tuple] = None  # (expected, actual) - Grammar-based: MySQL definer
    force_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: Oracle FORCE/NOFORCE
    )
    is_populated_changed: Optional[tuple] = None  # (expected, actual)
    refresh_method_changed: Optional[tuple] = None  # (expected, actual)
    refresh_mode_changed: Optional[tuple] = None  # (expected, actual)
    fast_refreshable_changed: Optional[tuple] = None  # (expected, actual)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.view_name:
            self.view_name = self.object_name

        self.object_type = "view"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = any(
            [
                self.definition_changed,
                self.materialized_changed is not None,
                self.unlogged_changed is not None,  # Grammar-based: Track UNLOGGED status changes
                self.algorithm_changed is not None,  # Grammar-based: Track MySQL algorithm changes
                self.sql_security_changed
                is not None,  # Grammar-based: Track MySQL SQL SECURITY changes
                self.definer_changed is not None,  # Grammar-based: Track MySQL definer changes
                self.force_changed is not None,  # Grammar-based: Track Oracle FORCE/NOFORCE changes
                self.is_populated_changed is not None,
                self.refresh_method_changed is not None,
                self.refresh_mode_changed is not None,
                self.fast_refreshable_changed is not None,
            ]
        )

        if self.has_diffs:
            # View definition changes are warnings (can be reapplied)
            self.severity = DiffSeverity.WARNING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update(
            {
                "view_name": self.view_name,
                "definition_changed": self.definition_changed,
                "expected_definition": self.expected_definition,
                "actual_definition": self.actual_definition,
                "materialized_changed": self.materialized_changed,
                "unlogged_changed": self.unlogged_changed,  # Grammar-based: UNLOGGED status
                "algorithm_changed": self.algorithm_changed,  # Grammar-based: MySQL algorithm
                "sql_security_changed": self.sql_security_changed,  # Grammar-based: MySQL SQL SECURITY
                "definer_changed": self.definer_changed,  # Grammar-based: MySQL definer
                "force_changed": self.force_changed,  # Grammar-based: Oracle FORCE/NOFORCE
                "is_populated_changed": self.is_populated_changed,
                "refresh_method_changed": self.refresh_method_changed,
                "refresh_mode_changed": self.refresh_mode_changed,
                "fast_refreshable_changed": self.fast_refreshable_changed,
            }
        )
        return result


@dataclass
class IndexDiff(DiffResult):
    """Represents differences in an index definition.

    Attributes:
        index_name: Name of the index
        table_name: Table the index belongs to
        columns_changed: Whether indexed columns changed
        uniqueness_changed: Whether uniqueness constraint changed
        type_changed: Whether index type changed (btree, hash, fulltext, spatial, etc.)
        online_changed: Whether ONLINE/OFFLINE status changed (MySQL grammar-based)
        concurrently_changed: Whether CONCURRENTLY status changed (PostgreSQL grammar-based)
        tablespace_changed: Whether TABLESPACE changed (Oracle grammar-based)
        expected_columns: Expected indexed columns
        actual_columns: Actual indexed columns
    """

    index_name: str = ""
    table_name: str = ""
    columns_changed: bool = False
    uniqueness_changed: Optional[tuple] = None  # (expected, actual)
    type_changed: Optional[tuple] = (
        None  # (expected, actual) - Supports FULLTEXT, SPATIAL (MySQL grammar-based)
    )
    online_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: MySQL ONLINE/OFFLINE
    )
    concurrently_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: PostgreSQL CONCURRENTLY
    )
    tablespace_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: Oracle TABLESPACE
    )
    expected_columns: Optional[List[str]] = None
    actual_columns: Optional[List[str]] = None

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.index_name:
            self.index_name = self.object_name

        self.object_type = "index"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = (
            self.columns_changed
            or self.uniqueness_changed is not None
            or self.type_changed is not None
            or self.online_changed is not None  # Grammar-based: Track MySQL ONLINE/OFFLINE changes
            or self.concurrently_changed
            is not None  # Grammar-based: Track PostgreSQL CONCURRENTLY changes
            or self.tablespace_changed is not None  # Grammar-based: Track Oracle TABLESPACE changes
        )

        if self.has_diffs:
            # Index changes are warnings (can be recreated)
            self.severity = DiffSeverity.WARNING


@dataclass
class SequenceDiff(DiffResult):
    """Represents differences in a sequence definition.

    Attributes:
        sequence_name: Name of the sequence
        start_value_changed: Whether start value changed
        increment_changed: Whether increment changed
        min_value_changed: Whether minimum value changed
        max_value_changed: Whether maximum value changed
        cycle_changed: Whether cycle option changed
        temp_changed: Whether TEMPORARY status changed (PostgreSQL grammar-based)
    """

    sequence_name: str = ""
    start_value_changed: Optional[tuple] = None  # (expected, actual)
    increment_changed: Optional[tuple] = None  # (expected, actual)
    min_value_changed: Optional[tuple] = None  # (expected, actual)
    max_value_changed: Optional[tuple] = None  # (expected, actual)
    cycle_changed: Optional[tuple] = None  # (expected, actual)
    temp_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: PostgreSQL TEMPORARY sequences
    )

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.sequence_name:
            self.sequence_name = self.object_name

        self.object_type = "sequence"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = any(
            [
                self.start_value_changed,
                self.increment_changed,
                self.min_value_changed,
                self.max_value_changed,
                self.cycle_changed,
                self.temp_changed,  # Grammar-based: Track PostgreSQL TEMPORARY sequence changes
            ]
        )

        if self.has_diffs:
            # Sequence changes are info (current value can differ)
            self.severity = DiffSeverity.INFO


@dataclass
class TriggerDiff(DiffResult):
    """Represents differences in a trigger definition.

    Attributes:
        trigger_name: Name of the trigger
        table_name: Table the trigger is attached to
        timing_changed: Whether timing changed (BEFORE/AFTER/INSTEAD OF, grammar-based)
        event_changed: Whether event changed (INSERT/UPDATE/DELETE/TRUNCATE, grammar-based)
        constraint_trigger_changed: Whether constraint trigger status changed (PostgreSQL, grammar-based)
        definer_changed: Whether definer changed (MySQL grammar-based: user@host)
        definition_changed: Whether trigger body changed
        enabled_changed: Whether enabled status changed
    """

    trigger_name: str = ""
    table_name: str = ""
    timing_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: Supports INSTEAD OF
    )
    event_changed: Optional[tuple] = None  # (expected, actual) - Grammar-based: Supports TRUNCATE
    constraint_trigger_changed: Optional[tuple] = (
        None  # (expected, actual) - Grammar-based: CONSTRAINT TRIGGER
    )
    definer_changed: Optional[tuple] = None  # (expected, actual) - Grammar-based: MySQL definer
    definition_changed: bool = False
    enabled_changed: Optional[tuple] = None  # (expected, actual)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.trigger_name:
            self.trigger_name = self.object_name

        self.object_type = "trigger"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = (
            self.timing_changed is not None
            or self.event_changed is not None
            or self.constraint_trigger_changed
            is not None  # Grammar-based: Track constraint trigger changes
            or self.definer_changed is not None  # Grammar-based: Track MySQL definer changes
            or self.definition_changed
            or self.enabled_changed is not None
        )

        if self.has_diffs:
            # Trigger changes are warnings (can affect data integrity)
            self.severity = DiffSeverity.WARNING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update(
            {
                "trigger_name": self.trigger_name,
                "table_name": self.table_name,
                "timing_changed": self.timing_changed,
                "event_changed": self.event_changed,
                "constraint_trigger_changed": self.constraint_trigger_changed,  # Grammar-based: CONSTRAINT TRIGGER
                "definer_changed": self.definer_changed,  # Grammar-based: MySQL definer
                "definition_changed": self.definition_changed,
                "enabled_changed": self.enabled_changed,
            }
        )
        return result


@dataclass
class ProcedureDiff(DiffResult):
    """Represents differences in a stored procedure definition.

    Attributes:
        procedure_name: Name of the procedure
        definition_changed: Whether procedure body changed
        parameters_changed: Whether parameters changed
        expected_parameters: Expected parameter list
        actual_parameters: Actual parameter list
    """

    procedure_name: str = ""
    definition_changed: bool = False
    parameters_changed: bool = False
    expected_parameters: Optional[List[str]] = None
    actual_parameters: Optional[List[str]] = None

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.procedure_name:
            self.procedure_name = self.object_name

        self.object_type = "procedure"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = self.definition_changed or self.parameters_changed

        if self.has_diffs:
            if self.parameters_changed:
                # Parameter changes are errors (breaking change)
                self.severity = DiffSeverity.ERROR
            else:
                # Body changes are warnings (can be reapplied)
                self.severity = DiffSeverity.WARNING


@dataclass
class FunctionDiff(DiffResult):
    """Represents differences in a function definition.

    Attributes:
        function_name: Name of the function
        definition_changed: Whether function body changed
        parameters_changed: Whether parameters changed
        return_type_changed: Whether return type changed
        expected_parameters: Expected parameter list
        actual_parameters: Actual parameter list
    """

    function_name: str = ""
    definition_changed: bool = False
    parameters_changed: bool = False
    return_type_changed: Optional[tuple] = None  # (expected, actual)
    expected_parameters: Optional[List[str]] = None
    actual_parameters: Optional[List[str]] = None

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.function_name:
            self.function_name = self.object_name

        self.object_type = "function"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = (
            self.definition_changed
            or self.parameters_changed
            or self.return_type_changed is not None
        )

        if self.has_diffs:
            if self.parameters_changed or self.return_type_changed:
                # Parameter/return type changes are errors (breaking change)
                self.severity = DiffSeverity.ERROR
            else:
                # Body changes are warnings (can be reapplied)
                self.severity = DiffSeverity.WARNING


@dataclass
class SynonymDiff(DiffResult):
    """Represents differences in a synonym definition.

    Attributes:
        synonym_name: Name of the synonym
        target_changed: Whether the target object changed
        target_schema_changed: Whether the target schema changed
        target_database_changed: Whether the target database changed (SQL Server)
        db_link_changed: Whether the database link changed (Oracle)
        expected_target: Expected target object
        actual_target: Actual target object
    """

    synonym_name: str = ""
    target_changed: Optional[tuple] = None  # (expected, actual)
    target_schema_changed: Optional[tuple] = None  # (expected, actual)
    target_database_changed: Optional[tuple] = None  # (expected, actual)
    db_link_changed: Optional[tuple] = None  # (expected, actual)
    expected_target: Optional[str] = None
    actual_target: Optional[str] = None

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.synonym_name:
            self.synonym_name = self.object_name

        self.object_type = "synonym"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = any(
            [
                self.target_changed,
                self.target_schema_changed,
                self.target_database_changed,
                self.db_link_changed,
            ]
        )

        if self.has_diffs:
            # Synonym target changes are warnings (synonym can be recreated)
            self.severity = DiffSeverity.WARNING


@dataclass
class PackageDiff(DiffResult):
    """Represents differences in a package definition (Oracle).

    Attributes:
        package_name: Name of the package
        spec_changed: Whether package specification changed
        body_changed: Whether package body changed
        expected_spec: Expected package specification
        actual_spec: Actual package specification
        expected_body: Expected package body
        actual_body: Actual package body
    """

    package_name: str = ""
    spec_changed: bool = False
    body_changed: bool = False
    expected_spec: Optional[str] = None
    actual_spec: Optional[str] = None
    expected_body: Optional[str] = None
    actual_body: Optional[str] = None

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.package_name:
            self.package_name = self.object_name

        self.object_type = "package"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = self.spec_changed or self.body_changed

        if self.has_diffs:
            # Package changes are warnings (can be reapplied with CREATE OR REPLACE)
            self.severity = DiffSeverity.WARNING


@dataclass
class DatabaseLinkDiff(DiffResult):
    """Represents differences in a database link definition (Oracle).

    Attributes:
        link_name: Name of the database link
        host_changed: Whether the host/connect string changed
        username_changed: Whether the username changed
        public_changed: Whether the public/private status changed
        expected_host: Expected host/connect string
        actual_host: Actual host/connect string
    """

    link_name: str = ""
    host_changed: Optional[tuple] = None  # (expected, actual)
    username_changed: Optional[tuple] = None  # (expected, actual)
    public_changed: Optional[tuple] = None  # (expected, actual)
    expected_host: Optional[str] = None
    actual_host: Optional[str] = None

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.link_name:
            self.link_name = self.object_name

        self.object_type = "database_link"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = (
            self.host_changed is not None
            or self.username_changed is not None
            or self.public_changed is not None
        )

        if self.has_diffs:
            # Database link changes require recreating the link (ERROR for critical infra)
            # Changed from WARNING to ERROR as links are critical infrastructure
            self.severity = DiffSeverity.ERROR


@dataclass
class LinkedServerDiff(DiffResult):
    """Represents differences in a linked server definition (SQL Server).

    Attributes:
        server_name: Name of the linked server
        product_changed: Whether the product name changed
        provider_changed: Whether the provider changed
        data_source_changed: Whether the data source changed
        catalog_changed: Whether the catalog changed
        username_changed: Whether the username changed
    """

    server_name: str = ""
    product_changed: Optional[tuple] = None  # (expected, actual)
    provider_changed: Optional[tuple] = None  # (expected, actual)
    data_source_changed: Optional[tuple] = None  # (expected, actual)
    catalog_changed: Optional[tuple] = None  # (expected, actual)
    username_changed: Optional[tuple] = None  # (expected, actual)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.server_name:
            self.server_name = self.object_name

        self.object_type = "linked_server"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = (
            self.product_changed is not None
            or self.provider_changed is not None
            or self.data_source_changed is not None
            or self.catalog_changed is not None
            or self.username_changed is not None
        )

        if self.has_diffs:
            # Linked server changes require recreating (ERROR for critical infra)
            self.severity = DiffSeverity.ERROR


@dataclass
class ModuleDiff(DiffResult):
    """Represents differences in a DB2 module definition.

    Attributes:
        module_name: Name of the module
        definition_changed: Whether the module definition changed
    """

    module_name: str = ""
    definition_changed: bool = False

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.module_name:
            self.module_name = self.object_name

        self.object_type = "module"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = self.definition_changed

        if self.has_diffs:
            # Module changes require recreating the module (WARNING - non-breaking)
            self.severity = DiffSeverity.WARNING


@dataclass
class ForeignDataWrapperDiff(DiffResult):
    """Represents differences in a foreign data wrapper definition (PostgreSQL).

    Attributes:
        fdw_name: Name of the foreign data wrapper
        handler_changed: Whether the handler function changed
        validator_changed: Whether the validator function changed
        options_changed: Whether the FDW options changed
    """

    fdw_name: str = ""
    handler_changed: Optional[tuple] = None  # (expected, actual)
    validator_changed: Optional[tuple] = None  # (expected, actual)
    options_changed: Optional[tuple] = None  # (expected, actual)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.fdw_name:
            self.fdw_name = self.object_name

        self.object_type = "foreign_data_wrapper"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = (
            self.handler_changed is not None
            or self.validator_changed is not None
            or self.options_changed is not None
        )

        if self.has_diffs:
            # FDW changes are warnings (can be altered)
            self.severity = DiffSeverity.WARNING


@dataclass
class ForeignServerDiff(DiffResult):
    """Represents differences in a foreign server definition (PostgreSQL).

    Attributes:
        server_name: Name of the foreign server
        fdw_changed: Whether the FDW name changed
        host_changed: Whether the host changed
        port_changed: Whether the port changed
        dbname_changed: Whether the database name changed
        options_changed: Whether server options changed
    """

    server_name: str = ""
    fdw_changed: Optional[tuple] = None  # (expected, actual)
    host_changed: Optional[tuple] = None  # (expected, actual)
    port_changed: Optional[tuple] = None  # (expected, actual)
    dbname_changed: Optional[tuple] = None  # (expected, actual)
    options_changed: Optional[tuple] = None  # (expected, actual)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.server_name:
            self.server_name = self.object_name

        self.object_type = "foreign_server"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = (
            self.fdw_changed is not None
            or self.host_changed is not None
            or self.port_changed is not None
            or self.dbname_changed is not None
            or self.options_changed is not None
        )

        if self.has_diffs:
            # Foreign server changes are errors (affects foreign tables)
            self.severity = DiffSeverity.ERROR


@dataclass
class ExtensionDiff(DiffResult):
    """Represents differences in an extension definition (PostgreSQL).

    Attributes:
        extension_name: Name of the extension
        version_changed: Whether the extension version changed
        schema_changed: Whether the extension schema changed
        expected_version: Expected extension version
        actual_version: Actual extension version
    """

    extension_name: str = ""
    version_changed: Optional[tuple] = None  # (expected, actual)
    schema_changed: Optional[tuple] = None  # (expected, actual)
    expected_version: Optional[str] = None
    actual_version: Optional[str] = None

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.extension_name:
            self.extension_name = self.object_name

        self.object_type = "extension"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = self.version_changed is not None or self.schema_changed is not None

        if self.has_diffs:
            # Extension changes are warnings (can be updated with ALTER EXTENSION)
            self.severity = DiffSeverity.WARNING


@dataclass
class EventDiff(DiffResult):
    """Represents differences in an event definition (MySQL).

    Attributes:
        event_name: Name of the event
        definition_changed: Whether the event body changed
        schedule_changed: Whether the event schedule changed
        enabled_changed: Whether the enabled status changed
        event_type_changed: Whether the event type changed (ONE TIME/RECURRING)
    """

    event_name: str = ""
    definition_changed: bool = False
    schedule_changed: Optional[tuple] = None  # (expected, actual)
    enabled_changed: Optional[tuple] = None  # (expected, actual)
    event_type_changed: Optional[tuple] = None  # (expected, actual)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.event_name:
            self.event_name = self.object_name

        self.object_type = "event"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = (
            self.definition_changed
            or self.schedule_changed is not None
            or self.enabled_changed is not None
            or self.event_type_changed is not None
        )

        if self.has_diffs:
            # Event changes are warnings (can be recreated with ALTER EVENT)
            self.severity = DiffSeverity.WARNING


@dataclass
class UserDefinedTypeDiff(DiffResult):
    """Represents differences in a user-defined type definition.

    Attributes:
        type_name: Name of the user-defined type
        type_category_changed: Whether the type category changed (COMPOSITE, ENUM, DOMAIN, etc.)
        base_type_changed: Whether the base type changed (for DOMAIN/DISTINCT types)
        attributes_changed: Whether composite type attributes changed
        enum_values_changed: Whether enum values changed
        definition_changed: Whether the type definition changed
        expected_type_category: Expected type category
        actual_type_category: Actual type category
        expected_base_type: Expected base type
        actual_base_type: Actual base type
    """

    type_name: str = ""
    type_category_changed: Optional[tuple] = None  # (expected, actual)
    base_type_changed: Optional[tuple] = None  # (expected, actual)
    attributes_changed: bool = False
    enum_values_changed: bool = False
    definition_changed: bool = False
    expected_type_category: Optional[str] = None
    actual_type_category: Optional[str] = None
    expected_base_type: Optional[str] = None
    actual_base_type: Optional[str] = None
    expected_attributes: Optional[List] = None
    actual_attributes: Optional[List] = None
    expected_enum_values: Optional[List] = None
    actual_enum_values: Optional[List] = None

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.type_name:
            self.type_name = self.object_name

        self.object_type = "user_defined_type"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = any(
            [
                self.type_category_changed is not None,
                self.base_type_changed is not None,
                self.attributes_changed,
                self.enum_values_changed,
                self.definition_changed,
            ]
        )

        if self.has_diffs:
            # Type category and base type changes are breaking changes (ERROR)
            # Attribute, enum value, and definition changes are non-breaking (WARNING)
            if self.type_category_changed is not None or self.base_type_changed is not None:
                self.severity = DiffSeverity.ERROR
            else:
                self.severity = DiffSeverity.WARNING


@dataclass
class SchemaDiff(DiffResult):
    """Represents schema-level comparison results.

    Attributes:
        schema_name: Name of the schema
        missing_tables: Tables in expected but not in actual
        extra_tables: Tables in actual but not in expected
        modified_tables: Tables with differences
        missing_views: Views in expected but not in actual
        extra_views: Views in actual but not in expected
        modified_views: Views with differences
        missing_indexes: Indexes in expected but not in actual
        extra_indexes: Indexes in actual but not in expected
        modified_indexes: Indexes with differences
        missing_sequences: Sequences in expected but not in actual
        extra_sequences: Sequences in actual but not in expected
        modified_sequences: Sequences with differences
        missing_triggers: Triggers in expected but not in actual
        extra_triggers: Triggers in actual but not in expected
        modified_triggers: Triggers with differences
        missing_procedures: Procedures in expected but not in actual
        extra_procedures: Procedures in actual but not in expected
        modified_procedures: Procedures with differences
        missing_functions: Functions in expected but not in actual
        extra_functions: Functions in actual but not in expected
        modified_functions: Functions with differences
        missing_synonyms: Synonyms in expected but not in actual
        extra_synonyms: Synonyms in actual but not in expected
        modified_synonyms: Synonyms with differences
        missing_packages: Packages in expected but not in actual
        extra_packages: Packages in actual but not in expected
        modified_packages: Packages with differences
        missing_extensions: Extensions in expected but not in actual
        extra_extensions: Extensions in actual but not in expected
        modified_extensions: Extensions with differences
        missing_events: Events in expected but not in actual
        extra_events: Events in actual but not in expected
        modified_events: Events with differences
        missing_user_defined_types: User-defined types in expected but not in actual
        extra_user_defined_types: User-defined types in actual but not in expected
        modified_user_defined_types: User-defined types with differences
    """

    schema_name: str = ""
    missing_tables: List[str] = field(default_factory=list)
    extra_tables: List[str] = field(default_factory=list)
    modified_tables: List[TableDiff] = field(default_factory=list)
    missing_views: List[str] = field(default_factory=list)
    extra_views: List[str] = field(default_factory=list)
    modified_views: List[ViewDiff] = field(default_factory=list)
    missing_indexes: List[str] = field(default_factory=list)
    extra_indexes: List[str] = field(default_factory=list)
    modified_indexes: List[IndexDiff] = field(default_factory=list)
    missing_sequences: List[str] = field(default_factory=list)
    extra_sequences: List[str] = field(default_factory=list)
    modified_sequences: List[SequenceDiff] = field(default_factory=list)
    missing_triggers: List[str] = field(default_factory=list)
    extra_triggers: List[str] = field(default_factory=list)
    modified_triggers: List[TriggerDiff] = field(default_factory=list)
    missing_procedures: List[str] = field(default_factory=list)
    extra_procedures: List[str] = field(default_factory=list)
    modified_procedures: List[ProcedureDiff] = field(default_factory=list)
    missing_functions: List[str] = field(default_factory=list)
    extra_functions: List[str] = field(default_factory=list)
    modified_functions: List[FunctionDiff] = field(default_factory=list)
    missing_synonyms: List[str] = field(default_factory=list)
    extra_synonyms: List[str] = field(default_factory=list)
    modified_synonyms: List[SynonymDiff] = field(default_factory=list)
    missing_packages: List[str] = field(default_factory=list)
    extra_packages: List[str] = field(default_factory=list)
    modified_packages: List["PackageDiff"] = field(default_factory=list)
    missing_modules: List[str] = field(default_factory=list)
    extra_modules: List[str] = field(default_factory=list)
    modified_modules: List["ModuleDiff"] = field(default_factory=list)
    missing_database_links: List[str] = field(default_factory=list)
    extra_database_links: List[str] = field(default_factory=list)
    modified_database_links: List[DatabaseLinkDiff] = field(default_factory=list)
    missing_linked_servers: List[str] = field(default_factory=list)
    extra_linked_servers: List[str] = field(default_factory=list)
    modified_linked_servers: List[LinkedServerDiff] = field(default_factory=list)
    missing_foreign_data_wrappers: List[str] = field(default_factory=list)
    extra_foreign_data_wrappers: List[str] = field(default_factory=list)
    modified_foreign_data_wrappers: List[ForeignDataWrapperDiff] = field(default_factory=list)
    missing_foreign_servers: List[str] = field(default_factory=list)
    extra_foreign_servers: List[str] = field(default_factory=list)
    modified_foreign_servers: List[ForeignServerDiff] = field(default_factory=list)
    missing_extensions: List[str] = field(default_factory=list)
    extra_extensions: List[str] = field(default_factory=list)
    modified_extensions: List[ExtensionDiff] = field(default_factory=list)
    missing_events: List[str] = field(default_factory=list)
    extra_events: List[str] = field(default_factory=list)
    modified_events: List[EventDiff] = field(default_factory=list)
    missing_user_defined_types: List[str] = field(default_factory=list)
    extra_user_defined_types: List[str] = field(default_factory=list)
    modified_user_defined_types: List[UserDefinedTypeDiff] = field(default_factory=list)

    def __post_init__(self):
        """Calculate has_diffs and severity after initialization."""
        if not self.schema_name:
            self.schema_name = self.object_name

        self.object_type = "schema"
        self._calculate_diffs()

    def _calculate_diffs(self):
        """Calculate whether differences exist and their severity."""
        self.has_diffs = any(
            [
                self.missing_tables,
                self.extra_tables,
                self.modified_tables,
                self.missing_views,
                self.extra_views,
                self.modified_views,
                self.missing_indexes,
                self.extra_indexes,
                self.modified_indexes,
                self.missing_sequences,
                self.extra_sequences,
                self.modified_sequences,
                self.missing_triggers,
                self.extra_triggers,
                self.modified_triggers,
                self.missing_procedures,
                self.extra_procedures,
                self.modified_procedures,
                self.missing_functions,
                self.extra_functions,
                self.modified_functions,
                self.missing_synonyms,
                self.extra_synonyms,
                self.modified_synonyms,
                self.missing_packages,
                self.extra_packages,
                self.modified_packages,
                self.missing_modules,
                self.extra_modules,
                self.modified_modules,
                self.missing_database_links,
                self.extra_database_links,
                self.modified_database_links,
                self.missing_linked_servers,
                self.extra_linked_servers,
                self.modified_linked_servers,
                self.missing_foreign_data_wrappers,
                self.extra_foreign_data_wrappers,
                self.modified_foreign_data_wrappers,
                self.missing_foreign_servers,
                self.extra_foreign_servers,
                self.modified_foreign_servers,
                self.missing_extensions,
                self.extra_extensions,
                self.modified_extensions,
                self.missing_events,
                self.extra_events,
                self.modified_events,
                self.missing_user_defined_types,
                self.extra_user_defined_types,
                self.modified_user_defined_types,
            ]
        )

        if not self.has_diffs:
            return

        # Calculate severity - check all modified objects for ERROR severity
        has_error = False

        # Missing tables/views/procedures/functions/packages/types are always errors
        if (
            self.missing_tables
            or self.missing_views
            or self.missing_procedures
            or self.missing_functions
            or self.missing_packages
            or self.missing_user_defined_types
        ):
            has_error = True

        if self.extra_user_defined_types:
            has_error = True

        # Check modified objects for error severity
        for table_diff in self.modified_tables:
            if table_diff.severity == DiffSeverity.ERROR:
                has_error = True
                break

        if not has_error:
            for view_diff in self.modified_views:
                if view_diff.severity == DiffSeverity.ERROR:
                    has_error = True
                    break

        if not has_error:
            for proc_diff in self.modified_procedures:
                if proc_diff.severity == DiffSeverity.ERROR:
                    has_error = True
                    break

        if not has_error:
            for func_diff in self.modified_functions:
                if func_diff.severity == DiffSeverity.ERROR:
                    has_error = True
                    break

        if not has_error:
            for udt_diff in self.modified_user_defined_types:
                if udt_diff.severity == DiffSeverity.ERROR:
                    has_error = True
                    break

        # Set severity
        if has_error:
            self.severity = DiffSeverity.ERROR
        else:
            self.severity = DiffSeverity.WARNING

    def get_diff_count(self) -> Dict[str, int]:
        """Get count of each type of difference.

        Returns:
            Dictionary with counts of different types
        """
        return {
            "missing_tables": len(self.missing_tables),
            "extra_tables": len(self.extra_tables),
            "modified_tables": len(self.modified_tables),
            "missing_views": len(self.missing_views),
            "extra_views": len(self.extra_views),
            "modified_views": len(self.modified_views),
            "missing_indexes": len(self.missing_indexes),
            "extra_indexes": len(self.extra_indexes),
            "modified_indexes": len(self.modified_indexes),
            "missing_sequences": len(self.missing_sequences),
            "extra_sequences": len(self.extra_sequences),
            "modified_sequences": len(self.modified_sequences),
            "missing_triggers": len(self.missing_triggers),
            "extra_triggers": len(self.extra_triggers),
            "modified_triggers": len(self.modified_triggers),
            "missing_procedures": len(self.missing_procedures),
            "extra_procedures": len(self.extra_procedures),
            "modified_procedures": len(self.modified_procedures),
            "missing_functions": len(self.missing_functions),
            "extra_functions": len(self.extra_functions),
            "modified_functions": len(self.modified_functions),
            "missing_synonyms": len(self.missing_synonyms),
            "extra_synonyms": len(self.extra_synonyms),
            "modified_synonyms": len(self.modified_synonyms),
            "missing_packages": len(self.missing_packages),
            "extra_packages": len(self.extra_packages),
            "modified_packages": len(self.modified_packages),
            "missing_modules": len(self.missing_modules),
            "extra_modules": len(self.extra_modules),
            "modified_modules": len(self.modified_modules),
            "missing_database_links": len(self.missing_database_links),
            "extra_database_links": len(self.extra_database_links),
            "modified_database_links": len(self.modified_database_links),
            "missing_linked_servers": len(self.missing_linked_servers),
            "extra_linked_servers": len(self.extra_linked_servers),
            "modified_linked_servers": len(self.modified_linked_servers),
            "missing_foreign_data_wrappers": len(self.missing_foreign_data_wrappers),
            "extra_foreign_data_wrappers": len(self.extra_foreign_data_wrappers),
            "modified_foreign_data_wrappers": len(self.modified_foreign_data_wrappers),
            "missing_foreign_servers": len(self.missing_foreign_servers),
            "extra_foreign_servers": len(self.extra_foreign_servers),
            "modified_foreign_servers": len(self.modified_foreign_servers),
            "missing_extensions": len(self.missing_extensions),
            "extra_extensions": len(self.extra_extensions),
            "modified_extensions": len(self.modified_extensions),
            "missing_events": len(self.missing_events),
            "extra_events": len(self.extra_events),
            "modified_events": len(self.modified_events),
            "missing_user_defined_types": len(self.missing_user_defined_types),
            "extra_user_defined_types": len(self.extra_user_defined_types),
            "modified_user_defined_types": len(self.modified_user_defined_types),
        }

    def get_total_diff_count(self) -> int:
        """Get total count of all differences.

        Returns:
            Total number of differences
        """
        counts = self.get_diff_count()
        return sum(counts.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update(
            {
                "schema_name": self.schema_name,
                "missing_tables": self.missing_tables,
                "extra_tables": self.extra_tables,
                "modified_tables": [table.to_dict() for table in self.modified_tables],
                "missing_views": self.missing_views,
                "extra_views": self.extra_views,
                "modified_views": [view.to_dict() for view in self.modified_views],
                "missing_indexes": self.missing_indexes,
                "extra_indexes": self.extra_indexes,
                "modified_indexes": [idx.to_dict() for idx in self.modified_indexes],
                "missing_sequences": self.missing_sequences,
                "extra_sequences": self.extra_sequences,
                "modified_sequences": [seq.to_dict() for seq in self.modified_sequences],
                "missing_triggers": self.missing_triggers,
                "extra_triggers": self.extra_triggers,
                "modified_triggers": [trg.to_dict() for trg in self.modified_triggers],
                "missing_procedures": self.missing_procedures,
                "extra_procedures": self.extra_procedures,
                "modified_procedures": [proc.to_dict() for proc in self.modified_procedures],
                "missing_functions": self.missing_functions,
                "extra_functions": self.extra_functions,
                "modified_functions": [func.to_dict() for func in self.modified_functions],
                "missing_synonyms": self.missing_synonyms,
                "extra_synonyms": self.extra_synonyms,
                "modified_synonyms": [syn.to_dict() for syn in self.modified_synonyms],
                "missing_packages": self.missing_packages,
                "extra_packages": self.extra_packages,
                "modified_packages": [pkg.to_dict() for pkg in self.modified_packages],
                "missing_modules": self.missing_modules,
                "extra_modules": self.extra_modules,
                "modified_modules": [mod.to_dict() for mod in self.modified_modules],
                "missing_database_links": self.missing_database_links,
                "extra_database_links": self.extra_database_links,
                "modified_database_links": [
                    link.to_dict() for link in self.modified_database_links
                ],
                "missing_linked_servers": self.missing_linked_servers,
                "extra_linked_servers": self.extra_linked_servers,
                "modified_linked_servers": [srv.to_dict() for srv in self.modified_linked_servers],
                "missing_foreign_data_wrappers": self.missing_foreign_data_wrappers,
                "extra_foreign_data_wrappers": self.extra_foreign_data_wrappers,
                "modified_foreign_data_wrappers": [
                    fdw.to_dict() for fdw in self.modified_foreign_data_wrappers
                ],
                "missing_foreign_servers": self.missing_foreign_servers,
                "extra_foreign_servers": self.extra_foreign_servers,
                "modified_foreign_servers": [
                    srv.to_dict() for srv in self.modified_foreign_servers
                ],
                "missing_extensions": self.missing_extensions,
                "extra_extensions": self.extra_extensions,
                "modified_extensions": [ext.to_dict() for ext in self.modified_extensions],
                "missing_events": self.missing_events,
                "extra_events": self.extra_events,
                "modified_events": [evt.to_dict() for evt in self.modified_events],
                "missing_user_defined_types": self.missing_user_defined_types,
                "extra_user_defined_types": self.extra_user_defined_types,
                "modified_user_defined_types": [
                    udt.to_dict() for udt in self.modified_user_defined_types
                ],
                "diff_count": self.get_diff_count(),
                "total_diff_count": self.get_total_diff_count(),
            }
        )
        return result

    def __str__(self) -> str:
        """Human-readable string representation."""
        if not self.has_diffs:
            return f"Schema '{self.schema_name}': No differences"

        parts = []
        counts = self.get_diff_count()

        # Tables
        if counts["missing_tables"]:
            parts.append(f"{counts['missing_tables']} missing table(s)")
        if counts["extra_tables"]:
            parts.append(f"{counts['extra_tables']} extra table(s)")
        if counts["modified_tables"]:
            parts.append(f"{counts['modified_tables']} modified table(s)")

        # Views
        if counts["missing_views"]:
            parts.append(f"{counts['missing_views']} missing view(s)")
        if counts["extra_views"]:
            parts.append(f"{counts['extra_views']} extra view(s)")
        if counts["modified_views"]:
            parts.append(f"{counts['modified_views']} modified view(s)")

        # Indexes
        if counts["missing_indexes"]:
            parts.append(f"{counts['missing_indexes']} missing index(es)")
        if counts["extra_indexes"]:
            parts.append(f"{counts['extra_indexes']} extra index(es)")
        if counts["modified_indexes"]:
            parts.append(f"{counts['modified_indexes']} modified index(es)")

        # Sequences
        if counts["missing_sequences"]:
            parts.append(f"{counts['missing_sequences']} missing sequence(s)")
        if counts["extra_sequences"]:
            parts.append(f"{counts['extra_sequences']} extra sequence(s)")
        if counts["modified_sequences"]:
            parts.append(f"{counts['modified_sequences']} modified sequence(s)")

        # Triggers
        if counts["missing_triggers"]:
            parts.append(f"{counts['missing_triggers']} missing trigger(s)")
        if counts["extra_triggers"]:
            parts.append(f"{counts['extra_triggers']} extra trigger(s)")
        if counts["modified_triggers"]:
            parts.append(f"{counts['modified_triggers']} modified trigger(s)")

        # Procedures
        if counts["missing_procedures"]:
            parts.append(f"{counts['missing_procedures']} missing procedure(s)")
        if counts["extra_procedures"]:
            parts.append(f"{counts['extra_procedures']} extra procedure(s)")
        if counts["modified_procedures"]:
            parts.append(f"{counts['modified_procedures']} modified procedure(s)")

        # Functions
        if counts["missing_functions"]:
            parts.append(f"{counts['missing_functions']} missing function(s)")
        if counts["extra_functions"]:
            parts.append(f"{counts['extra_functions']} extra function(s)")
        if counts["modified_functions"]:
            parts.append(f"{counts['modified_functions']} modified function(s)")

        # Synonyms
        if counts["missing_synonyms"]:
            parts.append(f"{counts['missing_synonyms']} missing synonym(s)")
        if counts["extra_synonyms"]:
            parts.append(f"{counts['extra_synonyms']} extra synonym(s)")
        if counts["modified_synonyms"]:
            parts.append(f"{counts['modified_synonyms']} modified synonym(s)")

        # Packages
        if counts["missing_packages"]:
            parts.append(f"{counts['missing_packages']} missing package(s)")
        if counts["extra_packages"]:
            parts.append(f"{counts['extra_packages']} extra package(s)")
        if counts["modified_packages"]:
            parts.append(f"{counts['modified_packages']} modified package(s)")

        # Modules
        if counts["missing_modules"]:
            parts.append(f"{counts['missing_modules']} missing module(s)")
        if counts["extra_modules"]:
            parts.append(f"{counts['extra_modules']} extra module(s)")
        if counts["modified_modules"]:
            parts.append(f"{counts['modified_modules']} modified module(s)")

        # Database Links
        if counts["missing_database_links"]:
            parts.append(f"{counts['missing_database_links']} missing database link(s)")
        if counts["extra_database_links"]:
            parts.append(f"{counts['extra_database_links']} extra database link(s)")
        if counts["modified_database_links"]:
            parts.append(f"{counts['modified_database_links']} modified database link(s)")

        # Linked Servers
        if counts["missing_linked_servers"]:
            parts.append(f"{counts['missing_linked_servers']} missing linked server(s)")
        if counts["extra_linked_servers"]:
            parts.append(f"{counts['extra_linked_servers']} extra linked server(s)")
        if counts["modified_linked_servers"]:
            parts.append(f"{counts['modified_linked_servers']} modified linked server(s)")

        # Database Links
        if counts["missing_database_links"]:
            parts.append(f"{counts['missing_database_links']} missing database link(s)")
        if counts["extra_database_links"]:
            parts.append(f"{counts['extra_database_links']} extra database link(s)")
        if counts["modified_database_links"]:
            parts.append(f"{counts['modified_database_links']} modified database link(s)")

        # Foreign Data Wrappers
        if counts["missing_foreign_data_wrappers"]:
            parts.append(
                f"{counts['missing_foreign_data_wrappers']} missing foreign data wrapper(s)"
            )
        if counts["extra_foreign_data_wrappers"]:
            parts.append(f"{counts['extra_foreign_data_wrappers']} extra foreign data wrapper(s)")
        if counts["modified_foreign_data_wrappers"]:
            parts.append(
                f"{counts['modified_foreign_data_wrappers']} modified foreign data wrapper(s)"
            )

        # Foreign Servers
        if counts["missing_foreign_servers"]:
            parts.append(f"{counts['missing_foreign_servers']} missing foreign server(s)")
        if counts["extra_foreign_servers"]:
            parts.append(f"{counts['extra_foreign_servers']} extra foreign server(s)")
        if counts["modified_foreign_servers"]:
            parts.append(f"{counts['modified_foreign_servers']} modified foreign server(s)")

        # Extensions
        if counts["missing_extensions"]:
            parts.append(f"{counts['missing_extensions']} missing extension(s)")
        if counts["extra_extensions"]:
            parts.append(f"{counts['extra_extensions']} extra extension(s)")
        if counts["modified_extensions"]:
            parts.append(f"{counts['modified_extensions']} modified extension(s)")

        # Events
        if counts["missing_events"]:
            parts.append(f"{counts['missing_events']} missing event(s)")
        if counts["extra_events"]:
            parts.append(f"{counts['extra_events']} extra event(s)")
        if counts["modified_events"]:
            parts.append(f"{counts['modified_events']} modified event(s)")

        # User-Defined Types
        if counts["missing_user_defined_types"]:
            parts.append(f"{counts['missing_user_defined_types']} missing user-defined type(s)")
        if counts["extra_user_defined_types"]:
            parts.append(f"{counts['extra_user_defined_types']} extra user-defined type(s)")
        if counts["modified_user_defined_types"]:
            parts.append(f"{counts['modified_user_defined_types']} modified user-defined type(s)")

        total = self.get_total_diff_count()
        return f"Schema '{self.schema_name}' [{self.severity.value}]: {total} difference(s) - {', '.join(parts)}"
