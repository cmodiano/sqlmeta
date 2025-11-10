from sqlmeta.comparison.comparator import (
    ObjectComparator,
    _extract_base_identity_type,
    _is_system_generated_constraint_name,
)
from sqlmeta.comparison.type_normalizer import DataTypeNormalizer
from sqlmeta import ConstraintType, SqlColumn, SqlConstraint, Table
from sqlmeta.objects.database_link import DatabaseLink
from sqlmeta.objects.event import Event
from sqlmeta.objects.extension import Extension
from sqlmeta.objects.foreign_data_wrapper import ForeignDataWrapper
from sqlmeta.objects.foreign_server import ForeignServer
from sqlmeta.objects.index import Index
from sqlmeta.objects.linked_server import LinkedServer
from sqlmeta.objects.module import Module
from sqlmeta.objects.package import Package
from sqlmeta.objects.procedure import Parameter, Procedure
from sqlmeta.objects.sequence import Sequence
from sqlmeta.objects.synonym import Synonym
from sqlmeta.objects.trigger import Trigger
from sqlmeta.objects.user_defined_type import UserDefinedType
from sqlmeta.objects.view import View


def make_column(name: str, data_type: str, **kwargs) -> SqlColumn:
    col = SqlColumn(name, data_type, **kwargs)
    return col


def make_constraint(constraint_type, **kwargs) -> SqlConstraint:
    return SqlConstraint(constraint_type=constraint_type, **kwargs)


def test_system_generated_constraint_detection():
    assert _is_system_generated_constraint_name("SYS_C00123")
    assert _is_system_generated_constraint_name("PK__users__ABCD1234")
    assert not _is_system_generated_constraint_name("pk_users")


def test_extract_base_identity_type_variations():
    assert _extract_base_identity_type("SERIAL", "postgresql") == "INTEGER"
    assert _extract_base_identity_type("BIGSERIAL", "postgresql") == "BIGINT"
    assert _extract_base_identity_type("NUMBER GENERATED ALWAYS AS IDENTITY", "oracle") == "NUMBER"
    assert _extract_base_identity_type("INT IDENTITY(1,1)", "sqlserver") == "INT"


def test_normalize_helpers():
    comparator = ObjectComparator(DataTypeNormalizer())
    assert comparator._normalize_default_value("'text'") == "text"
    assert comparator._normalize_default_value("((getdate()))") == "(getdate())"
    assert comparator._normalize_default_value("true") == "TRUE"
    assert comparator._normalize_default_value("FALSE") == "FALSE"
    assert comparator._normalize_default_value("CURRENT") == "CURRENT_TIMESTAMP"
    assert comparator._normalize_default_value("current_date") == "CURRENT_DATE"

    expr = comparator._normalize_expression('"price" * "quantity"')
    assert expr == "PRICE * QUANTITY"
    view_def = comparator._normalize_view_definition(
        """
        SELECT * FROM users
        -- comment
        WHERE active = TRUE
        """
    )
    assert "SELECT * FROM USERS WHERE ACTIVE = TRUE" in view_def

    params = comparator._normalize_parameters(
        [Parameter("id", "INT"), Parameter("name", "VARCHAR")]
    )
    assert params == "ID INT,NAME VARCHAR"
    pkg_code = comparator._normalize_package_code(
        """
        PROCEDURE refresh_sales;
        -- comment
        END;
        """
    )
    assert "PROCEDURE REFRESH_SALES;" in pkg_code
    module_code = comparator._normalize_module_code(
        """
        CREATE MODULE mod1;
        -- comment
        END MODULE;
        """
    )
    assert "CREATE MODULE MOD1;" in module_code


