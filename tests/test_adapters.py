import importlib
import sys
import types
from contextlib import contextmanager
from typing import Tuple

import pytest

from sqlmeta import ConstraintType, SqlColumn, SqlConstraint, Table


@contextmanager
def temporary_module(name: str, module: types.ModuleType):
    """Temporarily install a module in sys.modules."""
    original = sys.modules.get(name)
    sys.modules[name] = module
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def clear_module(prefix: str) -> None:
    """Remove imported modules that start with prefix."""
    for mod in list(sys.modules):
        if mod == prefix or mod.startswith(f"{prefix}."):
            sys.modules.pop(mod, None)


def build_fake_sqlalchemy() -> Tuple[types.ModuleType, types.ModuleType]:
    sa_module = types.ModuleType("sqlalchemy")
    schema_module = types.ModuleType("sqlalchemy.schema")

    class DummyType:
        def __init__(self, name, size=None):
            self.name = name
            self.size = size

        def __repr__(self):
            if self.size is None:
                return self.name
            return f"{self.name}({self.size})"

        __str__ = __repr__

    class Integer(DummyType):
        def __init__(self):
            super().__init__("INTEGER")

    class String(DummyType):
        def __init__(self, size=None):
            super().__init__("VARCHAR", size)

    class Text(DummyType):
        def __init__(self):
            super().__init__("TEXT")

    class Boolean(DummyType):
        def __init__(self):
            super().__init__("BOOLEAN")

    class Numeric(DummyType):
        def __init__(self):
            super().__init__("NUMERIC")

    class DateTime(DummyType):
        def __init__(self):
            super().__init__("DATETIME")

    class DummyMetaData:
        def __init__(self):
            self.tables = {}

    class DummyConstraint:
        def __init__(self, *columns, name=None):
            self.columns = [types.SimpleNamespace(name=col) if isinstance(col, str) else col for col in columns]
            self.name = name

    class PrimaryKeyConstraint(DummyConstraint):
        pass

    class UniqueConstraint(DummyConstraint):
        pass

    class CheckConstraint(DummyConstraint):
        def __init__(self, sqltext, name=None):
            super().__init__(name=name)
            self.sqltext = sqltext

    class DummyColumn:
        def __init__(
            self,
            name,
            type_,
            nullable=True,
            primary_key=False,
            unique=False,
            default=None,
            comment=None,
            autoincrement=False,
            server_default=None,
        ):
            self.name = name
            self.type = type_
            self.nullable = nullable
            self.primary_key = primary_key
            self.unique = unique
            self.default = default
            self.comment = comment
            self.autoincrement = autoincrement
            self.server_default = server_default

    class DummyTable:
        def __init__(self, name, metadata, *elements, schema=None, comment=None):
            self.name = name
            self.metadata = metadata
            self.schema = schema
            self.comment = comment
            self.columns = [elem for elem in elements if isinstance(elem, DummyColumn)]
            self.constraints = [elem for elem in elements if isinstance(elem, DummyConstraint)]
            metadata.tables[name] = self

    class DummyCreateTable:
        def __init__(self, table):
            self.table = table

        def compile(self, engine):
            schema_prefix = f"{self.table.schema}." if self.table.schema else ""
            cols = ", ".join(col.name for col in self.table.columns)
            return f"CREATE TABLE {schema_prefix}{self.table.name} ({cols})"

    def create_engine(url: str):
        return types.SimpleNamespace(url=url)

    sa_module.Integer = Integer
    sa_module.String = String
    sa_module.Text = Text
    sa_module.Boolean = Boolean
    sa_module.Numeric = Numeric
    sa_module.DateTime = DateTime
    sa_module.Boolean = Boolean
    sa_module.Column = DummyColumn
    sa_module.MetaData = DummyMetaData
    sa_module.Table = DummyTable
    sa_module.PrimaryKeyConstraint = PrimaryKeyConstraint
    sa_module.UniqueConstraint = UniqueConstraint
    sa_module.CheckConstraint = CheckConstraint
    sa_module.ForeignKey = lambda *args, **kwargs: ("foreign_key", args, kwargs)
    sa_module.create_engine = create_engine

    schema_module.CreateTable = DummyCreateTable
    schema_module.Table = DummyTable

    return sa_module, schema_module


def build_fake_pydantic() -> types.ModuleType:
    pydantic_module = types.ModuleType("pydantic")

    class BaseModel:
        __fields__: dict[str, object] = {}

        def __init__(self, **kwargs):
            for name in self.__class__.__fields__:
                setattr(self, name, kwargs.get(name))

        @classmethod
        def model_json_schema(cls):
            return {"title": cls.__name__, "fields": list(cls.__fields__.keys())}

    class DummyField:
        def __init__(self, **kwargs):
            self.metadata = kwargs

    def Field(**kwargs):
        return DummyField(**kwargs)

    def create_model(name, **fields):
        attrs = {"__fields__": {}, "__annotations__": {}}
        for field_name, (field_type, default) in fields.items():
            attrs["__fields__"][field_name] = default
            attrs["__annotations__"][field_name] = field_type
        return type(name, (BaseModel,), attrs)

    pydantic_module.BaseModel = BaseModel
    pydantic_module.Field = Field
    pydantic_module.create_model = create_model

    return pydantic_module


