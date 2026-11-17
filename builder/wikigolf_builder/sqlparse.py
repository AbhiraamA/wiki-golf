"""Streaming parser for MediaWiki SQL dumps.

Column positions come from the CREATE TABLE statement; nothing is hard-coded. Handles both the
classic layout (many rows per INSERT line) and one row per line. Works on bytes throughout and
uses one compiled regex per table so the per-row work happens in C.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from typing import BinaryIO

CHUNK = 1 << 23  # 8 MiB

_CREATE_RE = re.compile(rb"CREATE TABLE `(\w+)` \((.*?)\n\)", re.S)
_COLUMN_RE = re.compile(rb"^\s*`(\w+)`\s", re.M)
# One SQL value: a quoted string with backslash escapes, or a bare token (number, NULL).
_VALUE = rb"'[^'\\]*(?:\\.[^'\\]*)*'|[^,()']*"
_ESCAPE_RE = re.compile(rb"\\(.)", re.S)
_ESCAPES = {b"0": b"\0", b"n": b"\n", b"r": b"\r", b"t": b"\t", b"Z": b"\x1a", b"b": b"\b"}


class DumpFormatError(ValueError):
    pass


def parse_columns(header: bytes, table: str) -> list[str]:
    for m in _CREATE_RE.finditer(header):
        if m.group(1).decode() == table:
            cols = [c.decode() for c in _COLUMN_RE.findall(m.group(2))]
            if not cols:
                raise DumpFormatError(f"No columns found for {table}")
            return cols
    raise DumpFormatError(f"CREATE TABLE `{table}` not found")


def row_regex(columns: Sequence[str], capture: Sequence[str]) -> re.Pattern:
    """Regex matching any one row of the table, capturing `capture` columns in table order.

    Every row matches, so the scan never restarts inside a quoted value.
    """
    for name in capture:
        if name not in columns:
            raise DumpFormatError(f"Column {name} not in table (have {', '.join(columns)})")
    parts = [b"(" + _VALUE + b")" if c in capture else b"(?:" + _VALUE + b")" for c in columns]
    return re.compile(rb"\(" + b",".join(parts) + rb"\)")


def iter_rows(
    stream: BinaryIO,
    table: str,
    select: Sequence[str],
    where: dict[str, bytes] | None = None,
    chunk_size: int = CHUNK,
) -> Iterator[list[tuple[bytes, ...]]]:
    """Yield batches of rows as tuples of raw values in `select` order.

    `where` keeps only rows whose raw value equals the given bytes (e.g. {"page_namespace": b"0"}).
    """
    where = where or {}
    buf = b""
    while b"INSERT INTO" not in buf:
        data = stream.read(chunk_size)
        if not data:
            break
        buf += data
    start = buf.find(b"INSERT INTO")
    header = buf if start < 0 else buf[:start]
    columns = parse_columns(header, table)
    if start < 0:
        return
    wanted = list(dict.fromkeys([*select, *where]))
    pattern = row_regex(columns, wanted)
    captured = sorted(wanted, key=columns.index)
    sel = [captured.index(c) for c in select]
    conds = [(captured.index(c), v) for c, v in where.items()]
    single = len(captured) == 1
    identity = not conds and sel == list(range(len(captured)))

    rest = buf[start:]
    eof = False
    while not eof:
        data = stream.read(chunk_size)
        if not data:
            eof = True
            block, rest = rest, b""
        else:
            rest += data
            cut = rest.rfind(b"\n")
            if cut < 0:
                continue
            block, rest = rest[:cut], rest[cut:]
        rows = pattern.findall(block)
        if single:
            rows = [(r,) for r in rows]
        if conds:
            rows = [r for r in rows if all(r[i] == v for i, v in conds)]
        if not identity:
            rows = [tuple(r[i] for i in sel) for r in rows]
        if rows:
            yield rows


def unquote(value: bytes) -> bytes:
    """Strip quotes and unescape a MySQL string literal. NULL becomes b''."""
    if value == b"NULL":
        return b""
    if value[:1] == b"'" and value[-1:] == b"'":
        value = value[1:-1]
    if b"\\" in value:
        value = _ESCAPE_RE.sub(lambda m: _ESCAPES.get(m.group(1), m.group(1)), value)
    return value


def text(value: bytes) -> str:
    return unquote(value).decode("utf-8", errors="replace")