def test_compare_tables_identifies_differences():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected = Table(
        "users",
        schema="public",
        columns=[
            make_column("id", "INT", is_nullable=False, is_primary_key=True),
            make_column("status", "VARCHAR(10)", is_nullable=False, default_value="'active'"),
        ],
        constraints=[
            make_constraint(ConstraintType.PRIMARY_KEY, column_names=["id"], name="pk_users"),
            make_constraint(
                ConstraintType.CHECK,
                column_names=["status IN ('active','disabled')"],
                name="chk_status",
            ),
        ],
        temporary=True,
    )
    expected.columns[1].mark_property_explicit("default_value")
    expected.columns[1].mark_property_explicit("nullable")

    actual = Table(
        "users",
        schema="public",
        columns=[
            make_column("id", "INT", is_nullable=False, is_primary_key=True),
            make_column("status", "VARCHAR(12)", is_nullable=True, default_value="'ACTIVE'"),
            make_column("email", "VARCHAR(255)"),
        ],
        constraints=[
            make_constraint(ConstraintType.PRIMARY_KEY, column_names=["id"], name="PK_USERS"),
        ],
    )
    actual.columns[1].mark_property_explicit("default_value")
    actual.columns[1].mark_property_explicit("nullable")

    diff = comparator.compare_tables(expected, actual, dialect="postgresql")
    assert diff.has_diffs
    assert "status" in [c.object_name for c in diff.modified_columns]
    assert "email" in diff.extra_columns
    assert diff.temporary_changed


def test_compare_tables_derived_table_skips_columns():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected = Table("audit", columns=[make_column("id", "INT")])
    expected.derived_from = "CTAS"
    actual = Table("audit", columns=[make_column("id", "INT"), make_column("extra", "TEXT")])
    diff = comparator.compare_tables(expected, actual)
    assert not diff.missing_columns and not diff.extra_columns


def test_compare_tables_sqlserver_features():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected = Table(
        "events",
        columns=[make_column("id", "INT")],
        dialect="sqlserver",
        filegroup="FG1",
        memory_optimized=False,
        system_versioned=True,
        history_table="events_history",
        history_schema="dbo",
    )
    expected.mark_property_explicit("filegroup")
    expected.mark_property_explicit("system_versioned")

    actual = Table(
        "events",
        columns=[make_column("id", "INT")],
        dialect="sqlserver",
        filegroup="PRIMARY",
        memory_optimized=True,
        system_versioned=True,
        history_table="events_hist",
        history_schema="dbo",
    )
    actual.mark_property_explicit("memory_optimized")
    actual.mark_property_explicit("system_versioned")

    diff = comparator.compare_tables(expected, actual, dialect="sqlserver")
    assert diff.filegroup_changed
    assert diff.memory_optimized_changed
    assert diff.history_table_changed


def test_compare_tables_db2_features():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected = Table("logs", columns=[make_column("id", "INT")], dialect="db2")
    actual = Table("logs", columns=[make_column("id", "INT")], dialect="db2")
    expected.compress = True
    expected.compress_type = "static"
    expected.mark_property_explicit("compress")
    expected.mark_property_explicit("compress_type")
    expected.logged = True
    expected.mark_property_explicit("logged")
    expected.organize_by = "row"
    actual.organize_by = "column"
    actual.mark_property_explicit("organize_by")
    actual.compress = False
    actual.mark_property_explicit("compress")
    actual.logged = False
    actual.mark_property_explicit("logged")

    diff = comparator.compare_tables(expected, actual, dialect="db2")
    assert diff.compress_changed
    assert diff.organize_by_changed
    assert diff.logged_changed

    actual.compress = True
    actual.compress_type = "adaptive"
    actual.mark_property_explicit("compress_type")
    diff2 = comparator.compare_tables(expected, actual, dialect="db2")
    assert diff2.compress_type_changed


