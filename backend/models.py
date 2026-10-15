from datetime import date, time

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Building(Base):
    __tablename__ = "buildings"

    building_id: Mapped[str] = mapped_column(String, primary_key=True)
    building_name: Mapped[str] = mapped_column(String, nullable=False)
    data_status: Mapped[str] = mapped_column(String, nullable=False)


class Room(Base):
    __tablename__ = "rooms"

    room_id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), nullable=False)
    building_name: Mapped[str] = mapped_column(String, nullable=False)
    floor_number: Mapped[int] = mapped_column(Integer, nullable=False)
    floor_name: Mapped[str] = mapped_column(String, nullable=False)
    room_name: Mapped[str] = mapped_column(String, nullable=False)
    facility_type: Mapped[str] = mapped_column(String, nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    capacity_students: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_connected_load_kw: Mapped[float] = mapped_column(Float, nullable=False)
    timetable_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_status: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(String, nullable=False)


class TimetableEntry(Base):
    __tablename__ = "timetable"

    timetable_entry_id: Mapped[str] = mapped_column(String, primary_key=True)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String, nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    day_of_week: Mapped[str] = mapped_column(String, nullable=False)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    subject_code: Mapped[str] = mapped_column(String, nullable=False)
    subject_name: Mapped[str] = mapped_column(String, nullable=False)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"), nullable=False)
    faculty_id: Mapped[str] = mapped_column(String, nullable=False)
    session_type: Mapped[str] = mapped_column(String, nullable=False)
    data_status: Mapped[str] = mapped_column(String, nullable=False)


class Equipment(Base):
    __tablename__ = "equipment_inventory"

    equipment_id: Mapped[str] = mapped_column(String, primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_power_watts: Mapped[float] = mapped_column(Float, nullable=False)
    total_power_watts: Mapped[float] = mapped_column(Float, nullable=False)
    assumed_daily_hours: Mapped[float] = mapped_column(Float, nullable=False)
    assumed_days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    data_status: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(String, nullable=False)


class EnergyRecord(Base):
    __tablename__ = "energy_records"

    energy_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    estimated_energy_kwh_per_day: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_energy_kwh_per_week: Mapped[float] = mapped_column(Float, nullable=False)
    electricity_tariff_inr_per_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cost_inr_per_week: Mapped[float] = mapped_column(Float, nullable=False)
    calculation_method: Mapped[str] = mapped_column(String, nullable=False)
    data_status: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(String, nullable=False)


class OccupancyObservation(Base):
    __tablename__ = "occupancy_observations"

    observation_id: Mapped[str] = mapped_column(String, primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"), nullable=False)
    observed_at: Mapped[str] = mapped_column(String, nullable=False)
    detected_person_count: Mapped[int] = mapped_column(Integer, nullable=False)
    room_capacity: Mapped[int | None] = mapped_column(Integer)
    occupancy_percent: Mapped[float | None] = mapped_column(Float)
    detection_method: Mapped[str] = mapped_column(String, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    verified_by_human: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_status: Mapped[str] = mapped_column(String, nullable=False)


class RoomDistance(Base):
    __tablename__ = "room_distances"

    distance_id: Mapped[str] = mapped_column(String, primary_key=True)
    from_room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"), nullable=False)
    to_room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"), nullable=False)
    estimated_walking_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    distance_method: Mapped[str] = mapped_column(String, nullable=False)
    data_status: Mapped[str] = mapped_column(String, nullable=False)


class SustainabilityAction(Base):
    __tablename__ = "sustainability_actions"

    action_id: Mapped[str] = mapped_column(String, primary_key=True)
    action_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(String, nullable=False)
    trigger_condition: Mapped[str] = mapped_column(String, nullable=False)
    suggested_action: Mapped[str] = mapped_column(String, nullable=False)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_status: Mapped[str] = mapped_column(String, nullable=False)
