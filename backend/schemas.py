from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field


class BuildingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: str
    building_name: str
    data_status: str


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: str
    building_id: str
    building_name: str
    floor_number: int
    floor_name: str
    room_name: str
    facility_type: str
    department: str
    capacity_students: int
    estimated_connected_load_kw: float
    timetable_eligible: bool
    data_status: str
    notes: str


class TimetableEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timetable_entry_id: str
    semester: int
    section: str
    department: str
    day_of_week: str
    period_number: int
    start_time: time
    end_time: time
    subject_code: str
    subject_name: str
    room_id: str
    faculty_id: str
    session_type: str
    data_status: str


class OccupancyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    observation_id: str
    room_id: str
    observed_at: datetime
    detected_person_count: int
    room_capacity: int | None
    occupancy_percent: float | None
    detection_method: str
    confidence_score: float | None
    verified_by_human: bool
    data_status: str


class OccupancyCreate(BaseModel):
    room_id: str
    detected_person_count: int = Field(ge=0)
    observed_at: datetime
    detection_method: str = Field(min_length=1)
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    verified_by_human: bool = False
    data_status: str = Field(min_length=1)


class SustainabilityActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_id: str
    action_name: str
    category: str
    priority: str
    trigger_condition: str
    suggested_action: str
    requires_human_approval: bool
    data_status: str


class SimulationRequest(BaseModel):
    timetable_entry_id: str = Field(min_length=1)
    source_room_id: str = Field(min_length=1)
    target_room_id: str = Field(min_length=1)
    student_count: int | None = Field(default=None, ge=0)

