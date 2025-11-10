import pytest

from sqlmeta.base import (
    ConstraintType,
    SqlColumn,
    SqlConstraint,
    SqlObject,
    SqlObjectType,
)


class DummyObject(SqlObject):
    """Concrete subclass to exercise SqlObject behaviour."""

    def __init__(self, name: str, object_type="table", schema=None, dialect=None):
        super().__init__(name, object_type, schema, dialect)


def test_sqlobject_initialization_and_equality():
    obj_enum = DummyObject("users", SqlObjectType.TABLE, schema="public", dialect="postgresql")
    obj_str = DummyObject("users", "table", schema="PUBLIC", dialect="PostgreSQL")
    obj_other = DummyObject("orders", SqlObjectType.TABLE)

    assert obj_enum == obj_str
    assert obj_enum != obj_other
    assert obj_enum != "users"  # Non SqlObject comparison
    assert hash(obj_enum) == hash(obj_str)


@pytest.mark.parametrize(
    "dialect,identifier,expected",
    [
        ("postgresql", "Users", '"Users"'),
        ("oracle", "TeSt", '"TeSt"'),
        ("mysql", "col", "`col`"),
        ("mariadb", "col", "`col`"),
        ("sqlserver", "col", "[col]"),
        (None, "plain", "plain"),
        ("unknown", "noop", "noop"),
    ],
)
def test_format_identifier_various_dialects(dialect, identifier, expected):
    obj = DummyObject("dummy", dialect=dialect)
    assert obj.format_identifier(identifier) == expected


def test_sqlobject_compare_with_defaults_handles_mismatches():
    obj1 = DummyObject("users", SqlObjectType.TABLE, schema="public")
    obj2 = DummyObject("USERS", SqlObjectType.VIEW, schema="PUBLIC")

    diff = obj1.compare_with_defaults(obj2)
    assert diff["error"] == "Cannot compare objects of different types"


def test_sqlobject_compare_with_defaults_detects_name_schema_changes():
    obj1 = DummyObject("users", SqlObjectType.TABLE, schema="public")
    obj2 = DummyObject("accounts", SqlObjectType.TABLE, schema="finance")

    diff = obj1.compare_with_defaults(obj2)
    assert diff["name"] == {"self": "users", "other": "accounts"}
    assert diff["schema"] == {"self": "public", "other": "finance"}


def test_sqlobject_explicit_property_tracking():
    obj = DummyObject("users", SqlObjectType.TABLE)
    assert not obj.is_property_explicit("tablespace")
    obj.mark_property_explicit("tablespace")
    assert obj.is_property_explicit("tablespace")


def test_sqlcolumn_behaviour():
    column = SqlColumn(
        "ID",
        "INTEGER",
        is_nullable=False,
        default_value="1",
        is_primary_key=True,
        is_unique=True,
    )
    same = SqlColumn("id", "integer")

    assert "NOT NULL" in str(column)
    assert column == same
    assert hash(column) == hash(same)

    column.mark_property_explicit("nullable")
    assert column.is_property_explicit("nullable")
    assert not column.is_property_explicit("default_value")


def test_sqlconstraint_behaviour_and_string_types():
    constraint = SqlConstraint(
        "primary key",
        name="pk_users",
        column_names=["id"],
        dialect="postgresql",
    )
    same = SqlConstraint(ConstraintType.PRIMARY_KEY, name="PK_USERS", column_names=["ID"])
    other = SqlConstraint("unique", column_names=["email"])

    assert constraint.constraint_type is ConstraintType.PRIMARY_KEY
    assert str(constraint) == "PRIMARY KEY pk_users (id)"
    assert constraint == same
    assert constraint != other
    assert hash(constraint) == hash(same)

    constraint.mark_property_explicit("column_names")
    assert constraint.is_property_explicit("column_names")
    assert not constraint.is_property_explicit("reference_table")


def test_sqlconstraint_foreign_key_with_defaults():
    constraint = SqlConstraint(
        "foreign key",
        name="fk_orders_users",
        column_names=["user_id"],
        reference_table="users",
        reference_columns=["id"],
    )
    assert constraint.reference_schema is None
    assert "FOREIGN KEY" in str(constraint)

