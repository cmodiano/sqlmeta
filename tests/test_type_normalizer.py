import pytest

from sqlmeta.comparison.type_normalizer import DataTypeNormalizer


def test_normalize_with_precision_and_scale():
    normalizer = DataTypeNormalizer()
    assert normalizer.normalize("int", "postgresql") == "INTEGER"
    assert normalizer.normalize("varchar(100)", "postgresql") == "VARCHAR(100)"
    assert normalizer.normalize("number(10,2)", "oracle") == "NUMBER(10,2)"
    assert normalizer.normalize("numeric", "postgresql", precision=8, scale=2) == "NUMERIC(8,2)"
    # DATETIME family collapses to DATETIME
    assert normalizer.normalize("datetime2(6)", "sqlserver") == "DATETIME"


def test_normalize_boolean_and_default_precision_handling():
    normalizer = DataTypeNormalizer()
    assert normalizer.normalize("bool", "mysql") == "BOOLEAN"
    assert normalizer.normalize("timestamp", "postgresql") == "TIMESTAMP"


@pytest.mark.parametrize(
    "type1,type2,dialect1,dialect2,expected",
    [
        ("text", "clob", "postgresql", "oracle", True),
        ("varchar", "varchar2", "postgresql", "oracle", True),
        ("int", "varchar", "postgresql", "postgresql", False),
    ],
)
def test_are_equivalent(type1, type2, dialect1, dialect2, expected):
    normalizer = DataTypeNormalizer()
    assert normalizer.are_equivalent(type1, type2, dialect1, dialect2) is expected


def test_extract_precision_scale_and_base_type():
    normalizer = DataTypeNormalizer()
    assert normalizer.extract_precision_scale("NUMBER(12,4)") == (12, 4)
    assert normalizer.extract_precision_scale("VARCHAR(255)") == (255, None)
    assert normalizer.extract_precision_scale("TEXT") == (None, None)
    assert normalizer._extract_base_type("VARCHAR(200)") == "VARCHAR"

