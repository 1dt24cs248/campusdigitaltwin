from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import SimulationRequest, SimulationResultRead
from backend.services.simulator import (
    SimulationInputError,
    SimulationNotFoundError,
    evaluate_relocation,
)


router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("", response_model=SimulationResultRead)
def create_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return evaluate_relocation(request, db)
    except SimulationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SimulationInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
