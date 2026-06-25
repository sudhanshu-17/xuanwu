"""The user's identity documents (file upload/storage: Phase 11)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authorized_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Envelope
from app.schemas.resource import DocumentIn, DocumentOut
from app.services import document_service

router = APIRouter()


@router.get("/documents/me", response_model=Envelope[list[DocumentOut]])
async def list_my_documents(
    user: User = Depends(authorized_user), db: AsyncSession = Depends(get_db)
) -> Envelope[list[DocumentOut]]:
    rows = await document_service.list_documents(db, user.id)
    return Envelope[list[DocumentOut]](data=[DocumentOut.model_validate(r) for r in rows])


@router.post(
    "/documents", response_model=Envelope[DocumentOut], status_code=status.HTTP_201_CREATED
)
async def add_document(
    payload: DocumentIn,
    user: User = Depends(authorized_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[DocumentOut]:
    document = await document_service.create_document(
        db,
        user,
        doc_type=payload.doc_type,
        doc_number=payload.doc_number,
        doc_expire=payload.doc_expire,
    )
    return Envelope[DocumentOut](data=DocumentOut.model_validate(document))
