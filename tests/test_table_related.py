import copy

import pytest

from sqlmeta import (
    ConstraintType,
    Parameter,
    Procedure,
    SqlColumn,
    SqlConstraint,
    Table,
)
from sqlmeta.objects.index import Index
from sqlmeta.objects.partition import Partition
from sqlmeta.objects.sequence import Sequence
from sqlmeta.objects.trigger import Trigger
from sqlmeta.objects.view import View


def make_column(name: str, data_type: str, **kwargs) -> SqlColumn:
    column = SqlColumn(name, data_type, **kwargs)
    return column


def make_constraint(constraint_type, **kwargs) -> SqlConstraint:
    return SqlConstraint(constraint_type=constraint_type, **kwargs)


def test_table_create_statement_with_constraints_and_tablespace():
    columns = [
        make_column("id", "INTEGER", is_nullable=False, is_primary_key=True, default_value="1"),
        make_column("email", "VARCHAR(255)", is_nullable=False),
        make_column("created_at", "TIMESTAMP", default_value="CURRENT_TIMESTAMP"),
    ]

    pk = make_constraint(
        ConstraintType.PRIMARY_KEY,
        name="pk_users",
        column_names=["id"],
    )
    fk = make_constraint(
        ConstraintType.FOREIGN_KEY,
        name="fk_users_org",
        column_names=["org_id"],
        reference_table="organizations",
        reference_columns=["id"],
    )
    fk.reference_schema = "admin"
    unique = make_constraint(ConstraintType.UNIQUE, name="uq_users_email", column_names=["email"])
    check = make_constraint(
        ConstraintType.CHECK,
        name="chk_users_email",
        column_names=["email like '%@example.com'"],
    )

    table = Table(
        name="users",
        schema="public",
        columns=columns,
        constraints=[pk, fk, unique, check],
        tablespace="userspace",
        dialect="postgresql",
    )

    ddl = table.create_statement
    assert 'CONSTRAINT "pk_users" PRIMARY KEY ("id")' in ddl
    assert 'REFERENCES "admin"."organizations"' in ddl
    assert "TABLESPACE userspace" in ddl
    assert 'CONSTRAINT "chk_users_email" CHECK (email like \'%@example.com\')' in ddl


def test_table_create_statement_temporary_variants():
    oracle_table = Table("temp_data", temporary=True, dialect="oracle")
    assert oracle_table.create_statement.startswith("CREATE GLOBAL TEMPORARY TABLE")

    sqlserver_temp = Table("session_data", temporary=True, dialect="sqlserver")
    assert "CREATE TABLE #session_data" in sqlserver_temp.create_statement

    mysql_temp = Table("cache", temporary=True, dialect="mysql")
    assert mysql_temp.create_statement.startswith("CREATE TEMPORARY TABLE")


def test_table_create_statement_sqlserver_storage_options():
    table = Table(
        "audit",
        columns=[make_column("id", "INT")],
        dialect="sqlserver",
        filegroup="PRIMARY",
        memory_optimized=True,
        system_versioned=True,
        history_table="audit_history",
        history_schema="dbo",
    )
    ddl = table.create_statement
    assert "ON [PRIMARY]" in ddl
    assert "MEMORY_OPTIMIZED = ON" in ddl
    assert "SYSTEM_VERSIONING = ON (HISTORY_TABLE = [dbo].[audit_history])" in ddl

    table_custom_fg = Table(
        "metrics",
        columns=[make_column("id", "INT")],
        dialect="sqlserver",
        filegroup="fg_metrics",
    )
    assert "ON [fg_metrics]" in table_custom_fg.create_statement


def test_table_drop_statement_by_dialect():
    table = Table("users", schema="public")
    assert table.drop_statement == "DROP TABLE IF EXISTS public.users CASCADE"

    oracle_table = Table("users", schema="ADMIN", dialect="oracle")
    assert oracle_table.drop_statement == 'DROP TABLE "ADMIN"."users" CASCADE CONSTRAINTS'

    mysql_table = Table("users", dialect="mysql")
    assert mysql_table.drop_statement == "DROP TABLE IF EXISTS `users`"


