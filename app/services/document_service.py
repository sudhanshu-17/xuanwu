"""Document records. File upload/storage is wired in Phase 11; for now the
document metadata (with an encrypted number + blind index) is stored."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.user import User
from app.utils.blind_index import blind_index


async def list_documents(db: AsyncSession, user_id: uuid.UUID) -> list[Document]:
    rows = await db.scalars(select(Document).where(Document.user_id == user_id))
    return list(rows.all())


async def create_document(
    db: AsyncSession, user: User, *, doc_type: str, doc_number: str, doc_expire: date | None
) -> Document:
    document = Document(
        user_id=user.id,
        doc_type=doc_type,
        doc_number=doc_number,
        doc_number_index=blind_index(doc_number),
        doc_expire=doc_expire,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document