def test_compare_views_indexes_sequences_and_triggers():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected_view = View(
        "active_users",
        query="SELECT id FROM users WHERE active = TRUE",
        materialized=True,
        unlogged=True,
        dialect="postgresql",
        algorithm="MERGE",
        sql_security="DEFINER",
        definer="admin",
        force=True,
    )
    actual_view = View(
        "active_users",
        query="SELECT id FROM users WHERE active = FALSE",
        materialized=False,
        unlogged=False,
        dialect="postgresql",
        algorithm="TEMPTABLE",
        sql_security="INVOKER",
        definer="app",
        force=False,
    )
    view_diff = comparator.compare_views(expected_view, actual_view, dialect="postgresql")
    assert view_diff and view_diff.definition_changed

    expected_index = Index(
        "idx_users_email",
        table_name="users",
        columns=["email"],
        unique=True,
        type="BTREE",
        dialect="postgresql",
        concurrently=True,
    )
    actual_index = Index(
        "idx_users_email",
        table_name="users",
        columns=["EMAIL", "id"],
        unique=False,
        type="HASH",
        dialect="postgresql",
        concurrently=False,
    )
    index_diff = comparator.compare_indexes(expected_index, actual_index, dialect="postgresql")
    assert index_diff and index_diff.columns_changed

    expected_seq = Sequence(
        "user_seq",
        start_with=1,
        increment_by=1,
        cycle=False,
        dialect="postgresql",
        temp=True,
    )
    actual_seq = Sequence(
        "user_seq",
        start_with=5,
        increment_by=2,
        cycle=True,
        dialect="postgresql",
        temp=False,
    )
    seq_diff = comparator.compare_sequences(expected_seq, actual_seq, dialect="postgresql")
    assert seq_diff and seq_diff.start_value_changed

    expected_trigger = Trigger(
        "tr_users",
        table_name="users",
        timing="BEFORE",
        events=["INSERT"],
        definition="BEGIN SET NEW.created_at = NOW(); END;",
        enabled=True,
        dialect="postgresql",
    )
    actual_trigger = Trigger(
        "tr_users",
        table_name="users",
        timing="AFTER",
        events=["INSERT", "UPDATE"],
        definition="BEGIN SET NEW.created_at = NOW(); END;",
        enabled=False,
        dialect="postgresql",
        definer="admin@localhost",
    )
    trig_diff = comparator.compare_triggers(expected_trigger, actual_trigger, dialect="postgresql")
    assert trig_diff and trig_diff.timing_changed


def test_compare_procedure_function_and_synonym():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected_proc = Procedure(
        "refresh_stats",
        parameters=[Parameter("id", "INT")],
        body="BEGIN NULL; END;",
        dialect="oracle",
    )
    actual_proc = Procedure(
        "refresh_stats",
        parameters=[Parameter("user_id", "INT")],
        body="BEGIN NULL; END;",
        dialect="oracle",
    )
    proc_diff = comparator.compare_procedures(expected_proc, actual_proc, dialect="oracle")
    assert proc_diff and proc_diff.parameters_changed

    expected_func = Procedure(
        "calculate_tax",
        parameters=[Parameter("amount", "NUMERIC")],
        body="RETURN amount * 0.2;",
        is_function=True,
        return_type="NUMERIC",
        dialect="postgresql",
    )
    actual_func = Procedure(
        "calculate_tax",
        parameters=[Parameter("amount", "NUMERIC"), Parameter("rate", "NUMERIC")],
        body="RETURN amount * rate;",
        is_function=True,
        return_type="FLOAT",
        dialect="postgresql",
    )
    func_diff = comparator.compare_functions(expected_func, actual_func, dialect="postgresql")
    assert func_diff and func_diff.parameters_changed

    expected_syn = Synonym(
        "orders_syn",
        target_object="orders",
        target_schema="sales",
        target_database="analytics",
        db_link="remote",
        dialect="oracle",
    )
    actual_syn = Synonym(
        "orders_syn",
        target_object="orders_archive",
        target_schema="sales",
        target_database="analytics",
        db_link="remote",
        dialect="oracle",
    )
    syn_diff = comparator.compare_synonyms(expected_syn, actual_syn, dialect="oracle")
    assert syn_diff and syn_diff.target_changed


