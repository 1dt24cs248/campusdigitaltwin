import { useMemo, useState } from 'react';
import { campusData } from './campusData';

const formatTimestamp = (value) => {
  if (!value) return 'No timestamp available';

  try {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch (error) {
    return value;
  }
};

const getRoomStatusClass = (name, room) => {
  const occupancy = room?.latest_occupancy?.occupancy_percentage ?? 0;
  const status = room?.room_status ?? name;

  if (status === 'Occupied' || occupancy >= 75) return 'room occupied';
  if (status === 'Moderate' || occupancy >= 45) return 'room moderate';
  return 'room available';
};

function App() {
  const [selectedBuildingId, setSelectedBuildingId] = useState(campusData.buildings[0].building_id);
  const [selectedFloorNumber, setSelectedFloorNumber] = useState(campusData.buildings[0].floors[0].floor_number);
  const [selectedRoomId, setSelectedRoomId] = useState(campusData.buildings[0].floors[0].rooms[0].room_id);

  const currentBuilding = useMemo(
    () => campusData.buildings.find((building) => building.building_id === selectedBuildingId) ?? campusData.buildings[0],
    [selectedBuildingId],
  );

  const currentFloor = useMemo(
    () => currentBuilding.floors.find((floor) => floor.floor_number === selectedFloorNumber) ?? currentBuilding.floors[0],
    [currentBuilding, selectedFloorNumber],
  );

  const selectedRoom = useMemo(
    () => currentFloor.rooms.find((room) => room.room_id === selectedRoomId) ?? currentFloor.rooms[0],
    [currentFloor, selectedRoomId],
  );

  const allRooms = useMemo(
    () => campusData.buildings.flatMap((building) => building.floors.flatMap((floor) => floor.rooms)),
    [],
  );

  const averageOccupancy = Math.round(
    allRooms.reduce((sum, room) => sum + (room.latest_occupancy?.occupancy_percentage ?? 0), 0) /
      Math.max(allRooms.length, 1),
  );

  const occupiedRooms = allRooms.filter((room) => room.room_status === 'Occupied').length;

  const roomTimetable = campusData.timetable.filter((entry) => entry.room_id === selectedRoom.room_id);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">DIGITAL CAMPUS</p>
          <h1>{campusData.campus_name}</h1>
        </div>
        <nav className="topbar-nav" aria-label="Main navigation">
          <button type="button" className="nav-pill active">Dashboard</button>
          <button type="button" className="nav-pill">Buildings</button>
          <button type="button" className="nav-pill">Simulation</button>
          <button type="button" className="nav-pill">Insights</button>
        </nav>
      </header>

      <main className="content-grid">
        <section className="overview-panel">
          <div className="panel-header">
            <h2>Campus overview</h2>
            <span className="status-badge synthetic">Synthetic demo data</span>
          </div>

          <div className="metric-grid">
            <article className="metric-card accent">
              <span className="metric-label">Buildings</span>
              <strong>{campusData.buildings.length}</strong>
              <small>Campus blocks</small>
            </article>
            <article className="metric-card">
              <span className="metric-label">Rooms</span>
              <strong>{allRooms.length}</strong>
              <small>Tracked facilities</small>
            </article>
            <article className="metric-card">
              <span className="metric-label">Occupied rooms</span>
              <strong>{occupiedRooms}</strong>
              <small>Current status</small>
            </article>
            <article className="metric-card warn">
              <span className="metric-label">Avg. occupancy</span>
              <strong>{averageOccupancy}%</strong>
              <small>Illustrative average</small>
            </article>
          </div>

          <div className="selector-row">
            <label>
              Building
              <select
                value={selectedBuildingId}
                onChange={(event) => {
                  const nextBuildingId = event.target.value;
                  const nextBuilding = campusData.buildings.find((building) => building.building_id === nextBuildingId) ?? campusData.buildings[0];
                  setSelectedBuildingId(nextBuildingId);
                  setSelectedFloorNumber(nextBuilding.floors[0].floor_number);
                  setSelectedRoomId(nextBuilding.floors[0].rooms[0]?.room_id ?? '');
                }}
              >
                {campusData.buildings.map((building) => (
                  <option value={building.building_id} key={building.building_id}>{building.building_name}</option>
                ))}
              </select>
            </label>

            <label>
              Floor
              <select
                value={selectedFloorNumber}
                onChange={(event) => {
                  const nextFloorNumber = Number(event.target.value);
                  const nextFloor = currentBuilding.floors.find((floor) => floor.floor_number === nextFloorNumber) ?? currentBuilding.floors[0];
                  setSelectedFloorNumber(nextFloorNumber);
                  setSelectedRoomId(nextFloor.rooms[0]?.room_id ?? '');
                }}
              >
                {currentBuilding.floors.map((floor) => (
                  <option value={floor.floor_number} key={`${currentBuilding.building_id}-${floor.floor_number}`}>
                    {floor.floor_name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="digital-twin-panel">
            <div className="twin-header">
              <h3>{currentBuilding.building_name}</h3>
              <span>{currentFloor.floor_name}</span>
            </div>
            <p className="schematic-note">Illustrative floor layout — room positions are not verified.</p>

            <div className="floor-grid" aria-label="Digital Twin floor plan">
              {currentFloor.rooms.map((room) => (
                <button
                  type="button"
                  key={room.room_id}
                  className={`room-card ${getRoomStatusClass(room.room_name, room)} ${room.room_id === selectedRoom.room_id ? 'selected' : ''}`}
                  onClick={() => setSelectedRoomId(room.room_id)}
                >
                  <span className="room-id">{room.room_id}</span>
                  <strong>{room.room_name}</strong>
                  <small>{room.latest_occupancy?.observed_person_count ?? 0}/{room.capacity}</small>
                </button>
              ))}
            </div>
          </div>
        </section>

        <aside className="details-panel">
          <div className="panel-header">
            <h2>Room details</h2>
            <span className="subtle">{selectedRoom.room_id}</span>
          </div>

          <div className="room-summary">
            <h3>{selectedRoom.room_name}</h3>
            <div className="detail-row">
              <span>Building</span>
              <strong>{currentBuilding.building_name}</strong>
            </div>
            <div className="detail-row">
              <span>Floor</span>
              <strong>{currentFloor.floor_name}</strong>
            </div>
            <div className="detail-row">
              <span>Facility type</span>
              <strong>{selectedRoom.facility_type}</strong>
            </div>
            <div className="detail-row">
              <span>Department</span>
              <strong>{selectedRoom.department}</strong>
            </div>
            <div className="detail-row">
              <span>Capacity</span>
              <strong>{selectedRoom.capacity} seats</strong>
            </div>
            <div className="detail-row">
              <span>Connected load</span>
              <strong>{selectedRoom.estimated_connected_load_kw ?? 'Not available'} kW</strong>
            </div>
            <div className="detail-row">
              <span>Data status</span>
              <strong>{selectedRoom.data_status}</strong>
            </div>
          </div>

          <div className="info-block">
            <h4>Latest occupancy observation</h4>
            <div className="occupancy-box">
              <strong>{selectedRoom.latest_occupancy?.observed_person_count ?? 0}</strong>
              <span>people observed</span>
            </div>
            <ul>
              <li>Status: {selectedRoom.room_status}</li>
              <li>Occupancy: {selectedRoom.latest_occupancy?.occupancy_percentage ?? 0}%</li>
              <li>Confidence: {selectedRoom.latest_occupancy?.confidence_score ? `${Math.round(selectedRoom.latest_occupancy.confidence_score * 100)}%` : 'Not available'}</li>
              <li>Timestamp: {formatTimestamp(selectedRoom.latest_occupancy?.observation_timestamp)}</li>
              <li>Detection method: {selectedRoom.latest_occupancy?.detection_method ?? 'Not available'}</li>
              <li>Data note: {selectedRoom.latest_occupancy?.data_status ?? 'Not available'}</li>
            </ul>
          </div>

          <div className="info-block">
            <h4>Equipment inventory</h4>
            <div className="chip-list">
              {(selectedRoom.equipment ?? []).map((item) => (
                <span key={item} className="chip">{item}</span>
              ))}
              {(!selectedRoom.equipment || selectedRoom.equipment.length === 0) && <span className="empty-note">No equipment data available</span>}
            </div>
          </div>
        </aside>
      </main>

      <section className="bottom-grid">
        <div className="panel simulation-panel">
          <div className="panel-header">
            <h2>Simulation request</h2>
            <span className="status-badge neutral">API-ready UI</span>
          </div>

          <form className="simulation-form">
            <label>
              Source room
              <select defaultValue={selectedRoom.room_id}>
                {currentFloor.rooms.map((room) => (
                  <option key={room.room_id} value={room.room_id}>{room.room_name}</option>
                ))}
              </select>
            </label>

            <label>
              Target room
              <select defaultValue={currentFloor.rooms[0]?.room_id ?? ''}>
                {currentFloor.rooms.map((room) => (
                  <option key={room.room_id} value={room.room_id}>{room.room_name}</option>
                ))}
              </select>
            </label>

            <label>
              Section or class
              <input type="text" defaultValue={roomTimetable[0]?.subject ?? 'CS101'} />
            </label>

            <label>
              Proposed slot
              <input type="text" defaultValue="09:30 - 10:45" />
            </label>

            <label>
              Notes
              <textarea rows="4" defaultValue="Submit actual simulator contract payload when backend integration is available. This UI remains demonstration-safe and backend-agnostic." />
            </label>

            <button type="button" className="primary-button">Submit simulation</button>
          </form>
        </div>

        <div className="panel results-panel">
          <div className="panel-header">
            <h2>Comparison results</h2>
            <span className="status-badge neutral">Waiting for API response</span>
          </div>

          <div className="comparison-grid">
            <div className="scenario-card baseline">
              <h3>Baseline</h3>
              <p>Current room allocation and current occupancy profile.</p>
              <ul>
                <li>Room: {selectedRoom.room_id}</li>
                <li>Occupancy: {selectedRoom.latest_occupancy?.observed_person_count ?? 0}/{selectedRoom.capacity}</li>
                <li>Estimated energy: {selectedRoom.energy_estimate_kwh ?? 'n/a'} kWh</li>
              </ul>
            </div>

            <div className="scenario-card proposed">
              <h3>Proposed</h3>
              <p>Example scenario values are shown only as labelled fixtures.</p>
              <ul>
                <li>Scenario status: Pending simulator response</li>
                <li>Energy estimate: Available only after API response</li>
                <li>Cost estimate: Available only after API response</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="panel insights-panel">
        <div className="panel-header">
          <h2>Sustainability and AI results</h2>
          <span className="status-badge neutral">Member 4 API</span>
        </div>

        <div className="insight-grid">
          <article className="insight-card">
            <h3>Recommendation</h3>
            <p>{campusData.sustainabilityActions[0]?.suggested_action ?? 'No recommendation payload available yet.'}</p>
          </article>
          <article className="insight-card">
            <h3>Assumptions</h3>
            <p>These recommendation fields remain synthetic demonstration records until the backend and AI module provide verified outputs.</p>
          </article>
          <article className="insight-card">
            <h3>AI explanation</h3>
            <p>AI-generated explanations are not created in the frontend and will be rendered only when the responsible module returns actual content.</p>
          </article>
        </div>
      </section>

      <section className="panel timetable-panel">
        <div className="panel-header">
          <h2>Timetable</h2>
          <span className="status-badge neutral">Synthetic demonstration</span>
        </div>

        <div className="timetable-wrap">
          {roomTimetable.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Semester</th>
                  <th>Section</th>
                  <th>Day</th>
                  <th>Period</th>
                  <th>Subject</th>
                  <th>Session</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {roomTimetable.map((entry) => (
                  <tr key={`${entry.room_id}-${entry.day}-${entry.period}`}>
                    <td>{entry.semester}</td>
                    <td>{entry.section}</td>
                    <td>{entry.day}</td>
                    <td>{entry.period}</td>
                    <td>{entry.subject}</td>
                    <td>{entry.session_type}</td>
                    <td>{entry.start_time} - {entry.end_time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="empty-note">No timetable entries are available for this room in the current demonstration data.</p>
          )}
        </div>
      </section>

      <section className="panel sustainability-panel">
        <div className="panel-header">
          <h2>Sustainability actions</h2>
          <span className="status-badge neutral">Demo actions</span>
        </div>

        <div className="action-list">
          {campusData.sustainabilityActions.map((action) => (
            <article className="action-card" key={action.action_id}>
              <div className="action-header">
                <h3>{action.action_name}</h3>
                <span>{action.priority}</span>
              </div>
              <p><strong>Category:</strong> {action.category}</p>
              <p><strong>Trigger:</strong> {action.trigger_condition}</p>
              <p><strong>Suggested action:</strong> {action.suggested_action}</p>
              <p><strong>Status:</strong> {action.status}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

export default App;
