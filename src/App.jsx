import { useMemo, useState } from 'react';
import { campusData } from './campusData';

const navigation = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'buildings', label: 'Buildings' },
  { id: 'simulation', label: 'Simulation' },
  { id: 'insights', label: 'Insights' },
];

const formatTimestamp = (value) => {
  if (!value) return 'No observation available';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

const getRoomStatusClass = (room) => {
  const occupancy = room.latest_occupancy?.occupancy_percentage;
  if (occupancy === null || occupancy === undefined) return '';
  if (occupancy >= 75) return 'room-occupied';
  if (occupancy >= 45) return 'room-moderate';
  return 'room-available';
};

const getObservationStatus = (room) => {
  const observation = room.latest_occupancy;
  if (!observation) return 'No observation available';
  return observation.observed_person_count > 0 ? 'People detected' : 'No people detected';
};

function App() {
  const [activeSection, setActiveSection] = useState('dashboard');
  const [selectedBuildingId, setSelectedBuildingId] = useState('');
  const [selectedFloorNumber, setSelectedFloorNumber] = useState(null);
  const [selectedRoomId, setSelectedRoomId] = useState('');
  const [sourceRoomId, setSourceRoomId] = useState('');
  const [targetRoomId, setTargetRoomId] = useState('');

  const allRooms = useMemo(
    () => campusData.buildings.flatMap((building) => building.floors.flatMap((floor) => floor.rooms)),
    [],
  );
  const currentBuilding = campusData.buildings.find((building) => building.building_id === selectedBuildingId);
  const currentFloor = currentBuilding?.floors.find((floor) => floor.floor_number === selectedFloorNumber)
    ?? currentBuilding?.floors[0];
  const selectedRoom = currentFloor?.rooms.find((room) => room.room_id === selectedRoomId)
    ?? currentFloor?.rooms[0];
  const roomTimetable = selectedRoom?.timetable ?? [];
  const observedRooms = allRooms.filter((room) => room.latest_occupancy);
  const averageOccupancy = observedRooms.length
    ? Math.round(observedRooms.reduce((sum, room) => sum + room.latest_occupancy.occupancy_percentage, 0) / observedRooms.length)
    : null;
  const occupiedRooms = observedRooms.filter((room) => room.latest_occupancy.observed_person_count > 0).length;
  const sourceRoom = allRooms.find((room) => room.room_id === sourceRoomId);

  const selectBuilding = (building) => {
    const firstFloor = building.floors[0];
    setSelectedBuildingId(building.building_id);
    setSelectedFloorNumber(firstFloor?.floor_number ?? null);
    setSelectedRoomId(firstFloor?.rooms[0]?.room_id ?? '');
  };

  const selectFloor = (floor) => {
    setSelectedFloorNumber(floor.floor_number);
    setSelectedRoomId(floor.rooms[0]?.room_id ?? '');
  };

  const showBuildingList = () => {
    setSelectedBuildingId('');
    setSelectedFloorNumber(null);
    setSelectedRoomId('');
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">DIGITAL CAMPUS</p>
          <h1>{campusData.campus_name}</h1>
        </div>
        <nav className="topbar-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <button
              type="button"
              key={item.id}
              className={`nav-pill ${activeSection === item.id ? 'active' : ''}`}
              aria-current={activeSection === item.id ? 'page' : undefined}
              onClick={() => setActiveSection(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {activeSection === 'dashboard' && (
          <section className="panel dashboard-panel" aria-labelledby="overview-title">
            <div className="panel-header">
              <div>
                <p className="eyebrow">CAMPUS SNAPSHOT</p>
                <h2 id="overview-title">Campus overview</h2>
              </div>
              <span className="status-badge synthetic">{campusData.data_status}</span>
            </div>

            <div className="metric-grid">
              <article className="metric-card accent">
                <span className="metric-label">Buildings</span>
                <strong>{campusData.buildings.length}</strong>
                <small>Canonical building records</small>
              </article>
              <article className="metric-card">
                <span className="metric-label">Rooms</span>
                <strong>{allRooms.length}</strong>
                <small>Canonical room records</small>
              </article>
              <article className="metric-card">
                <span className="metric-label">Observed rooms</span>
                <strong>{observedRooms.length}</strong>
                <small>Rooms with occupancy records</small>
              </article>
              <article className="metric-card warn">
                <span className="metric-label">Avg. recorded occupancy</span>
                <strong>{averageOccupancy === null ? '—' : `${averageOccupancy}%`}</strong>
                <small>Observed records only</small>
              </article>
            </div>

            <div className="dashboard-summary">
              <div>
                <h3>Explore campus buildings</h3>
                <p>Browse canonical rooms by building and floor, then inspect their recorded details.</p>
              </div>
              <button type="button" className="primary-button" onClick={() => setActiveSection('buildings')}>
                Open building explorer
              </button>
            </div>
          </section>
        )}

        {activeSection === 'buildings' && (
          <>
            {!currentBuilding ? (
              <section className="panel building-list-panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">CANONICAL DATASET</p>
                    <h2>Building explorer</h2>
                  </div>
                  <span className="status-badge synthetic">{campusData.buildings.length} buildings</span>
                </div>
                <div className="building-grid">
                  {campusData.buildings.map((building) => {
                    const buildingRooms = building.floors.flatMap((floor) => floor.rooms);
                    return (
                      <button
                        type="button"
                        className="building-card"
                        key={building.building_id}
                        onClick={() => selectBuilding(building)}
                      >
                        <span className="building-card-id">{building.building_id}</span>
                        <strong>{building.building_name}</strong>
                        <span>{building.floors.length} floors · {buildingRooms.length} rooms</span>
                        <span className="building-card-action">View floors and rooms →</span>
                      </button>
                    );
                  })}
                </div>
              </section>
            ) : (
              <>
                <section className="panel building-explorer-panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">BUILDING EXPLORER</p>
                      <h2>{currentBuilding.building_name}</h2>
                    </div>
                    <button type="button" className="secondary-button" onClick={showBuildingList}>
                      ← All buildings
                    </button>
                  </div>

                  <div className="building-grid building-grid-compact" aria-label="Select a building">
                    {campusData.buildings.map((building) => {
                      const buildingRooms = building.floors.flatMap((floor) => floor.rooms);
                      const isSelected = building.building_id === currentBuilding.building_id;
                      return (
                        <button
                          type="button"
                          className={`building-card ${isSelected ? 'selected' : ''}`}
                          key={building.building_id}
                          aria-pressed={isSelected}
                          onClick={() => selectBuilding(building)}
                        >
                          <span className="building-card-id">{building.building_id}</span>
                          <strong>{building.building_name}</strong>
                          <span>{building.floors.length} floors · {buildingRooms.length} rooms</span>
                          <span className="building-card-action">{isSelected ? 'Selected building' : 'Switch building'}</span>
                        </button>
                      );
                    })}
                  </div>

                  <div className="floor-selector" aria-label={`Floors in ${currentBuilding.building_name}`}>
                    {currentBuilding.floors.map((floor) => (
                      <button
                        type="button"
                        key={`${currentBuilding.building_id}-${floor.floor_number}`}
                        className={`floor-button ${currentFloor?.floor_number === floor.floor_number ? 'selected' : ''}`}
                        aria-pressed={currentFloor?.floor_number === floor.floor_number}
                        onClick={() => selectFloor(floor)}
                      >
                        <span>{floor.floor_name}</span>
                        <small>{floor.rooms.length} rooms</small>
                      </button>
                    ))}
                  </div>
                </section>

                {currentFloor && (
                  <div className="content-grid building-content-grid">
                    <section className="panel rooms-panel">
                      <div className="panel-header">
                        <div>
                          <h2>{currentFloor.floor_name}</h2>
                          <span className="subtle">{currentFloor.rooms.length} canonical rooms</span>
                        </div>
                        <span className="status-badge neutral">{currentBuilding.building_id}</span>
                      </div>
                      <div className="floor-grid" aria-label={`${currentFloor.floor_name} rooms`}>
                        {currentFloor.rooms.map((room) => (
                          <button
                            type="button"
                            key={room.room_id}
                            className={`room-card ${getRoomStatusClass(room)} ${room.room_id === selectedRoom?.room_id ? 'selected' : ''}`}
                            aria-pressed={room.room_id === selectedRoom?.room_id}
                            onClick={() => setSelectedRoomId(room.room_id)}
                          >
                            <span className="room-id">{room.room_id}</span>
                            <strong>{room.room_name}</strong>
                            <small>
                              {room.latest_occupancy
                                ? `${room.latest_occupancy.observed_person_count ?? '—'}/${room.capacity ?? '—'} observed`
                                : `Capacity ${room.capacity ?? 'not recorded'} · no occupancy record`}
                            </small>
                          </button>
                        ))}
                      </div>
                    </section>

                    {selectedRoom && (
                      <RoomDetails
                        building={currentBuilding}
                        floor={currentFloor}
                        room={selectedRoom}
                      />
                    )}
                  </div>
                )}

                {selectedRoom && (
                  <section className="panel timetable-panel">
                    <div className="panel-header">
                      <div>
                        <h2>Room timetable</h2>
                        <span className="subtle">{selectedRoom.room_id}</span>
                      </div>
                      <span className="status-badge neutral">Canonical timetable records</span>
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
                            {roomTimetable.map((entry, index) => (
                              <tr key={`${entry.room_id}-${entry.day}-${entry.period}-${index}`}>
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
                        <p className="empty-note">No timetable records are linked to this room.</p>
                      )}
                    </div>
                  </section>
                )}
              </>
            )}
          </>
        )}

        {activeSection === 'simulation' && (
          <div className="bottom-grid">
            <section className="panel simulation-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">REQUEST WORKSPACE</p>
                  <h2>Simulation request</h2>
                </div>
                <span className="status-badge neutral">Request UI only</span>
              </div>
              <form className="simulation-form" onSubmit={(event) => event.preventDefault()}>
                <label>
                  Source room
                  <select value={sourceRoomId} onChange={(event) => setSourceRoomId(event.target.value)}>
                    <option value="">Select source room</option>
                    {allRooms.map((room) => (
                      <option key={room.room_id} value={room.room_id}>{room.room_id} · {room.room_name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Target room
                  <select value={targetRoomId} onChange={(event) => setTargetRoomId(event.target.value)}>
                    <option value="">Select target room</option>
                    {allRooms.map((room) => (
                      <option key={room.room_id} value={room.room_id}>{room.room_id} · {room.room_name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Section or class
                  <input type="text" placeholder="Enter a class from the canonical timetable" />
                </label>
                <label>
                  Proposed slot
                  <input type="text" placeholder="Enter a proposed time slot" />
                </label>
                <label>
                  Notes
                  <textarea rows="4" placeholder="Optional request notes" />
                </label>
                <button type="button" className="primary-button" disabled>
                  Simulator API unavailable
                </button>
                <p className="empty-note">No request is submitted and no simulation is calculated in this frontend.</p>
              </form>
            </section>

            <section className="panel results-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">RESULTS</p>
                  <h2>Comparison results</h2>
                </div>
                <span className="status-badge neutral">No simulator response</span>
              </div>
              <div className="comparison-grid">
                <div className="scenario-card baseline">
                  <h3>Baseline record</h3>
                  {sourceRoom ? (
                    <ul>
                      <li>Room: {sourceRoom.room_id}</li>
                      <li>Recorded capacity: {sourceRoom.capacity ?? 'Not available'}</li>
                      <li>Estimated energy: {sourceRoom.energy_estimate_kwh ?? 'Not available'} kWh/day</li>
                    </ul>
                  ) : (
                    <p>Select a source room to inspect its canonical baseline records.</p>
                  )}
                </div>
                <div className="scenario-card proposed">
                  <h3>Proposed scenario</h3>
                  <p>Comparison values will appear only after a simulator response is available.</p>
                </div>
              </div>
            </section>
          </div>
        )}

        {activeSection === 'insights' && (
          <>
            <section className="panel insights-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">CAMPUS ACTIONS</p>
                  <h2>Sustainability actions</h2>
                </div>
                <span className="status-badge neutral">Canonical action records</span>
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
                    <p><strong>Human approval:</strong> {action.requires_human_approval ? 'Required' : 'Not specified as required'}</p>
                    <p><strong>Record status:</strong> {action.data_status}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel insights-panel ai-results-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">AI RESULTS</p>
                  <h2>AI-generated insights</h2>
                </div>
                <span className="status-badge neutral">No AI response</span>
              </div>
              <p className="empty-note">AI-generated results are not available in this frontend yet.</p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function RoomDetails({ building, floor, room }) {
  const observation = room.latest_occupancy;
  const details = [
    ['Building', building.building_name],
    ['Floor', floor.floor_name],
    ['Facility type', room.facility_type || 'Not recorded'],
    ['Department', room.department || 'Not recorded'],
    ['Capacity', room.capacity === null ? 'Not recorded' : `${room.capacity} seats`],
    ['Connected load', room.estimated_connected_load_kw === null ? 'Not recorded' : `${room.estimated_connected_load_kw} kW`],
    ['Data status', room.data_status],
  ];

  return (
    <aside className="details-panel">
      <div className="panel-header">
        <h2>Room details</h2>
        <span className="subtle">{room.room_id}</span>
      </div>
      <div className="room-summary">
        <h3>{room.room_name}</h3>
        {details.map(([label, value]) => (
          <div className="detail-row" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <div className="info-block">
        <h4>Latest occupancy observation</h4>
        {observation ? (
          <>
            <div className="occupancy-box">
              <strong>{observation.observed_person_count ?? '—'}</strong>
              <span>people detected</span>
            </div>
            <ul>
              <li>Status: {getObservationStatus(room)}</li>
              <li>Occupancy: {observation.occupancy_percentage ?? 'Not available'}%</li>
              <li>Confidence: {observation.confidence_score === null ? 'Not available' : `${Math.round(observation.confidence_score * 100)}%`}</li>
              <li>Timestamp: {formatTimestamp(observation.observation_timestamp)}</li>
              <li>Detection method: {observation.detection_method}</li>
              <li>Data note: {observation.data_status}</li>
            </ul>
          </>
        ) : (
          <p className="empty-note">No occupancy observation is recorded for this room.</p>
        )}
      </div>
      <div className="info-block">
        <h4>Equipment inventory</h4>
        <div className="chip-list">
          {room.equipment.map((item) => <span key={item} className="chip">{item}</span>)}
          {room.equipment.length === 0 && <span className="empty-note">No equipment records available</span>}
        </div>
      </div>
    </aside>
  );
}

export default App;