def test_table_column_and_constraint_management():
    table = Table("users", columns=[make_column("id", "INT")])
    table.add_column(make_column("email", "VARCHAR(100)", is_nullable=False))
    assert table.get_column("EMAIL").data_type == "VARCHAR(100)"

    pk = make_constraint(ConstraintType.PRIMARY_KEY, column_names=["id"])
    table.add_constraint(pk)
    assert table.get_primary_key() == pk
    assert table.get_unique_constraints() == []

    fk = make_constraint(
        ConstraintType.FOREIGN_KEY,
        column_names=["org_id"],
        reference_table="organizations",
        reference_columns=["id"],
    )
    table.add_constraint(fk)
    assert table.get_foreign_keys() == [fk]


def test_table_compare_with_defaults_reports_differences():
    base_columns = [
        make_column("id", "INT", is_nullable=False),
        make_column("name", "VARCHAR(50)"),
    ]
    for col in base_columns:
        col.mark_property_explicit("nullable")
    expected = Table(
        "users",
        columns=copy.deepcopy(base_columns),
        constraints=[make_constraint(ConstraintType.PRIMARY_KEY, column_names=["id"])],
        temporary=True,
        tablespace="tblspace1",
        dialect="sqlserver",
        filegroup="PRIMARY",
    )

    actual = Table(
        "users",
        columns=[make_column("id", "INT"), make_column("name", "VARCHAR(60)")],
        constraints=[],
        temporary=False,
        dialect="sqlserver",
        filegroup="FG2",
    )
    actual.memory_optimized = True
    actual.mark_property_explicit("memory_optimized")

    diff = expected.compare_with_defaults(actual)

    assert diff["temporary"] == {"self": True, "other": False}
    assert diff["column_differences"]["name"]["data_type"] == {
        "self": "VARCHAR(50)",
        "other": "VARCHAR(60)",
    }
    assert "filegroup" in diff
    assert diff["memory_optimized"] == {"self": False, "other": True}


def test_table_to_from_dict_roundtrip():
    column = make_column(
        "amount",
        "NUMERIC(10,2)",
        is_nullable=False,
        default_value="0",
        is_identity=True,
        computed_expression=None,
    )
    column.mark_property_explicit("default_value")
    constraint = make_constraint(
        ConstraintType.CHECK,
        name="chk_amount_positive",
        column_names=["amount > 0"],
    )
    constraint.mark_property_explicit("columns")
    table = Table(
        "payments",
        schema="finance",
        columns=[column],
        constraints=[constraint],
        comment="Payment records",
        tablespace="fastspace",
        dialect="postgresql",
    )
    table.mark_property_explicit("tablespace")

    data = table.to_dict()
    restored = Table.from_dict(data)
    assert restored == table
    assert restored.is_property_explicit("tablespace")


def test_view_create_and_drop_statements():
    view = View(
        "active_users",
        schema="public",
        query="SELECT * FROM users WHERE active = TRUE",
        columns=["id", "email"],
        dialect="postgresql",
        materialized=True,
        unlogged=True,
        algorithm="MERGE",
        sql_security="DEFINER",
        definer="admin@localhost",
    )
    stmt = view.create_statement
    assert stmt.startswith("CREATE UNLOGGED MATERIALIZED VIEW")
    assert "UNLOGGED MATERIALIZED VIEW" in stmt
    assert view.drop_statement == 'DROP MATERIALIZED VIEW IF EXISTS "public"."active_users"'

    oracle_view = View(
        "customer_v",
        schema="sales",
        query="SELECT * FROM customers",
        dialect="oracle",
        force=True,
    )
    assert "FORCE" in oracle_view.create_statement
    assert oracle_view.drop_statement == 'DROP VIEW "sales"."customer_v"'


