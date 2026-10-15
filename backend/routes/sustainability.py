from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SustainabilityAction
from backend.schemas import SustainabilityActionRead


router = APIRouter(prefix="/api/sustainability/actions", tags=["sustainability"])


@router.get("", response_model=list[SustainabilityActionRead])
def list_sustainability_actions(db: Session = Depends(get_db)) -> list[SustainabilityAction]:
    return list(db.scalars(select(SustainabilityAction).order_by(SustainabilityAction.action_id)))
