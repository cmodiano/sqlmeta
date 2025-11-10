import importlib
import sys
import types
from contextlib import contextmanager


@contextmanager
def temp_module(name: str, module: types.ModuleType | None):
    original = sys.modules.get(name)
    if module is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = module
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def reload_module(name: str):
    if name in sys.modules:
        del sys.modules[name]
    return importlib.import_module(name)


def build_stub_sqlalchemy():
    sa_module = types.ModuleType("sqlalchemy")
    schema_module = types.ModuleType("sqlalchemy.schema")

    class DummyType:
        def __repr__(self):
            return "DUMMY"

    class Column:
        def __init__(self, *args, **kwargs):
            pass

    class MetaData:
        pass

    class SATable:
        def __init__(self, name, metadata, *columns, schema=None, comment=None):
            self.name = name
            self.columns = columns
            self.schema = schema

    class CreateTable:
        def __init__(self, table):
            self.table = table

        def compile(self, engine):
            return f"CREATE TABLE {self.table.name}"

    sa_module.Integer = DummyType
    sa_module.String = DummyType
    sa_module.Text = DummyType
    sa_module.Boolean = DummyType
    sa_module.Numeric = DummyType
    sa_module.DateTime = DummyType
    sa_module.Column = Column
    sa_module.MetaData = MetaData
    sa_module.Table = SATable
    sa_module.PrimaryKeyConstraint = object
    sa_module.UniqueConstraint = object
    sa_module.CheckConstraint = object
    sa_module.ForeignKey = object
    sa_module.create_engine = lambda url: object()

    schema_module.CreateTable = CreateTable
    schema_module.Table = SATable

    return sa_module, schema_module


def build_stub_pydantic():
    pydantic = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        @classmethod
        def model_json_schema(cls):
            return {"title": cls.__name__}

    class DummyField:
        pass

    def Field(**kwargs):
        return DummyField()

    def create_model(name, **fields):
        attrs = {"__annotations__": {k: v[0] for k, v in fields.items()}}
        return type(name, (BaseModel,), attrs)

    pydantic.BaseModel = BaseModel
    pydantic.Field = Field
    pydantic.create_model = create_model
    return pydantic


def build_stub_alembic():
    ops = types.ModuleType("alembic.operations")
    ops_ops = types.ModuleType("alembic.operations.ops")

    class Operations:
        pass

    class BaseOp:
        pass

    class CreateTableOp(BaseOp):
        @classmethod
        def from_table(cls, table):
            return cls()

    class AddColumnOp(BaseOp):
        pass

    class AlterColumnOp(BaseOp):
        pass

    class DropColumnOp(BaseOp):
        pass

    class DropTableOp(BaseOp):
        pass

    class MigrationScript:
        pass

    ops.Operations = Operations
    ops_ops.CreateTableOp = CreateTableOp
    ops_ops.AddColumnOp = AddColumnOp
    ops_ops.AlterColumnOp = AlterColumnOp
    ops_ops.DropColumnOp = DropColumnOp
    ops_ops.DropTableOp = DropTableOp
    ops_ops.MigrationScript = MigrationScript

    return ops, ops_ops


def test_utils_module_import():
    utils = importlib.import_module("sqlmeta.utils")
    assert utils.__all__ == []


def test_adapters_init_without_dependencies():
    dummy_sqlalchemy = types.ModuleType("sqlmeta.adapters.sqlalchemy")
    dummy_pydantic = types.ModuleType("sqlmeta.adapters.pydantic")
    dummy_alembic = types.ModuleType("sqlmeta.adapters.alembic")

    with temp_module("sqlmeta.adapters.sqlalchemy", dummy_sqlalchemy), temp_module(
        "sqlmeta.adapters.pydantic", dummy_pydantic
    ), temp_module("sqlmeta.adapters.alembic", dummy_alembic):
        adapters = reload_module("sqlmeta.adapters")
        assert adapters.__all__ == []


def test_adapters_init_with_stubs():
    sa_module, schema_module = build_stub_sqlalchemy()
    pydantic_module = build_stub_pydantic()
    ops_module, ops_ops_module = build_stub_alembic()

    with temp_module("sqlalchemy", sa_module), temp_module(
        "sqlalchemy.schema", schema_module
    ), temp_module("pydantic", pydantic_module), temp_module(
        "alembic.operations", ops_module
    ), temp_module(
        "alembic.operations.ops", ops_ops_module
    ):
        adapters = reload_module("sqlmeta.adapters")
        assert "to_sqlalchemy" in adapters.__all__
        assert "to_pydantic" in adapters.__all__
        assert "generate_operations" in adapters.__all__