def test_sequence_statements():
    seq = Sequence(
        "order_seq",
        schema="public",
        start_with=10,
        increment_by=5,
        min_value=10,
        max_value=1000,
        cycle=True,
        cache=20,
        dialect="postgresql",
        temp=True,
    )
    stmt = seq.create_statement
    assert "START WITH 10" in stmt
    assert "INCREMENT BY 5" in stmt
    assert "CYCLE" in stmt
    assert "TEMPORARY" in stmt
    assert seq.drop_statement == 'DROP SEQUENCE IF EXISTS "public"."order_seq"'


def test_index_create_and_drop_statements():
    index = Index(
        name="idx_users_email",
        table_name="users",
        columns=["email"],
        schema="public",
        include_columns=["name"],
        condition="email IS NOT NULL",
        sort_directions=["ASC"],
        dialect="postgresql",
        concurrently=True,
    )
    stmt = index.create_statement
    assert "CONCURRENTLY" in stmt
    assert "INCLUDE (\"name\")" in stmt
    assert "WHERE email IS NOT NULL" in stmt
    assert index.drop_statement == 'DROP INDEX IF EXISTS "public"."idx_users_email"'

    mysql_index = Index(
        name="idx_users_fulltext",
        table_name="users",
        columns=["bio"],
        type="FULLTEXT",
        dialect="mysql",
        online=True,
    )
    assert mysql_index.create_statement.startswith("CREATE ONLINE FULLTEXT INDEX")


def test_trigger_create_statement_variants():
    trigger = Trigger(
        name="tr_users_notify",
        table_name="users",
        schema="public",
        timing="AFTER",
        events=["INSERT", "UPDATE"],
        orientation="ROW",
        definition="BEGIN\n  PERFORM notify_user();\nEND;",
        dialect="postgresql",
    )
    stmt = trigger.create_statement
    assert "FOR EACH ROW" in stmt

    mysql_trigger = Trigger(
        name="tr_users_log",
        table_name="users",
        dialect="mysql",
        definer="admin@localhost",
        timing="BEFORE",
        events=["INSERT"],
        definition="BEGIN SET NEW.created_at = NOW(); END;",
    )
    assert "DEFINER = admin@localhost" in mysql_trigger.create_statement
    assert str(mysql_trigger) == "Trigger tr_users_log on users"


def test_procedure_create_function_and_drop():
    params = [
        Parameter("user_id", "INT", direction="IN"),
        Parameter("include_inactive", "BOOLEAN", direction="IN", default_value="FALSE"),
    ]
    proc = Procedure(
        "refresh_user_stats",
        schema="public",
        parameters=params,
        body="UPDATE stats SET refreshed_at = NOW();",
        language="plpgsql",
        dialect="postgresql",
        comment="Recalculate user statistics",
    )
    stmt = proc.create_statement
    assert "LANGUAGE plpgsql" in stmt
    assert proc.drop_statement == 'DROP PROCEDURE IF EXISTS "public"."refresh_user_stats"'

    func = Procedure(
        "calculate_tax",
        schema="finance",
        parameters=[Parameter("amount", "NUMERIC", direction="IN")],
        body="RETURN amount * 0.2;",
        is_function=True,
        return_type="NUMERIC",
        dialect="sqlserver",
    )
    stmt_func = func.create_statement
    assert "RETURNS NUMERIC" in stmt_func
    assert "BEGIN" in stmt_func
    assert func.drop_statement == "DROP FUNCTION IF EXISTS [finance].[calculate_tax]"


def test_partition_serialization_and_display():
    sub = Partition(
        "p2024q1",
        table="orders",
        partition_method="range",
        partition_description="VALUES LESS THAN ('2024-04-01')",
    )
    partition = Partition(
        "p2024",
        table="orders",
        partition_method="range",
        partition_expression="order_date",
        partition_description="VALUES LESS THAN ('2024-07-01')",
        subpartitions=[sub],
        schema="sales",
        tablespace="fastspace",
        storage="flash",
    )
    stmt = partition.create_statement
    assert "SUBPARTITION" in stmt
    assert "with 1 subpartitions" in str(partition)

    data = partition.to_dict()
    restored = Partition.from_dict(data)
    assert restored == partition
    assert restored.metadata["storage"] == "flash"

