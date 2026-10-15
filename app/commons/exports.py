"""The commons package exports."""

import csv
from collections.abc import AsyncIterator
from io import StringIO
from typing import Any

from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from app.commons.constants import CSV_BATCH_SIZE, CSV_FORMULA_PREFIXES
from app.commons.schemas import BaseCSVSchema


def csv_cell(value: object) -> object:
    """Return a value safe to open in a spreadsheet (no formula execution)."""
    if isinstance(value, str) and value.startswith(CSV_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def csv_response(
    session: AsyncSession,
    query: SelectOfScalar[Any],
    schema: type[BaseCSVSchema],
    filename: str,
) -> StreamingResponse:
    """Return the rows of a query as a CSV file, one column per schema field."""
    return StreamingResponse(
        csv_chunks(session, query, schema),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def csv_chunks(
    session: AsyncSession, query: SelectOfScalar[Any], schema: type[BaseCSVSchema]
) -> AsyncIterator[str]:
    """
    Yield a CSV file: the header, then one chunk per batch of rows.

    Why: the rows are read with a server-side cursor while the file is sent, so
    an export of any size holds one batch in memory. The session stays open
    until the response is sent (FastAPI closes request dependencies after it).
    """
    headers = {name: field.title or name for name, field in schema.model_fields.items()}
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(headers.values()))
    writer.writeheader()
    yield _drain(buffer)
    result = await session.stream_scalars(
        query.execution_options(yield_per=CSV_BATCH_SIZE)
    )
    async for rows in result.partitions():
        for row in rows:
            data = schema.model_validate(row).model_dump(mode="json")
            writer.writerow(
                {headers[name]: csv_cell(value) for name, value in data.items()}
            )
        yield _drain(buffer)


def _drain(buffer: StringIO) -> str:
    """Return what was written to the buffer, and empty it."""
    chunk = buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    return chunk
