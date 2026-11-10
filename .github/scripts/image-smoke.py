"""Exercise native runtime dependencies with synthetic, in-memory data only."""

import asyncio
import os
from io import BytesIO

import httpx
import psycopg
from docx import Document
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import create_engine

import app.main
import app.worker
from app.database.models import Base

assert os.getuid() != 0
assert psycopg.pq.version() > 0
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
engine.dispose()

docx = BytesIO()
document = Document()
document.add_paragraph('Synthetic runtime check')
document.save(docx)
assert docx.getvalue().startswith(b'PK')
pdf = BytesIO()
canvas = Canvas(pdf)
canvas.drawString(20, 20, 'Synthetic runtime check')
canvas.save()
assert pdf.getvalue().startswith(b'%PDF')


async def check_health():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app.main.app), base_url='http://synthetic.test',
    ) as client:
        assert (await client.get('/health')).status_code == 200


asyncio.run(check_health())
print('Non-root API, worker imports, database drivers, DOCX and PDF smoke checks passed')
