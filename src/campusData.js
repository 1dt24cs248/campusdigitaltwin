import buildingsCsv from '../data/updated_dataset/canonical_csv/buildings.csv?raw';
import roomsCsv from '../data/updated_dataset/canonical_csv/rooms.csv?raw';
import occupancyCsv from '../data/updated_dataset/canonical_csv/occupancy_observations.csv?raw';
import equipmentCsv from '../data/updated_dataset/canonical_csv/equipment_inventory.csv?raw';
import timetableCsv from '../data/updated_dataset/canonical_csv/timetable.csv?raw';
import energyCsv from '../data/updated_dataset/canonical_csv/energy_records.csv?raw';
import actionsCsv from '../data/updated_dataset/canonical_csv/sustainability_actions.csv?raw';

function parseCsv(csv) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;

  for (let index = 0; index < csv.length; index += 1) {
    const character = csv[index];

    if (quoted) {
      if (character === '"' && csv[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"' && field.length === 0) {
      quoted = true;
    } else if (character === ',') {
      row.push(field);
      field = '';
    } else if (character === '\n' || character === '\r') {
      if (character === '\r' && csv[index + 1] === '\n') index += 1;
      row.push(field);
      if (row.some((value) => value.trim() !== '')) rows.push(row);
      row = [];
      field = '';
    } else {
      field += character;
    }
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    if (row.some((value) => value.trim() !== '')) rows.push(row);
  }

  const [header, ...records] = rows;
  if (!header) return [];

  return records.map((record) => Object.fromEntries(
    header.map((key, index) => [key.replace(/^\uFEFF/, '').trim(), (record[index] ?? '').trim()]),
  ));
}

const toNumber = (value) => {
  if (value === undefined || value === null || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const rawBuildings = parseCsv(buildingsCsv);
const rawRooms = parseCsv(roomsCsv);
const latestOccupancyByRoom = new Map();
const equipmentByRoom = new Map();
const timetableByRoom = new Map();
const energyByRoom = new Map();

for (const observation of parseCsv(occupancyCsv)) {
  const previous = latestOccupancyByRoom.get(observation.room_id);
  if (!previous || observation.observed_at > previous.observed_at) {
    latestOccupancyByRoom.set(observation.room_id, observation);
  }
}

for (const equipment of parseCsv(equipmentCsv)) {
  const items = equipmentByRoom.get(equipment.room_id) ?? [];
  if (!items.includes(equipment.equipment_type)) items.push(equipment.equipment_type);
  equipmentByRoom.set(equipment.room_id, items);
}

for (const entry of parseCsv(timetableCsv)) {
  const entries = timetableByRoom.get(entry.room_id) ?? [];
  entries.push({
    semester: entry.semester,
    section: entry.section,
    department: entry.department,
    day: entry.day_of_week,
    period: entry.period_number,
    start_time: entry.start_time,
    end_time: entry.end_time,
    subject: [entry.subject_code, entry.subject_name].filter(Boolean).join(' — '),
    room_id: entry.room_id,
    session_type: entry.session_type,
  });
  timetableByRoom.set(entry.room_id, entries);
}

for (const energy of parseCsv(energyCsv)) {
  energyByRoom.set(energy.room_id, energy);
}

const buildings = rawBuildings.map((building) => {
  const rooms = rawRooms
    .filter((room) => room.building_id === building.building_id)
    .map((room) => {
      const observation = latestOccupancyByRoom.get(room.room_id);
      const energy = energyByRoom.get(room.room_id);

      return {
        room_id: room.room_id,
        building_id: room.building_id,
        building_name: room.building_name,
        floor_number: toNumber(room.floor_number),
        floor_name: room.floor_name,
        room_name: room.room_name,
        facility_type: room.facility_type,
        department: room.department,
        capacity: toNumber(room.capacity_students),
        estimated_connected_load_kw: toNumber(room.estimated_connected_load_kw),
        data_status: room.data_status,
        notes: room.notes,
        latest_occupancy: observation ? {
          observation_id: observation.observation_id,
          observed_person_count: toNumber(observation.detected_person_count),
          room_capacity: toNumber(observation.room_capacity),
          occupancy_percentage: toNumber(observation.occupancy_percent),
          observation_timestamp: observation.observed_at,
          detection_method: observation.detection_method,
          confidence_score: toNumber(observation.confidence_score),
          verification_status: observation.verified_by_human,
          data_status: observation.data_status,
        } : null,
        equipment: equipmentByRoom.get(room.room_id) ?? [],
        timetable: timetableByRoom.get(room.room_id) ?? [],
        energy_estimate_kwh: toNumber(energy?.estimated_energy_kwh_per_day),
        energy_data_status: energy?.data_status ?? null,
      };
    });

  const floors = [...new Set(rooms.map((room) => room.floor_number))]
    .sort((first, second) => first - second)
    .map((floorNumber) => {
      const floorRooms = rooms.filter((room) => room.floor_number === floorNumber);
      return {
        floor_number: floorNumber,
        floor_name: floorRooms[0].floor_name,
        rooms: floorRooms,
      };
    });

  return {
    building_id: building.building_id,
    building_name: building.building_name,
    data_status: building.data_status,
    floors,
  };
});

export const campusData = {
  campus_name: 'EcoTwin AI',
  data_status: 'Canonical CSV dataset — synthetic/illustrative records',
  buildings,
  timetable: [...timetableByRoom.values()].flat(),
  sustainabilityActions: parseCsv(actionsCsv).map((action) => ({
    action_id: action.action_id,
    action_name: action.action_name,
    category: action.category,
    priority: action.priority,
    trigger_condition: action.trigger_condition,
    suggested_action: action.suggested_action,
    requires_human_approval: action.requires_human_approval === 'True',
    data_status: action.data_status,
  })),
};
