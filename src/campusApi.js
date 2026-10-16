import { resolveApiBaseUrl } from './apiConfig';

async function request(path, options = {}) {
  const apiBaseUrl = resolveApiBaseUrl(
    import.meta.env.VITE_API_BASE_URL,
    import.meta.env.PROD,
  );
  let response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...options.headers,
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      },
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `Cannot reach the EcoTwin backend at ${apiBaseUrl}. Check that the backend is running, the URL is correct, and its CORS settings allow this frontend.`,
      );
    }
    throw error;
  }
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = payload?.detail;
    const validationMessage = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item?.msg).filter(Boolean).join(' ')
        : null;
    const message = response.status === 422
      ? (validationMessage || 'Please check the selected room, image, or timetable details.')
      : response.status === 503
        ? (detail?.message || 'This service is temporarily unavailable. Please try again later.')
        : `${typeof detail === 'string' ? detail : detail?.message || 'The request could not be completed.'} (HTTP ${response.status} at ${path}). Check the backend URL and API route.`;
    throw new Error(message);
  }

  if (payload === null) {
    throw new Error(
      `The backend returned a non-JSON response for ${path}. Check that VITE_API_BASE_URL points to the FastAPI /api base.`,
    );
  }

  return payload;
}

function latestByRoom(records, roomKey, timestampKey) {
  const latest = new Map();
  for (const record of records) {
    const previous = latest.get(record[roomKey]);
    if (!previous || record[timestampKey] > previous[timestampKey]) {
      latest.set(record[roomKey], record);
    }
  }
  return latest;
}

function buildCampusData({
  buildings: rawBuildings,
  rooms: rawRooms,
  occupancy,
  equipment,
  timetable,
  energy,
  actions,
  recommendations,
}) {
  const occupancyByRoom = latestByRoom(occupancy, 'room_id', 'observed_at');
  const energyByRoom = latestByRoom(energy, 'room_id', 'record_date');
  const equipmentByRoom = new Map();
  const timetableByRoom = new Map();

  for (const item of equipment) {
    const items = equipmentByRoom.get(item.room_id) || [];
    if (!items.includes(item.equipment_type)) items.push(item.equipment_type);
    equipmentByRoom.set(item.room_id, items);
  }

  const mappedTimetable = timetable.map((entry) => ({
    timetable_entry_id: entry.timetable_entry_id,
    semester: entry.semester,
    section: entry.section,
    department: entry.department,
    day: entry.day_of_week,
    period: entry.period_number,
    start_time: entry.start_time,
    end_time: entry.end_time,
    subject: [entry.subject_code, entry.subject_name].filter(Boolean).join(' - '),
    room_id: entry.room_id,
    session_type: entry.session_type,
    data_status: entry.data_status,
  }));
  for (const entry of mappedTimetable) {
    const entries = timetableByRoom.get(entry.room_id) || [];
    entries.push(entry);
    timetableByRoom.set(entry.room_id, entries);
  }

  const mappedBuildings = rawBuildings.map((building) => {
    const buildingRooms = rawRooms
      .filter((room) => room.building_id === building.building_id)
      .map((room) => {
        const observation = occupancyByRoom.get(room.room_id);
        const energyRecord = energyByRoom.get(room.room_id);
        return {
          room_id: room.room_id,
          building_id: room.building_id,
          building_name: room.building_name,
          floor_number: room.floor_number,
          floor_name: room.floor_name,
          room_name: room.room_name,
          facility_type: room.facility_type,
          department: room.department,
          capacity: room.capacity_students,
          estimated_connected_load_kw: room.estimated_connected_load_kw,
          data_status: room.data_status,
          notes: room.notes,
          latest_occupancy: observation ? {
            observation_id: observation.observation_id,
            observed_person_count: observation.detected_person_count,
            room_capacity: observation.room_capacity,
            occupancy_percentage: observation.occupancy_percent,
            observation_timestamp: observation.observed_at,
            detection_method: observation.detection_method,
            confidence_score: observation.confidence_score,
            verification_status: observation.verified_by_human,
            data_status: observation.data_status,
          } : null,
          equipment: equipmentByRoom.get(room.room_id) || [],
          timetable: timetableByRoom.get(room.room_id) || [],
          energy_estimate_kwh: energyRecord?.estimated_energy_kwh_per_day ?? null,
          energy_data_status: energyRecord?.data_status ?? null,
        };
      });

    const floorNumbers = [...new Set(buildingRooms.map((room) => room.floor_number))]
      .sort((first, second) => first - second);
    return {
      building_id: building.building_id,
      building_name: building.building_name,
      data_status: building.data_status,
      floors: floorNumbers.map((floorNumber) => {
        const floorRooms = buildingRooms.filter((room) => room.floor_number === floorNumber);
        return {
          floor_number: floorNumber,
          floor_name: floorRooms[0]?.floor_name ?? `Floor ${floorNumber}`,
          rooms: floorRooms,
        };
      }),
    };
  });

  return {
    campus_name: 'EcoTwin AI',
    data_status: 'Demo campus records',
    buildings: mappedBuildings,
    timetable: mappedTimetable,
    sustainabilityActions: actions,
    recommendations,
  };
}

export async function loadCampusData() {
  const [buildings, rooms, occupancy, equipment, timetable, energy, actions, recommendations] = await Promise.all([
    request('/buildings'),
    request('/rooms?limit=500'),
    request('/occupancy?limit=500'),
    request('/equipment?limit=500'),
    request('/timetables?limit=500'),
    request('/energy?limit=500'),
    request('/sustainability/actions'),
    request('/ai/recommendations'),
  ]);

  return buildCampusData({
    buildings,
    rooms,
    occupancy,
    equipment,
    timetable,
    energy,
    actions,
    recommendations,
  });
}

export function submitSimulation(payload) {
  return request('/simulations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function requestSimulationExplanation(simulationResult) {
  return request('/ai/explanations', {
    method: 'POST',
    body: JSON.stringify({ simulation_result: simulationResult }),
  });
}

export function inferOccupancy(payload) {
  return request('/occupancy/infer', { method: 'POST', body: JSON.stringify(payload) });
}

export function askCampusQuestion(question) {
  return request('/ai/chat', { method: 'POST', body: JSON.stringify({ question }) });
}