def test_compare_user_defined_types_and_packages():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected_udt = UserDefinedType(
        "status_type",
        type_category="ENUM",
        enum_values=["active", "disabled"],
    )
    actual_udt = UserDefinedType(
        "status_type",
        type_category="ENUM",
        enum_values=["active", "disabled", "pending"],
    )
    udt_diff = comparator.compare_user_defined_types(expected_udt, actual_udt, dialect="postgresql")
    assert udt_diff and udt_diff.enum_values_changed

    expected_pkg = Package(
        "sales_pkg",
        spec="AS PROCEDURE refresh_sales; END;",
        body="AS PROCEDURE refresh_sales IS BEGIN NULL; END; END;",
    )
    actual_pkg = Package(
        "sales_pkg",
        spec="AS PROCEDURE refresh_sales; END;",
        body="AS PROCEDURE refresh_sales IS BEGIN COMMIT; END; END;",
    )
    pkg_diff = comparator.compare_packages(expected_pkg, actual_pkg, dialect="oracle")
    assert pkg_diff and pkg_diff.body_changed

    expected_module = Module("audit_mod", definition="CREATE MODULE audit_mod; END MODULE;")
    actual_module = Module("audit_mod", definition="CREATE MODULE audit_mod; ALTER MODULE; END MODULE;")
    mod_diff = comparator.compare_modules(expected_module, actual_module, dialect="db2")
    assert mod_diff and mod_diff.definition_changed


def test_compare_extensions_events_and_connections():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected_ext = Extension("pg_trgm", version="1.6", schema="public")
    actual_ext = Extension("pg_trgm", version="1.7", schema="analytics")
    ext_diff = comparator.compare_extensions(expected_ext, actual_ext, dialect="postgresql")
    assert ext_diff and ext_diff.version_changed

    expected_event = Event(
        "cleanup",
        definition="DELETE FROM sessions;",
        schedule="EVERY 1 HOUR",
        enabled=True,
        event_type="ONE TIME",
    )
    actual_event = Event(
        "cleanup",
        definition="DELETE FROM sessions WHERE expired = TRUE;",
        schedule="EVERY 2 HOUR",
        enabled=False,
        event_type="RECURRING",
    )
    event_diff = comparator.compare_events(expected_event, actual_event, dialect="mysql")
    assert event_diff and event_diff.definition_changed

    expected_link = DatabaseLink("orders_link", host="db1", username="user1", public=False)
    actual_link = DatabaseLink("orders_link", host="db2", username="user2", public=True)
    link_diff = comparator.compare_database_links(expected_link, actual_link, dialect="oracle")
    assert link_diff and link_diff.host_changed

    expected_server = LinkedServer(
        "reports",
        product="SQL Server",
        provider="SQLNCLI",
        data_source="srv1",
        catalog="analytics",
    )
    actual_server = LinkedServer(
        "reports",
        product="Oracle",
        provider="OraOLEDB",
        data_source="srv2",
        catalog="dw",
    )
    linked_diff = comparator.compare_linked_servers(expected_server, actual_server, dialect="sqlserver")
    assert linked_diff and linked_diff.product_changed

    expected_fdw = ForeignDataWrapper("oracle_fdw", handler="handler1", validator="validator1", options={"a": "1"})
    actual_fdw = ForeignDataWrapper("oracle_fdw", handler="handler2", validator="validator2", options={"a": "2"})
    fdw_diff = comparator.compare_foreign_data_wrappers(expected_fdw, actual_fdw, dialect="postgresql")
    assert fdw_diff and fdw_diff.handler_changed

    expected_foreign_server = ForeignServer(
        "oracle_server",
        fdw_name="oracle_fdw",
        host="db.example.com",
        port=1521,
        dbname="SALES",
        options={"ssl": "on"},
    )
    actual_foreign_server = ForeignServer(
        "oracle_server",
        fdw_name="oracle_fdw",
        host="db2.example.com",
        port=1522,
        dbname="SALES",
        options={"ssl": "off"},
    )
    foreign_server_diff = comparator.compare_foreign_servers(
        expected_foreign_server, actual_foreign_server, dialect="postgresql"
    )
    assert foreign_server_diff and foreign_server_diff.host_changed


