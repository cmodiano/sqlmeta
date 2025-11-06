"""Oracle Package SQL Model."""

from typing import Any, Dict, List, Optional

from sqlmeta.base import SqlObject, SqlObjectType


class Package(SqlObject):
    """Represents an Oracle package (specification and body)."""

    def __init__(
        self,
        name: str,
        schema: Optional[str] = None,
        spec: Optional[str] = None,
        body: Optional[str] = None,
        dialect: Optional[str] = "oracle",
    ):
        """Initialize an Oracle package.

        Args:
            name: Package name
            schema: Schema name (optional)
            spec: Package specification (header/interface)
            body: Package body (implementation)
            dialect: SQL dialect (defaults to oracle)
        """
        super().__init__(name, SqlObjectType.PACKAGE, schema, dialect)
        self.spec = spec
        self.body = body
        # Track procedures and functions declared in this package
        self.procedures: List[str] = []
        self.functions: List[str] = []

    @property
    def create_statement(self) -> str:
        """Generate CREATE PACKAGE statements.

        Returns both spec and body if available.

        Returns:
            CREATE PACKAGE and CREATE PACKAGE BODY statements
        """
        statements = []

        # Format identifiers
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        package_name = self.format_identifier(self.name)
        schema_prefix = f"{schema_name}." if schema_name else ""

        # Create package specification
        if self.spec:
            spec_stmt = f"CREATE OR REPLACE PACKAGE {schema_prefix}{package_name}\n"
            spec_stmt += self.spec
            statements.append(spec_stmt)

        # Create package body
        if self.body:
            body_stmt = f"CREATE OR REPLACE PACKAGE BODY {schema_prefix}{package_name}\n"
            body_stmt += self.body
            statements.append(body_stmt)

        return "\n/\n\n".join(statements) if statements else ""

    def __str__(self) -> str:
        """Return string representation of the package."""
        qualified = f"{self.schema}.{self.name}" if self.schema else self.name
        if self.spec and self.body:
            return f"Package {qualified} (spec + body)"
        elif self.spec:
            return f"Package {qualified} (spec only)"
        elif self.body:
            return f"Package {qualified} (body only)"
        return f"Package {qualified}"

    def __eq__(self, other: Any) -> bool:
        """Check if two packages are equal."""
        if not isinstance(other, Package):
            return False
        return super().__eq__(other) and self.spec == other.spec and self.body == other.body

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Package":
        """Create package from dictionary representation.

        Args:
            data: Dictionary with package attributes

        Returns:
            Package object
        """
        return cls(
            name=data["name"],
            schema=data.get("schema"),
            spec=data.get("spec"),
            body=data.get("body"),
            dialect=data.get("dialect", "oracle"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert package to dictionary representation.

        Returns:
            Dictionary with package attributes
        """
        return {
            "name": self.name,
            "schema": self.schema,
            "object_type": self.object_type.value,
            "dialect": self.dialect,
            "spec": self.spec,
            "body": self.body,
            "procedures": self.procedures,
            "functions": self.functions,
        }
