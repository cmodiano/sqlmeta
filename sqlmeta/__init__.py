"""sqlmeta - Universal SQL metadata and schema representation for Python.

This package provides database-agnostic SQL schema representation, supporting:
- 15+ SQL object types (tables, views, procedures, triggers, etc.)
- Cross-database type normalization
- Schema comparison and drift detection
- Export to SQLAlchemy, Pydantic, Alembic, and more

Example:
    >>> from sqlmeta import Table, SqlColumn
    >>> users = Table(
    ...     name="users",
    ...     columns=[
    ...         SqlColumn("id", "SERIAL", is_primary_key=True),
    ...         SqlColumn("email", "VARCHAR(255)", is_nullable=False),
    ...     ]
    ... )
    >>> print(users.create_statement)
"""

# Base classes and types
from sqlmeta.base import (
    ConstraintType,
    SqlColumn,
    SqlConstraint,
    SqlObject,
    SqlObjectType,
)

# SQL objects
from sqlmeta.objects.database_link import DatabaseLink
from sqlmeta.objects.event import Event
from sqlmeta.objects.extension import Extension
from sqlmeta.objects.foreign_data_wrapper import ForeignDataWrapper
from sqlmeta.objects.foreign_server import ForeignServer
from sqlmeta.objects.index import Index
from sqlmeta.objects.linked_server import LinkedServer
from sqlmeta.objects.module import Module
from sqlmeta.objects.package import Package
from sqlmeta.objects.partition import Partition
from sqlmeta.objects.procedure import Parameter, Procedure
from sqlmeta.objects.sequence import Sequence
from sqlmeta.objects.synonym import Synonym
from sqlmeta.objects.table import Table
from sqlmeta.objects.trigger import Trigger
from sqlmeta.objects.user_defined_type import UserDefinedType
from sqlmeta.objects.view import View

__version__ = "0.1.0"

__all__ = [
    # Base classes
    "SqlObject",
    "SqlObjectType",
    "SqlColumn",
    "SqlConstraint",
    "ConstraintType",
    # SQL objects
    "Table",
    "View",
    "Sequence",
    "Procedure",
    "Parameter",
    "Index",
    "Trigger",
    "Synonym",
    "UserDefinedType",
    "Extension",
    "Package",
    "Module",
    "DatabaseLink",
    "LinkedServer",
    "ForeignDataWrapper",
    "ForeignServer",
    "Event",
    "Partition",
]