def test_compare_schemas_summarizes_changes():
    comparator = ObjectComparator(DataTypeNormalizer())
    table_expected = Table("users", columns=[make_column("id", "INT")])
    table_actual = Table("users", columns=[make_column("id", "INT"), make_column("email", "TEXT")])
    schema_diff = comparator.compare_schemas(
        expected_tables=[table_expected],
        actual_tables=[table_actual, Table("sessions", columns=[])],
    )
    assert schema_diff.has_diffs
    assert "sessions" in schema_diff.extra_tables


def test_compare_constraints_handles_duplicates_and_name_matching():
    comparator = ObjectComparator(DataTypeNormalizer())
    pk_expected = make_constraint(ConstraintType.PRIMARY_KEY, column_names=["id"], name="PK_USERS")
    unique_duplicate = make_constraint(ConstraintType.UNIQUE, column_names=["id"], name="SYS_UQ")
    fk_expected = make_constraint(
        ConstraintType.FOREIGN_KEY,
        column_names=["org_id"],
        reference_table="organizations",
        reference_columns=["id"],
        name="fk_users_org",
    )
    check_expected = make_constraint(
        ConstraintType.CHECK, column_names=["status IN ('active')"], name="chk_status"
    )
    unique_named_expected = make_constraint(
        ConstraintType.UNIQUE, column_names=["status"], name="uq_status"
    )
    actual_pk = make_constraint(ConstraintType.PRIMARY_KEY, column_names=["id"], name="PK_USERS")
    unique_actual = make_constraint(ConstraintType.UNIQUE, column_names=["id"], name="SYS_UQ")
    fk_actual = make_constraint(
        ConstraintType.FOREIGN_KEY,
        column_names=["org_id"],
        reference_table="ORG_TABLE",
        reference_columns=["ORG_ID"],
        name="fk_users_org",
    )
    check_actual = make_constraint(
        ConstraintType.CHECK, column_names=["status IN ('active','disabled')"], name="chk_status"
    )
    unique_named_actual = make_constraint(
        ConstraintType.UNIQUE, column_names=["state"], name="uq_status"
    )
    expected_constraints = [
        pk_expected,
        unique_duplicate,
        fk_expected,
        check_expected,
        unique_named_expected,
    ]
    actual_constraints = [actual_pk, unique_actual, fk_actual, check_actual, unique_named_actual]

    missing, extra, modified = comparator._compare_constraints(
        expected_constraints, actual_constraints, dialect="postgresql"
    )
    assert not missing
    assert not extra
    assert any(diff.constraint_name == "fk_users_org" for diff in modified)
    assert any(diff.constraint_name == "chk_status" for diff in modified)
    assert any(diff.constraint_name == "uq_status" for diff in modified)


def test_compare_column_details_with_identity_and_computed():
    comparator = ObjectComparator(DataTypeNormalizer())
    expected_col = SqlColumn(
        "id",
        "SERIAL",
        is_nullable=False,
        is_identity=True,
    )
    actual_col = SqlColumn(
        "id",
        "INTEGER",
        is_nullable=True,
        is_identity=True,
        default_value="(nextval('id_seq'))",
    )
    diff = comparator._compare_column_details(expected_col, actual_col, dialect="postgresql")
    assert diff is None  # identity columns ignore nullable/default differences

    expected_comp = SqlColumn(
        "total",
        "INTEGER",
        is_computed=True,
        computed_expression="price * quantity",
    )
    actual_comp = SqlColumn(
        "total",
        "INTEGER",
        is_computed=True,
        computed_expression=None,
        default_value="price + quantity",
    )
    comp_diff = comparator._compare_column_details(expected_comp, actual_comp, dialect="postgresql")
    assert comp_diff and comp_diff.computed_diff

