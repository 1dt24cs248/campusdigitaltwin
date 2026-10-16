from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class OccupancyInferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: str = Field(min_length=1, max_length=100)
    image_format: Literal["png", "jpeg"]
    image_base64: str = Field(min_length=1, max_length=6_990_508)


class OccupancyInferenceRead(BaseModel):
    estimate: dict[str, Any]
    capacity_students: int = Field(ge=0)
    persisted: Literal[False] = False


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: str
    room_id: str
    equipment_type: str
    quantity: int
    unit_power_watts: float
    total_power_watts: float
    assumed_daily_hours: float
    assumed_days_per_week: int
    data_status: str
    notes: str


class EnergyRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    energy_record_id: str
    room_id: str
    record_date: date
    estimated_energy_kwh_per_day: float
    estimated_energy_kwh_per_week: float
    electricity_tariff_inr_per_kwh: float
    estimated_cost_inr_per_week: float
    calculation_method: str
    data_status: str
    notes: str


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


class OccupancyScenarioContext(BaseModel):
    """An explicit image observation attached as context, never as enrollment."""

    model_config = ConfigDict(extra="forbid")

    room_id: str = Field(min_length=1)
    estimated_visible_person_count: int = Field(ge=0)
    observed_at: datetime
    source: Literal["image_inference"]
    model: str = Field(min_length=1, max_length=200)


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timetable_entry_id: str = Field(min_length=1)
    source_room_id: str = Field(min_length=1)
    target_room_id: str = Field(min_length=1)
    student_count: int | None = Field(default=None, ge=0)
    affected_student_counts: dict[str, int] = Field(default_factory=dict, max_length=128)
    occupancy_scenario: OccupancyScenarioContext | None = None

    @field_validator("affected_student_counts")
    @classmethod
    def validate_affected_student_counts(cls, value: dict[str, int]) -> dict[str, int]:
        if any(not entry_id.strip() for entry_id in value):
            raise ValueError("affected_student_counts keys must be non-empty timetable entry IDs")
        if any(count < 0 for count in value.values()):
            raise ValueError("affected_student_counts values must be non-negative")
        return value


class SimulationResultRead(BaseModel):
    simulation_id: str
    status: Literal["feasible", "infeasible", "incomplete"]
    feasible: bool | None
    scenario_inputs: dict[str, Any]
    baseline: dict[str, Any]
    proposed: dict[str, Any]
    projected_metrics: dict[str, Any]
    checks: dict[str, dict[str, Any]]
    validation_errors: list[str]
    warnings: list[str]
    affected_entries: list[dict[str, Any]]
    affected_entities: list[dict[str, Any]]
    unresolved_conflicts: list[dict[str, Any]]
    effects: list[dict[str, Any]]
    ripple_effects: list[str]
    search: dict[str, Any]
    energy_impact: dict[str, Any]
    cost_impact: dict[str, Any]
    walking_impact: dict[str, Any]
    assumptions: list[str]
    data_classification: str


class SimulationExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_result: SimulationResultRead
    campus_context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_verdict_consistency(self):
        expected_status = {True: "feasible", False: "infeasible", None: "incomplete"}[
            self.simulation_result.feasible
        ]
        if self.simulation_result.status != expected_status:
            raise ValueError("simulation status and feasibility must agree")
        return self


class CampusQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
