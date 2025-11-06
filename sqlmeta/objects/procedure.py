from typing import Any, Dict, List, Optional

from sqlmeta.base import SqlObject, SqlObjectType


class Parameter:
    """Represents a stored procedure parameter."""

    def __init__(
        self,
        name: str,
        data_type: str,
        direction: str = "IN",
        default_value: Optional[str] = None,
        dialect: Optional[str] = None,
    ):
        """Initialize a procedure parameter.

        Args:
            name: Parameter name
            data_type: Parameter data type
            direction: Parameter direction (IN, OUT, INOUT)
            default_value: Default value for the parameter
            dialect: SQL dialect (optional)
        """
        self.name = name
        self.data_type = data_type
        self.direction = direction.upper()  # IN, OUT, INOUT
        self.default_value = default_value
        self.dialect = dialect

    def __str__(self) -> str:
        """String representation of the parameter."""
        # Get parameter direction syntax based on dialect
        if self.dialect and self.dialect.lower() == "sqlserver" and self.direction == "INOUT":
            # SQL Server uses OUTPUT instead of INOUT
            direction_str = "OUTPUT" if self.direction != "IN" else ""
        else:
            direction_str = self.direction if self.direction != "IN" else ""

        result = ""
        if direction_str:
            result += f"{direction_str} "
        result += f"{self.name} {self.data_type}"

        # Add default value if supported by dialect
        if self.default_value is not None:
            supports_defaults = True
            if self.dialect and self.dialect.lower() == "db2":
                # DB2 doesn't support parameter defaults
                supports_defaults = False

            if supports_defaults:
                result += f" = {self.default_value}"

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary."""
        return {
            "name": self.name,
            "data_type": self.data_type,
            "direction": self.direction,
            "default_value": self.default_value,
            "dialect": self.dialect,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Parameter":
        """Create parameter from dictionary."""
        return cls(
            name=data["name"],
            data_type=data["data_type"],
            direction=data.get("direction", "IN"),
            default_value=data.get("default_value"),
            dialect=data.get("dialect"),
        )


class Procedure(SqlObject):
    """Represents a stored procedure or function."""

    def __init__(
        self,
        name: str,
        schema: Optional[str] = None,
        parameters: Optional[List[Parameter]] = None,
        body: Optional[str] = None,
        language: str = "SQL",
        dialect: Optional[str] = None,
        is_function: bool = False,
        return_type: Optional[str] = None,
        comment: Optional[str] = None,
        definition: Optional[str] = None,
    ):
        """Initialize a stored procedure or function.

        Args:
            name: Procedure/function name
            schema: Schema name
            parameters: List of procedure/function parameters
            body: Procedure/function body
            language: Procedure language (SQL, PLSQL, PLPGSQL, TSQL, etc.)
            dialect: SQL dialect
            is_function: Whether this is a function (vs procedure)
            return_type: Return type for functions
            comment: Procedure/function comment/description
            definition: Full procedure/function definition SQL
        """
        object_type = SqlObjectType.FUNCTION if is_function else SqlObjectType.PROCEDURE
        super().__init__(name, object_type, schema, dialect)
        self.parameters = parameters or []

        # Ensure parameters inherit the dialect
        for param in self.parameters:
            if not param.dialect:
                param.dialect = dialect

        self.body = body
        self.language = language
        self.is_function = is_function
        self.return_type = return_type
        self.comment = comment
        self.definition = definition

    @property
    def create_statement(self) -> str:
        """Generate CREATE PROCEDURE or CREATE FUNCTION statement.

        The syntax varies by dialect.

        Returns:
            Dialect-specific CREATE PROCEDURE/FUNCTION statement
        """
        # Format schema and procedure/function name properly
        schema_name = self.format_identifier(self.schema) if self.schema else ""
        proc_name = self.format_identifier(self.name)
        schema_prefix = f"{schema_name}." if schema_name else ""

        # Use CREATE OR REPLACE for Oracle/PostgreSQL
        if self.dialect and self.dialect.lower() in ("oracle", "postgresql", "postgres"):
            create_keyword = "CREATE OR REPLACE"
        else:
            create_keyword = "CREATE"

        # Determine object type
        object_keyword = "FUNCTION" if self.is_function else "PROCEDURE"

        # Start statement
        stmt = f"{create_keyword} {object_keyword} {schema_prefix}{proc_name}"

        # Add parameters if available
        if self.parameters:
            params_str = ", ".join(str(param) for param in self.parameters)
            stmt += f"({params_str})"
        else:
            stmt += "()"

        # Add return type for functions
        if self.is_function and self.return_type:
            if self.dialect and self.dialect.lower() in ("postgresql", "postgres"):
                stmt += f" RETURNS {self.return_type}"
            elif self.dialect and self.dialect.lower() == "oracle":
                stmt += f" RETURN {self.return_type}"
            elif self.dialect and self.dialect.lower() in ("sqlserver", "mssql"):
                stmt += f" RETURNS {self.return_type}"
            else:
                stmt += f" RETURNS {self.return_type}"

        # Add language specification for PostgreSQL
        if (
            self.language != "SQL"
            and self.dialect
            and self.dialect.lower() in ("postgresql", "postgres")
        ):
            stmt += f"\nLANGUAGE {self.language.lower()}"

        # Add procedure/function body
        if self.body:
            if self.dialect and self.dialect.lower() == "oracle":
                stmt += f"\nAS\n{self.body}"
            elif self.dialect and self.dialect.lower() in ("sqlserver", "mssql"):
                stmt += f"\nAS\nBEGIN\n{self.body}\nEND"
            elif self.dialect and self.dialect.lower() in ("postgresql", "postgres"):
                stmt += f"\nAS $$\n{self.body}\n$$"
            else:
                stmt += f"\nAS\n{self.body}"

        return stmt

    @property
    def drop_statement(self) -> str:
        """Generate DROP PROCEDURE or DROP FUNCTION statement.

        Returns:
            SQL DROP PROCEDURE/FUNCTION statement
        """
        schema_prefix = self.format_identifier(self.schema) + "." if self.schema else ""
        proc_name = self.format_identifier(self.name)
        object_keyword = "FUNCTION" if self.is_function else "PROCEDURE"

        if self.dialect and self.dialect.lower() == "oracle":
            return f"DROP {object_keyword} {schema_prefix}{proc_name}"
        else:
            # PostgreSQL, SQL Server, MySQL, DB2
            return f"DROP {object_keyword} IF EXISTS {schema_prefix}{proc_name}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Procedure":
        """Create procedure/function from dictionary representation.

        Args:
            data: Dictionary with procedure/function attributes

        Returns:
            Procedure object
        """
        # Create parameters with the same dialect as the procedure
        parameters = []
        if "parameters" in data:
            dialect = data.get("dialect")
            parameters = [
                Parameter.from_dict({**param_data, "dialect": dialect})
                for param_data in data["parameters"]
            ]

        return cls(
            name=data["name"],
            schema=data.get("schema"),
            parameters=parameters,
            body=data.get("body"),
            language=data.get("language", "SQL"),
            dialect=data.get("dialect"),
            is_function=data.get("is_function", False),
            return_type=data.get("return_type"),
            comment=data.get("comment"),
            definition=data.get("definition"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert procedure/function to dictionary representation.

        Returns:
            Dictionary with procedure/function attributes
        """
        return {
            "name": self.name,
            "schema": self.schema,
            "object_type": self.object_type.value,
            "dialect": self.dialect,
            "parameters": [param.to_dict() for param in self.parameters],
            "body": self.body,
            "language": self.language,
            "is_function": self.is_function,
            "return_type": self.return_type,
            "comment": self.comment,
            "definition": self.definition,
        }
