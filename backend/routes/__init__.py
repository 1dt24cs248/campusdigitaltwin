from fastapi import APIRouter

from backend.routes.buildings import router as buildings_router
from backend.routes.occupancy import router as occupancy_router
from backend.routes.rooms import router as rooms_router
from backend.routes.simulations import router as simulations_router
from backend.routes.sustainability import router as sustainability_router
from backend.routes.timetables import router as timetables_router

api_router = APIRouter()
api_router.include_router(buildings_router)
api_router.include_router(rooms_router)
api_router.include_router(timetables_router)
api_router.include_router(occupancy_router)
api_router.include_router(simulations_router)
api_router.include_router(sustainability_router)
