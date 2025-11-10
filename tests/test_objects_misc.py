from sqlmeta.objects.database_link import DatabaseLink
from sqlmeta.objects.event import Event
from sqlmeta.objects.extension import Extension
from sqlmeta.objects.foreign_data_wrapper import ForeignDataWrapper
from sqlmeta.objects.foreign_server import ForeignServer
from sqlmeta.objects.linked_server import LinkedServer
from sqlmeta.objects.module import Module
from sqlmeta.objects.package import Package
from sqlmeta.objects.synonym import Synonym
from sqlmeta.objects.user_defined_type import UserDefinedType


def test_database_link_create_and_drop():
    link = DatabaseLink(
        "orders_link",
        host="db.remote",
        username="report_user",
        connect_string="db.remote/service",
        public=True,
    )
    create = link.create_statement
    assert "CREATE PUBLIC DATABASE LINK" in create
    assert "CONNECT TO report_user" in create
    assert "USING 'db.remote/service'" in create
    assert link.drop_statement == 'DROP PUBLIC DATABASE LINK "orders_link"'
    assert "PUBLIC DATABASE LINK orders_link" in str(link)

    same = DatabaseLink(
        "ORDERS_LINK",
        host="DB.REMOTE",
        username="REPORT_USER",
        connect_string="DB.REMOTE/service",
        public=True,
    )
    assert link == same
    assert hash(link) == hash(same)


def test_linked_server_statements_and_comparison():
    server = LinkedServer(
        "reports",
        product="SQL Server",
        provider="SQLNCLI",
        data_source="10.0.0.5",
        catalog="analytics",
        username="svc_reports",
    )
    create = server.create_statement
    assert "@srvproduct = 'SQL Server'" in create
    assert "sp_addlinkedsrvlogin" in create
    assert (
        server.drop_statement
        == "EXEC sp_dropserver @server = [reports], @droplogins = 'droplogins';"
    )
    assert "LINKED SERVER reports (SQL Server) -> 10.0.0.5.analytics" in str(server)

    same = LinkedServer(
        "REPORTS",
        product="sql server",
        provider="SQLNCLI",
        data_source="10.0.0.5",
        catalog="analytics",
        username="svc_reports",
    )
    assert server == same
    assert hash(server) == hash(same)


def test_extension_statements_and_str():
    ext = Extension(
        "pg_trgm",
        version="1.6",
        schema="extensions",
        description="Trigram text search",
        relocatable=True,
    )
    stmt = ext.create_statement
    assert "CREATE EXTENSION" in stmt
    assert "SCHEMA \"extensions\"" in stmt
    assert "VERSION '1.6'" in stmt
    assert ext.drop_statement == "DROP EXTENSION IF EXISTS \"pg_trgm\""
    assert "EXTENSION pg_trgm (v1.6) - Trigram text search" in str(ext)

    same = Extension("PG_TRGM", version="1.6", schema="extensions")
    assert ext == same
    assert hash(ext) == hash(same)


def test_event_create_and_to_dict_roundtrip():
    event = Event(
        "cleanup_sessions",
        schema="maintenance",
        definition="DELETE FROM sessions WHERE updated_at < NOW() - INTERVAL 1 DAY;",
        schedule="EVERY 1 HOUR",
        enabled=False,
        comment="Remove stale sessions",
        definer="admin@localhost",
        event_type="RECURRING",
    )
    stmt = event.create_statement
    assert "ON SCHEDULE EVERY 1 HOUR" in stmt
    assert "DISABLE" in stmt
    data = event.to_dict()
    restored = Event.from_dict(data)
    assert restored == event
    assert "Event maintenance.cleanup_sessions (RECURRING, disabled)" in str(event)


def test_synonym_create_drop_and_string():
    syn = Synonym(
        name="latest_orders",
        target_object="orders",
        schema="public",
        target_schema="sales",
        target_database="analytics",
        db_link="remote_link",
        dialect="oracle",
    )
    assert syn.target_full_name == '"analytics"."sales"."orders"@"remote_link"'
    stmt = syn.create_statement
    assert "CREATE OR REPLACE SYNONYM" in stmt
    assert "FOR \"analytics\"" in stmt
    assert syn.drop_statement == "DROP SYNONYM \"public\".\"latest_orders\""
    assert "SYNONYM latest_orders ->" in str(syn)

    same = Synonym(
        name="LATEST_ORDERS",
        target_object="ORDERS",
        schema="PUBLIC",
        target_schema="SALES",
        target_database="ANALYTICS",
        db_link="remote_link",
    )
    assert syn == same
    assert hash(syn) == hash(same)


def test_package_to_from_dict_and_str():
    pkg = Package(
        "sales_pkg",
        schema="sales",
        spec="AS PROCEDURE refresh_sales; END sales_pkg;",
        body="AS PROCEDURE refresh_sales IS BEGIN NULL; END refresh_sales; END sales_pkg;",
    )
    stmt = pkg.create_statement
    assert "CREATE OR REPLACE PACKAGE" in stmt
    assert "CREATE OR REPLACE PACKAGE BODY" in stmt
    data = pkg.to_dict()
    restored = Package.from_dict(data)
    assert restored == pkg
    assert "Package sales.sales_pkg (spec + body)" == str(pkg)


