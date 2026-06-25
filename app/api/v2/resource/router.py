"""Resource router: endpoints an authenticated user acts on for themselves."""

from fastapi import APIRouter, Depends

from app.api.deps import authorized_user
from app.models.user import User
from app.schemas.common import Envelope
from app.schemas.identity import UserOut

resource_router = APIRouter()


@resource_router.get("/me", response_model=Envelope[UserOut])
async def get_me(user: User = Depends(authorized_user)) -> Envelope[UserOut]:
    return Envelope[UserOut](data=UserOut.model_validate(user))