def build_fake_alembic() -> Tuple[types.ModuleType, types.ModuleType]:
    ops_module = types.ModuleType("alembic.operations")
    ops_ops_module = types.ModuleType("alembic.operations.ops")

    class Operations:
        pass

    class BaseOp:
        def __init__(self, *args, **kwargs):
            self.__dict__.update(kwargs)

    class CreateTableOp(BaseOp):
        def __init__(self, table_name, columns, schema=None):
            super().__init__(table_name=table_name, columns=columns, schema=schema)

        @classmethod
        def from_table(cls, table):
            return cls(table.name, list(table.columns), schema=table.schema)

    class AddColumnOp(BaseOp):
        def __init__(self, table_name, column, schema=None):
            super().__init__(table_name=table_name, column=column, schema=schema)

    class DropColumnOp(BaseOp):
        def __init__(self, table_name, column_name, schema=None):
            super().__init__(table_name=table_name, column_name=column_name, schema=schema)

    class AlterColumnOp(BaseOp):
        def __init__(self, table_name, column_name, schema=None, type_=None, nullable=None, server_default=None):
            super().__init__(
                table_name=table_name,
                column_name=column_name,
                schema=schema,
                type_=type_,
                nullable=nullable,
                server_default=server_default,
            )

    class DropTableOp(BaseOp):
        def __init__(self, table_name, schema=None):
            super().__init__(table_name=table_name, schema=schema)

    class MigrationScript:
        pass

    ops_module.Operations = Operations
    ops_ops_module.CreateTableOp = CreateTableOp
    ops_ops_module.AddColumnOp = AddColumnOp
    ops_ops_module.AlterColumnOp = AlterColumnOp
    ops_ops_module.DropColumnOp = DropColumnOp
    ops_ops_module.DropTableOp = DropTableOp
    ops_ops_module.MigrationScript = MigrationScript

    return ops_module, ops_ops_module


def reload_module(module_name: str):
    clear_module(module_name)
    return importlib.import_module(module_name)


def test_sqlalchemy_adapter_import_error():
    clear_module("sqlalchemy")
    module = reload_module("sqlmeta.adapters.sqlalchemy")

    with pytest.raises(ImportError):
        module.to_sqlalchemy(None)
    with pytest.raises(ImportError):
        module.from_sqlalchemy(None)
    assert not hasattr(module, "get_create_ddl")


def test_sqlalchemy_adapter_with_stub():
    sa_module, schema_module = build_fake_sqlalchemy()
    with temporary_module("sqlalchemy", sa_module), temporary_module("sqlalchemy.schema", schema_module):
        module = reload_module("sqlmeta.adapters.sqlalchemy")

        table = Table(
            "users",
            schema="public",
            columns=[
                SqlColumn("id", "INTEGER", is_nullable=False, is_primary_key=True, default_value="1"),
                SqlColumn("email", "VARCHAR(100)", is_nullable=False, is_unique=True),
            ],
            constraints=[
                SqlConstraint(ConstraintType.PRIMARY_KEY, column_names=["id"], name="pk_users"),
                SqlConstraint(ConstraintType.CHECK, column_names=["email LIKE '%@example.com'"], name="chk_email"),
            ],
        )

        sa_table = module.to_sqlalchemy(table)
        assert sa_table.name == "users"
        assert len(sa_table.columns) == 2

        rebuilt = module.from_sqlalchemy(sa_table)
        assert rebuilt.name == "users"
        assert len(rebuilt.columns) == 2

        ddl = module.get_create_ddl(table, dialect="postgresql")
        assert "CREATE TABLE" in ddl

        assert str(module._map_sql_type_to_sa("VARCHAR(50)")) == "VARCHAR(50)"
        assert str(module._map_sql_type_to_sa("INT")) == "INTEGER"


def test_pydantic_adapter_import_error():
    clear_module("pydantic")
    module = reload_module("sqlmeta.adapters.pydantic")

    with pytest.raises(ImportError):
        module.to_pydantic(None)
    with pytest.raises(ImportError):
        module.to_pydantic_schema(None)


def test_pydantic_adapter_with_stub():
    pydantic_module = build_fake_pydantic()
    with temporary_module("pydantic", pydantic_module):
        module = reload_module("sqlmeta.adapters.pydantic")

        table = Table(
            "user_profile",
            columns=[
                SqlColumn("id", "INT", is_nullable=False, is_primary_key=True),
                SqlColumn("bio", "TEXT", is_nullable=True, comment="User biography"),
            ],
        )
        model = module.to_pydantic(table)
        instance = model(id=1, bio="hello")
        assert instance.id == 1
        schema = module.to_pydantic_schema(table)
        assert schema["title"] == "UserProfile"
        assert "bio" in schema["fields"]


def test_alembic_adapter_import_error():
    clear_module("alembic")
    module = reload_module("sqlmeta.adapters.alembic")

    with pytest.raises(ImportError):
        module.generate_operations(None, None)
    with pytest.raises(ImportError):
        module.to_alembic_table(None)
    with pytest.raises(ImportError):
        module.generate_migration_script([], [])


def test_alembic_adapter_with_stubs():
    sa_module, schema_module = build_fake_sqlalchemy()
    ops_module, ops_ops_module = build_fake_alembic()

    with temporary_module("sqlalchemy", sa_module), temporary_module(
        "sqlalchemy.schema", schema_module
    ), temporary_module("alembic.operations", ops_module), temporary_module("alembic.operations.ops", ops_ops_module):
        module = reload_module("sqlmeta.adapters.alembic")

        source = Table(
            "users",
            schema="public",
            columns=[SqlColumn("id", "INTEGER", is_nullable=False, is_primary_key=True)],
        )
        target = Table(
            "users",
            schema="public",
            columns=[
                SqlColumn("id", "INTEGER", is_nullable=False, is_primary_key=True),
                SqlColumn("email", "VARCHAR(255)", is_nullable=False),
            ],
        )

        create_op = module.to_alembic_table(target)
        assert create_op.table_name == "users"
        assert len(create_op.columns) == 2

        ops = module.generate_operations(source, target, dialect="postgresql")
        assert any(hasattr(op, "column") for op in ops)

        script = module.generate_migration_script([source], [target], dialect="postgresql")
        assert "def upgrade()" in script

