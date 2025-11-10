from sqlmeta.comparison.diff_models import (
    ColumnDiff,
    ConstraintDiff,
    DatabaseLinkDiff,
    DiffResult,
    EventDiff,
    ExtensionDiff,
    ForeignDataWrapperDiff,
    ForeignServerDiff,
    FunctionDiff,
    IndexDiff,
    LinkedServerDiff,
    ModuleDiff,
    PackageDiff,
    ProcedureDiff,
    SchemaDiff,
    SequenceDiff,
    SynonymDiff,
    TableDiff,
    TriggerDiff,
    UserDefinedTypeDiff,
    ViewDiff,
    DiffSeverity,
)


def test_base_diff_result_summary_and_str():
    diff = DiffResult("users", object_type="table")
    assert diff.get_summary().endswith("MATCH")
    assert str(diff) == "table 'users': No differences"

    diff.has_diffs = True
    diff.severity = DiffSeverity.ERROR
    assert "Differences" in str(diff)


def test_column_diff_and_to_dict():
    diff = ColumnDiff(
        object_name="users.email",
        column_name="email",
        data_type_diff=("VARCHAR(100)", "VARCHAR(255)"),
        nullable_diff=(False, True),
        default_diff=("''", None),
        identity_diff=(False, True),
        computed_diff=("price * qty", None),
    )
    assert diff.has_diffs
    assert diff.severity == DiffSeverity.ERROR
    data = diff.to_dict()
    assert data["differences"]["data_type"]["expected"] == "VARCHAR(100)"
    assert "type: VARCHAR(100) → VARCHAR(255)" in str(diff)


def test_constraint_diff_and_str():
    diff = ConstraintDiff(
        object_name="users_pk",
        constraint_name="users_pk",
        constraint_type="PRIMARY KEY",
        columns_diff=(["id"], ["user_id"]),
        references_diff=(("users", ["id"]), ("users", ["user_id"])),
        check_clause_diff=("price > 0", "price >= 0"),
    )
    assert diff.has_diffs
    assert diff.severity == DiffSeverity.ERROR
    data = diff.to_dict()
    assert data["differences"]["columns"]["actual"] == ["user_id"]
    assert "columns: ['id'] → ['user_id']" in str(diff)


def test_table_diff_counts_and_to_dict():
    column_diff = ColumnDiff(
        object_name="users.email",
        column_name="email",
        data_type_diff=("VARCHAR(100)", "VARCHAR(200)"),
    )
    constraint_diff = ConstraintDiff(
        object_name="users_pk",
        constraint_name="users_pk",
        constraint_type="PRIMARY KEY",
        columns_diff=(["id"], ["user_id"]),
    )
    diff = TableDiff(
        object_name="users",
        missing_columns=["created_at"],
        extra_columns=["deprecated"],
        modified_columns=[column_diff],
        missing_constraints=["users_pk"],
        extra_constraints=["users_old_pk"],
        modified_constraints=[constraint_diff],
        missing_indexes=["idx_old"],
        extra_indexes=["idx_new"],
        temporary_changed=True,
        filegroup_changed=True,
        memory_optimized_changed=True,
    )
    assert diff.has_diffs
    assert diff.severity == DiffSeverity.ERROR
    counts = diff.get_diff_count()
    assert counts["missing_columns"] == 1
    assert "missing column(s)" in str(diff)
    data = diff.to_dict()
    assert data["diff_count"]["missing_columns"] == 1


def test_view_diff_flags():
    diff = ViewDiff(
        object_name="active_users",
        definition_changed=True,
        materialized_changed=(False, True),
        unlogged_changed=(False, True),
        algorithm_changed=("MERGE", "TEMPTABLE"),
        sql_security_changed=("DEFINER", "INVOKER"),
        definer_changed=("admin", "app"),
    )
    assert diff.has_diffs
    assert diff.severity == DiffSeverity.WARNING
    data = diff.to_dict()
    assert data["definition_changed"]


def test_index_diff_properties():
    diff = IndexDiff(
        object_name="idx_users_email",
        index_name="idx_users_email",
        columns_changed=True,
        uniqueness_changed=(False, True),
        type_changed=("btree", "hash"),
        online_changed=(False, True),
        concurrently_changed=(False, True),
        tablespace_changed=("main", "fastspace"),
    )
    assert diff.has_diffs
    assert diff.severity == DiffSeverity.WARNING


def test_sequence_diff_properties():
    diff = SequenceDiff(
        object_name="user_seq",
        sequence_name="user_seq",
        start_value_changed=(1, 10),
        increment_changed=(1, 2),
        min_value_changed=(1, 0),
        max_value_changed=(1000, 500),
        cycle_changed=(False, True),
        temp_changed=(False, True),
    )
    assert diff.has_diffs
    assert diff.severity == DiffSeverity.INFO


def test_trigger_diff_properties():
    diff = TriggerDiff(
        object_name="tr_users",
        trigger_name="tr_users",
        table_name="users",
        timing_changed=("BEFORE", "AFTER"),
        event_changed=(["INSERT"], ["UPDATE"]),
        constraint_trigger_changed=(False, True),
        definer_changed=("admin", "app"),
        definition_changed=True,
        enabled_changed=(True, False),
    )
    assert diff.has_diffs
    assert diff.severity == DiffSeverity.WARNING
    data = diff.to_dict()
    assert data["definition_changed"]


