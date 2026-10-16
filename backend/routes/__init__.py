from fastapi import APIRouter

from backend.routes.ai import router as ai_router
from backend.routes.buildings import router as buildings_router
from backend.routes.energy import router as energy_router
from backend.routes.equipment import router as equipment_router
from backend.routes.occupancy import router as occupancy_router
from backend.routes.rooms import router as rooms_router
from backend.routes.simulations import router as simulations_router
from backend.routes.sustainability import router as sustainability_router
from backend.routes.timetables import router as timetables_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(buildings_router)
api_router.include_router(energy_router)
api_router.include_router(equipment_router)
api_router.include_router(rooms_router)
api_router.include_router(timetables_router)
api_router.include_router(occupancy_router)
api_router.include_router(simulations_router)
api_router.include_router(sustainability_router)