def test_module_statements_and_equality():
    definition = """CREATE OR REPLACE MODULE "UTILS"."audit_mod"
  PROCEDURE purge_old_audit();
END MODULE;"""
    module = Module("audit_mod", definition=definition, schema="UTILS")
    assert module.create_statement == definition
    assert "MODULE UTILS.audit_mod" in str(module)
    assert module.drop_statement == 'DROP MODULE "UTILS"."audit_mod";'

    minimal = Module("simple_mod", definition="", schema=None)
    assert "CREATE OR REPLACE MODULE" in minimal.create_statement

    same = Module("audit_mod", definition=definition, schema="UTILS")
    assert module == same
    assert hash(module) == hash(same)


def test_foreign_data_wrapper_statements():
    fdw = ForeignDataWrapper(
        "oracle_fdw",
        handler="oracle_fdw_handler",
        validator="oracle_fdw_validator",
        options={"dbserver": "ORCL", "nls_lang": "AMERICAN_AMERICA.AL32UTF8"},
    )
    stmt = fdw.create_statement
    assert "HANDLER oracle_fdw_handler" in stmt
    assert "OPTIONS (dbserver 'ORCL', nls_lang 'AMERICAN_AMERICA.AL32UTF8')" in stmt
    assert fdw.drop_statement == "DROP FOREIGN DATA WRAPPER IF EXISTS \"oracle_fdw\" CASCADE;"
    assert "FOREIGN DATA WRAPPER oracle_fdw" in str(fdw)


def test_foreign_server_statements_and_equality():
    server = ForeignServer(
        "reports",
        fdw_name="oracle_fdw",
        host="db.example.com",
        port=1521,
        dbname="SALES",
        options={"fetch_size": "500"},
    )
    stmt = server.create_statement
    assert "FOREIGN DATA WRAPPER \"oracle_fdw\"" in stmt
    assert "OPTIONS (fetch_size '500', host 'db.example.com', port '1521', dbname 'SALES')" in stmt
    assert server.drop_statement == "DROP SERVER IF EXISTS \"reports\" CASCADE;"
    assert "FOREIGN SERVER reports (FDW: oracle_fdw) -> db.example.com:1521/SALES" in str(server)

    same = ForeignServer(
        "reports",
        fdw_name="oracle_fdw",
        host="db.example.com",
        port=1521,
        dbname="SALES",
        options={"fetch_size": "500"},
    )
    assert server == same
    assert hash(server) == hash(same)


def test_user_defined_type_statements_for_variants():
    composite = UserDefinedType(
        "address_type",
        type_category="COMPOSITE",
        schema="public",
        attributes=[{"name": "street", "type": "TEXT"}, {"name": "zip", "type": "INT"}],
    )
    comp_stmt = composite.create_statement
    assert "CREATE TYPE public.address_type AS (" in comp_stmt
    assert "street TEXT" in comp_stmt

    enum = UserDefinedType(
        "status_type",
        type_category="ENUM",
        schema="public",
        enum_values=["pending", "complete"],
    )
    assert "AS ENUM ('pending', 'complete')" in enum.create_statement

    domain = UserDefinedType(
        "positive_int",
        type_category="DOMAIN",
        schema="public",
        base_type="INTEGER",
        definition="CHECK(VALUE > 0)",
    )
    assert "CREATE DOMAIN public.positive_int AS INTEGER" in domain.create_statement
    assert domain.drop_statement == "DROP DOMAIN public.positive_int"

    distinct = UserDefinedType(
        "money_type",
        type_category="DISTINCT",
        schema="finance",
        base_type="DECIMAL(10,2)",
        dialect="db2",
    )
    assert "CREATE DISTINCT TYPE finance.money_type AS DECIMAL(10,2)" in distinct.create_statement

    distinct_sqlserver = UserDefinedType(
        "money_type",
        type_category="DISTINCT",
        schema="dbo",
        base_type="DECIMAL(10,2)",
        dialect="sqlserver",
    )
    assert "CREATE TYPE [dbo].[money_type] FROM DECIMAL(10,2)" in distinct_sqlserver.create_statement

    fallback = UserDefinedType(
        "any_type",
        type_category="OTHER",
        schema=None,
        definition="TABLE OF VARCHAR(10)",
    )
    assert fallback.create_statement == "CREATE TYPE any_type AS TABLE OF VARCHAR(10)"
    assert "TYPE any_type: OTHER" in str(fallback)


def test_user_defined_type_equality():
    type1 = UserDefinedType("arr_type", type_category="COMPOSITE", schema="public")
    type2 = UserDefinedType("ARR_TYPE", type_category="COMPOSITE", schema="PUBLIC")
    assert type1 == type2
    assert hash(type1) == hash(type2)

