import io

import pytest

from wikigolf_builder.sqlparse import DumpFormatError, iter_rows, parse_columns, text, unquote

DUMP = b"""-- header
CREATE TABLE `t` (
  `b` int(11) NOT NULL,
  `a` varbinary(255) NOT NULL,
  `c` int(11) NOT NULL,
  PRIMARY KEY (`b`)
) ENGINE=InnoDB;

INSERT INTO `t` VALUES (1,'x(1,2,3)',0),(2,'it\\'s, ok',1),(3,'back\\\\slash',0);
INSERT INTO `t` VALUES
(4,'line\\nbreak',0),
(5,NULL,0),
(6,'(7,\\'y\\',0)',1);
/*!40000 ALTER TABLE `t` ENABLE KEYS */;
"""


def rows(chunk_size=1 << 20, **kw):
    return [
        r for batch in iter_rows(io.BytesIO(DUMP), "t", chunk_size=chunk_size, **kw) for r in batch
    ]


def test_columns_come_from_create_table():
    assert parse_columns(DUMP, "t") == ["b", "a", "c"]
    with pytest.raises(DumpFormatError):
        parse_columns(DUMP, "other")


def test_select_in_any_order():
    got = rows(select=["a", "b"])
    assert [int(b) for _, b in got] == [1, 2, 3, 4, 5, 6]
    assert text(got[0][0]) == "x(1,2,3)"
    assert text(got[1][0]) == "it's, ok"
    assert text(got[2][0]) == "back\\slash"
    assert text(got[3][0]) == "line\nbreak"
    assert unquote(got[4][0]) == b""


def test_parens_inside_strings_do_not_create_rows():
    got = rows(select=["b"])
    assert len(got) == 6


def test_where_filters_rows():
    got = rows(select=["b"], where={"c": b"1"})
    assert [int(r[0]) for r in got] == [2, 6]


@pytest.mark.parametrize("chunk_size", [3, 7, 64])
def test_small_chunks_give_same_rows(chunk_size):
    assert rows(chunk_size=chunk_size, select=["b", "a"]) == rows(select=["b", "a"])


def test_unknown_column():
    with pytest.raises(DumpFormatError):
        rows(select=["zzz"])
