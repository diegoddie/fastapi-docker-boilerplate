"""The commons package exports."""

import csv
from io import StringIO
from typing import Any

from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from app.commons.constants import CSV_FORMULA_PREFIXES
from app.commons.schemas import BaseCSVSchema


def csv_cell(value: object) -> object:
    """Return a value safe to open in a spreadsheet (no formula execution)."""
    if isinstance(value, str) and value.startswith(CSV_FORMULA_PREFIXES):
        return f"'{value}"
    return value


async def csv_response(
    session: AsyncSession,
    query: SelectOfScalar[Any],
    schema: type[BaseCSVSchema],
    filename: str,
) -> StreamingResponse:
    """Return the rows of a query as a CSV file, one column per schema field."""
    headers = {name: field.title or name for name, field in schema.model_fields.items()}
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(headers.values()))
    writer.writeheader()
    for row in (await session.exec(query)).all():
        data = schema.model_validate(row).model_dump(mode="json")
        writer.writerow(
            {headers[name]: csv_cell(value) for name, value in data.items()}
        )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