def test_procedure_and_function_diff():
    proc_diff = ProcedureDiff(
        object_name="refresh_stats",
        procedure_name="refresh_stats",
        definition_changed=True,
        parameters_changed=True,
        expected_parameters=["id INT"],
        actual_parameters=["user_id INT"],
    )
    assert proc_diff.severity == DiffSeverity.ERROR

    func_diff = FunctionDiff(
        object_name="calc_tax",
        function_name="calc_tax",
        definition_changed=True,
        parameters_changed=False,
        return_type_changed=("NUMERIC", "FLOAT"),
    )
    assert func_diff.severity == DiffSeverity.ERROR


def test_synonym_package_module_and_type_diffs():
    syn_diff = SynonymDiff(
        object_name="syn",
        synonym_name="syn",
        target_changed=("table_a", "table_b"),
        target_schema_changed=("schema1", "schema2"),
        target_database_changed=("db1", "db2"),
        db_link_changed=("link1", "link2"),
    )
    assert syn_diff.severity == DiffSeverity.WARNING

    pkg_diff = PackageDiff(
        object_name="pkg",
        package_name="pkg",
        spec_changed=True,
        body_changed=True,
    )
    assert pkg_diff.severity == DiffSeverity.WARNING

    mod_diff = ModuleDiff(
        object_name="mod",
        module_name="mod",
        definition_changed=True,
    )
    assert mod_diff.severity == DiffSeverity.WARNING

    type_diff = UserDefinedTypeDiff(
        object_name="address_type",
        type_name="address_type",
        type_category_changed=("COMPOSITE", "ENUM"),
        base_type_changed=("TEXT", "VARCHAR"),
        attributes_changed=True,
        enum_values_changed=True,
        definition_changed=True,
    )
    assert type_diff.severity == DiffSeverity.ERROR


def test_connection_related_diffs():
    db_link_diff = DatabaseLinkDiff(
        object_name="orders_link",
        link_name="orders_link",
        host_changed=("host1", "host2"),
        username_changed=("user1", "user2"),
        public_changed=(False, True),
        expected_host="host1",
        actual_host="host2",
    )
    assert db_link_diff.severity == DiffSeverity.ERROR

    linked_server_diff = LinkedServerDiff(
        object_name="reports",
        server_name="reports",
        product_changed=("SQL Server", "Oracle"),
        provider_changed=("SQLNCLI", "OraOLEDB"),
        data_source_changed=("ds1", "ds2"),
        catalog_changed=("cat1", "cat2"),
        username_changed=("user1", "user2"),
    )
    assert linked_server_diff.severity == DiffSeverity.ERROR


def test_foreign_data_and_server_diffs():
    fdw_diff = ForeignDataWrapperDiff(
        object_name="fdw",
        fdw_name="fdw",
        handler_changed=("handler1", "handler2"),
        validator_changed=("validator1", "validator2"),
        options_changed=({"option": "a"}, {"option": "b"}),
    )
    assert fdw_diff.severity == DiffSeverity.WARNING

    foreign_server_diff = ForeignServerDiff(
        object_name="server",
        server_name="server",
        fdw_changed=("fdw1", "fdw2"),
        host_changed=("host1", "host2"),
        port_changed=(5432, 5433),
        dbname_changed=("db1", "db2"),
        options_changed=({"ssl": "on"}, {"ssl": "off"}),
    )
    assert foreign_server_diff.severity == DiffSeverity.ERROR


def test_extension_event_and_schema_diff():
    extension_diff = ExtensionDiff(
        object_name="pg_stat_statements",
        extension_name="pg_stat_statements",
        version_changed=("1.8", "1.9"),
        schema_changed=("public", "monitoring"),
        expected_version="1.8",
        actual_version="1.9",
    )
    assert extension_diff.severity == DiffSeverity.WARNING

    event_diff = EventDiff(
        object_name="cleanup",
        event_name="cleanup",
        definition_changed=True,
        schedule_changed=("EVERY 1 HOUR", "EVERY 2 HOUR"),
        enabled_changed=(True, False),
        event_type_changed=("ONE TIME", "RECURRING"),
    )
    assert event_diff.severity == DiffSeverity.WARNING

    table_diff = TableDiff(
        object_name="users",
        missing_columns=["a"],
    )
    schema_diff = SchemaDiff(
        object_name="public",
        schema_name="public",
        missing_tables=["users"],
        extra_tables=["sessions"],
        modified_tables=[table_diff],
        missing_views=["v1"],
        extra_views=["v2"],
        modified_views=[
            ViewDiff(
                object_name="v1",
                definition_changed=True,
            )
        ],
    )
    assert schema_diff.has_diffs
    assert schema_diff.severity == DiffSeverity.ERROR
    assert schema_diff.get_total_diff_count() >= 3
    assert "missing table" in str(schema_diff)

