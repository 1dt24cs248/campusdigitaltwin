import { useEffect, useMemo, useRef, useState } from 'react';
import { askCampusQuestion, inferOccupancy, loadCampusData, requestSimulationExplanation, submitSimulation } from './campusApi';

const navigation = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'buildings', label: 'Buildings' },
  { id: 'occupancy', label: 'Occupancy vision' },
  { id: 'simulation', label: 'Simulation' },
  { id: 'assistant', label: 'AI assistant' },
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

const recordSourceLabel = (value = '') => /synthetic|illustrative/i.test(value) ? 'Demo record' : 'Campus record';
const responseSourceLabel = (response) => {
  if (response?.source === 'language_model') return `Model response · ${response.model}`;
  if (response?.provider_status === 'not_configured') return 'Deterministic explanation · model not configured';
  if (response?.provider_status === 'unavailable') return 'Deterministic explanation · provider unavailable';
  if (response?.provider_status === 'conflicting_response') return 'Deterministic explanation · conflicting model response rejected';
  return 'Deterministic explanation';
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
  const [campusData, setCampusData] = useState(null);
  const [dataLoading, setDataLoading] = useState(true);
  const [dataError, setDataError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedBuildingId, setSelectedBuildingId] = useState('');
  const [selectedFloorNumber, setSelectedFloorNumber] = useState(null);
  const [selectedRoomId, setSelectedRoomId] = useState('');
  const [roomQuery, setRoomQuery] = useState('');
  const [recommendationQuery, setRecommendationQuery] = useState('');
  const [recommendationLimit, setRecommendationLimit] = useState(10);
  const [timetableEntryId, setTimetableEntryId] = useState('');
  const [targetRoomId, setTargetRoomId] = useState('');
  const [studentCount, setStudentCount] = useState('');
  const [affectedStudentCountsText, setAffectedStudentCountsText] = useState('');
  const [simulationResult, setSimulationResult] = useState(null);
  const [simulationExplanation, setSimulationExplanation] = useState(null);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState('');
  const [explanationError, setExplanationError] = useState('');
  const [visionImage, setVisionImage] = useState(null);
  const [visionPreview, setVisionPreview] = useState('');
  const [visionResult, setVisionResult] = useState(null);
  const [visionObservation, setVisionObservation] = useState(null);
  const [visionLoading, setVisionLoading] = useState(false);
  const [visionError, setVisionError] = useState('');
  const [includeOccupancyContext, setIncludeOccupancyContext] = useState(false);
  const visionRequestId = useRef(0);
  const [question, setQuestion] = useState('Which rooms may be underused based on the available records?');
  const [chatResult, setChatResult] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState('');

  useEffect(() => {
    let active = true;
    setDataLoading(true);
    setDataError('');
    loadCampusData()
      .then((data) => {
        if (active) setCampusData(data);
      })
      .catch((error) => {
        if (active) setDataError(error.message || 'Unable to load campus data.');
      })
      .finally(() => {
        if (active) setDataLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  useEffect(() => () => {
    if (visionPreview) URL.revokeObjectURL(visionPreview);
  }, [visionPreview]);

  const allRooms = useMemo(
    () => campusData?.buildings.flatMap((building) => building.floors.flatMap((floor) => floor.rooms)) || [],
    [campusData],
  );
  const currentBuilding = campusData?.buildings.find((building) => building.building_id === selectedBuildingId);
  const currentFloor = currentBuilding?.floors.find((floor) => floor.floor_number === selectedFloorNumber)
    ?? currentBuilding?.floors[0];
  const selectedRoom = currentFloor?.rooms.find((room) => room.room_id === selectedRoomId)
    ?? currentFloor?.rooms[0];
  const visibleRooms = (currentFloor?.rooms ?? []).filter((room) =>
    `${room.room_id} ${room.room_name} ${room.department} ${room.facility_type}`.toLowerCase().includes(roomQuery.trim().toLowerCase()),
  );
  const roomTimetable = selectedRoom?.timetable ?? [];
  const observedRooms = allRooms.filter((room) => room.latest_occupancy);
  const occupancyValues = observedRooms
    .map((room) => room.latest_occupancy.occupancy_percentage)
    .filter((value) => value !== null && value !== undefined);
  const averageOccupancy = observedRooms.length
    ? occupancyValues.length
      ? Math.round(occupancyValues.reduce((sum, value) => sum + value, 0) / occupancyValues.length)
      : null
    : null;
  const selectedTimetableEntry = campusData?.timetable.find((entry) => entry.timetable_entry_id === timetableEntryId);
  const simulationAffectedRoomIds = simulationResult?.projected_metrics?.affected_room_ids ?? [];
  const visibleRecommendations = useMemo(() => {
    const query = recommendationQuery.trim().toLowerCase();
    if (!query) return campusData?.recommendations ?? [];
    return (campusData?.recommendations ?? []).filter((recommendation) =>
      [
        recommendation.title,
        recommendation.room_id,
        recommendation.building_id,
        ...recommendation.evidence,
        recommendation.suggested_next_step,
      ].filter(Boolean).join(' ').toLowerCase().includes(query),
    );
  }, [campusData, recommendationQuery]);
  const displayedRecommendations = visibleRecommendations.slice(0, recommendationLimit);

  const clearVisionEstimate = () => {
    visionRequestId.current += 1;
    setVisionResult(null);
    setVisionObservation(null);
    setVisionLoading(false);
    setVisionError('');
    setIncludeOccupancyContext(false);
  };

  const chooseVisionImage = (file) => {
    if (!file) return;
    clearVisionEstimate();
    setVisionError('');
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setVisionImage(null); setVisionPreview(''); setVisionError('Choose a JPEG or PNG classroom image.'); return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setVisionImage(null); setVisionPreview(''); setVisionError('The image must be 5 MB or smaller.'); return;
    }
    setVisionImage(file);
    setVisionPreview(URL.createObjectURL(file));
  };

  const runVision = async () => {
    if (!visionImage || !selectedRoom) { setVisionError('Choose a classroom image and room first.'); return; }
    const requestId = ++visionRequestId.current;
    const image = visionImage;
    const room = selectedRoom;
    setVisionLoading(true);
    setVisionError('');
    setVisionResult(null);
    setVisionObservation(null);
    setIncludeOccupancyContext(false);
    try {
      const bytes = new Uint8Array(await image.arrayBuffer());
      let binary = ''; bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
      const result = await inferOccupancy({
        room_id: room.room_id,
        image_format: image.type === 'image/png' ? 'png' : 'jpeg',
        image_base64: btoa(binary),
      });
      if (requestId !== visionRequestId.current) return;
      setVisionResult(result);
      setVisionObservation({
        room_id: room.room_id,
        room_name: room.room_name,
        estimated_visible_person_count: result.estimate.estimated_occupancy,
        observed_at: result.estimate.observed_at,
        source: result.estimate.source,
        model: result.estimate.model,
      });
    } catch (error) {
      if (requestId === visionRequestId.current) {
        setVisionError(error.message || 'Image analysis failed. Please try again.');
      }
    } finally {
      if (requestId === visionRequestId.current) setVisionLoading(false);
    }
  };

  const submitQuestion = async (event) => {
    event.preventDefault(); setChatLoading(true); setChatError(''); setChatResult(null);
    try { setChatResult(await askCampusQuestion(question)); }
    catch (error) { setChatError(error.message || 'The answer is unavailable. Please try again.'); }
    finally { setChatLoading(false); }
  };

  const runSimulation = async (event) => {
    event.preventDefault();
    setSimulationError('');
    setExplanationError('');
    setSimulationExplanation(null);
    setSimulationResult(null);
    if (!selectedTimetableEntry || !targetRoomId) {
      setSimulationError('Select a timetable entry and destination room.');
      return;
    }
    if (studentCount === '') {
      setSimulationError('Enter the class enrollment so destination capacity can be checked. The image estimate is not enrollment.');
      return;
    }
    const occupancyMatchesScenario = visionObservation && [selectedTimetableEntry.room_id, targetRoomId]
      .includes(visionObservation.room_id);
    if (includeOccupancyContext && !occupancyMatchesScenario) {
      setSimulationError('The image estimate belongs to a different room. Choose its room as the source or destination, or leave the observation out.');
      return;
    }

    setSimulationLoading(true);
    try {
      let affectedStudentCounts;
      try {
        affectedStudentCounts = Object.fromEntries(affectedStudentCountsText.split(/\r?\n/).filter(Boolean).map((line) => {
          const [entryId, count, ...extra] = line.split('=').map((part) => part.trim());
          if (!entryId || !/^\d+$/.test(count || '') || extra.length) throw new Error();
          return [entryId, Number(count)];
        }));
      } catch {
        setSimulationError('Enter each timetable ID and class size on its own line, like TT0031=25.');
        setSimulationLoading(false);
        return;
      }
      const result = await submitSimulation({
        timetable_entry_id: selectedTimetableEntry.timetable_entry_id,
        source_room_id: selectedTimetableEntry.room_id,
        target_room_id: targetRoomId,
        student_count: studentCount === '' ? null : Number(studentCount),
        affected_student_counts: affectedStudentCounts,
        occupancy_scenario: includeOccupancyContext ? {
          room_id: visionObservation.room_id,
          estimated_visible_person_count: visionObservation.estimated_visible_person_count,
          observed_at: visionObservation.observed_at,
          source: visionObservation.source,
          model: visionObservation.model,
        } : null,
      });
      setSimulationResult(result);
      try {
        setSimulationExplanation(await requestSimulationExplanation(result));
      } catch (error) {
        setExplanationError(error.message || 'The explanation could not be generated.');
      }
    } catch (error) {
      setSimulationError(error.message || 'The simulation request failed.');
    } finally {
      setSimulationLoading(false);
    }
  };

  const selectBuilding = (building) => {
    const firstFloor = building.floors[0];
    clearVisionEstimate();
    setSelectedBuildingId(building.building_id);
    setSelectedFloorNumber(firstFloor?.floor_number ?? null);
    setSelectedRoomId(firstFloor?.rooms[0]?.room_id ?? '');
  };

  const selectFloor = (floor) => {
    clearVisionEstimate();
    setSelectedFloorNumber(floor.floor_number);
    setSelectedRoomId(floor.rooms[0]?.room_id ?? '');
  };

  const showBuildingList = () => {
    clearVisionEstimate();
    setSelectedBuildingId('');
    setSelectedFloorNumber(null);
    setSelectedRoomId('');
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">DIGITAL CAMPUS</p>
          <h1>{campusData?.campus_name ?? 'EcoTwin AI'}</h1>
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
        {dataLoading && <section className="panel" role="status">Loading campus records from the backend...</section>}
        {!dataLoading && dataError && (
          <section className="panel" role="alert">
            <h2>Campus data unavailable</h2>
            <p>{dataError}</p>
            <button type="button" className="primary-button" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </button>
          </section>
        )}
        {!dataLoading && !dataError && campusData && (
          <>
        {activeSection === 'dashboard' && (
          <section className="panel dashboard-panel" aria-labelledby="overview-title">
            <div className="panel-header">
              <div>
                <p className="eyebrow">CAMPUS SNAPSHOT</p>
                <h2 id="overview-title">Campus at a glance</h2>
                <p className="dashboard-intro">Explore buildings, rooms, and the latest records available to this demo.</p>
              </div>
              <span className="status-badge synthetic">Demo campus data</span>
            </div>

            <div className="dashboard-content">
            <div className="metric-grid">
              <article className="metric-card accent">
                <span className="metric-label">Buildings</span>
                <strong>{campusData.buildings.length}</strong>
                <small>Across the campus</small>
              </article>
              <article className="metric-card">
                <span className="metric-label">Rooms</span>
                <strong>{allRooms.length}</strong>
                <small>Available to explore</small>
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
                <p>Browse campus rooms by building and floor, then inspect their recorded details.</p>
              </div>
              <button type="button" className="primary-button" onClick={() => setActiveSection('buildings')}>
                Open building explorer
              </button>
            </div>
            <div className="dashboard-workspaces" aria-label="Explore other workspaces">
              <button type="button" className="workspace-shortcut" onClick={() => setActiveSection('occupancy')}>
                <span className="shortcut-label">IMAGE ESTIMATION</span>
                <strong>Occupancy vision</strong>
                <span>Upload a room image for a separate visible-person estimate.</span>
              </button>
              <button type="button" className="workspace-shortcut" onClick={() => setActiveSection('simulation')}>
                <span className="shortcut-label">SCENARIO CHECKS</span>
                <strong>Simulation Studio</strong>
                <span>Evaluate a proposed timetable relocation without changing the schedule.</span>
              </button>
              <button type="button" className="workspace-shortcut" onClick={() => setActiveSection('insights')}>
                <span className="shortcut-label">CAMPUS INSIGHTS</span>
                <strong>Sustainability insights</strong>
                <span>Review actions and recommendations grounded in available records.</span>
              </button>
            </div>
            </div>
          </section>
        )}

        {activeSection === 'buildings' && (
          <>
            {!currentBuilding ? (
              <section className="panel building-list-panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">CAMPUS DIRECTORY</p>
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

                  <div className="building-summary">
                    <span className="building-card-id">BUILDING {currentBuilding.building_id}</span>
                    <span>{currentBuilding.floors.length} floors · {currentBuilding.floors.reduce((count, floor) => count + floor.rooms.length, 0)} rooms</span>
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
                          <span className="subtle">{currentFloor.rooms.length} campus rooms</span>
                        </div>
                        <span className="status-badge neutral">{currentBuilding.building_id}</span>
                      </div>
                      <label className="room-search">Find a room<input type="search" value={roomQuery} onChange={(event) => setRoomQuery(event.target.value)} placeholder="Name, room, or department" /></label>
                      {simulationAffectedRoomIds.length > 0 && <p className="simulation-legend">Outlined rooms are affected by the latest proposed scenario.</p>}
                      <div className="floor-grid" aria-label={`${currentFloor.floor_name} rooms`}>
                        {visibleRooms.map((room) => (
                          <button
                            type="button"
                            key={room.room_id}
                            className={`room-card ${getRoomStatusClass(room)} ${room.room_id === selectedRoom?.room_id ? 'selected' : ''} ${simulationAffectedRoomIds.includes(room.room_id) ? 'simulation-affected' : ''}`}
                            aria-pressed={room.room_id === selectedRoom?.room_id}
                            onClick={() => {
                              clearVisionEstimate();
                              setSelectedRoomId(room.room_id);
                            }}
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
                        {visibleRooms.length === 0 && <p className="empty-note">No rooms match this search.</p>}
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
                      <span className="status-badge neutral">Campus schedule</span>
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

        {activeSection === 'occupancy' && (
          <section className="panel workspace-panel">
            <div className="panel-header"><div><p className="eyebrow">CLASSROOM VISION</p><h2>Estimate visible people in an image</h2></div><span className="status-badge neutral">Image snapshot</span></div>
            <p className="subtle">Choose a room and upload a JPEG or PNG image. The image is processed temporarily and is not saved.</p>
            <div className="workspace-grid">
              <div className="upload-card">
                <label>Classroom<select value={selectedRoom?.room_id ?? ''} onChange={(event) => {
                  const room = allRooms.find((item) => item.room_id === event.target.value);
                  if (room) {
                    clearVisionEstimate();
                    setSelectedBuildingId(room.building_id);
                    setSelectedFloorNumber(room.floor_number);
                    setSelectedRoomId(room.room_id);
                  }
                }}>{allRooms.map((room) => <option key={room.room_id} value={room.room_id}>{room.room_id} · {room.room_name}</option>)}</select></label>
                <label className="upload-zone">Choose classroom image<input type="file" accept="image/jpeg,image/png" onChange={(event) => chooseVisionImage(event.target.files?.[0])} /></label>
                {visionError && <p className="form-error" role="alert">{visionError}</p>}
                <button type="button" className="primary-button" onClick={runVision} disabled={!visionImage || visionLoading}>{visionLoading ? 'Analysing image…' : visionResult ? 'Analyse another image' : 'Estimate occupancy'}</button>
              </div>
              {visionPreview ? (
                <div className="vision-preview">
                  <img src={visionPreview} alt="Selected classroom" />
                  {visionLoading && <div className="preview-loading" role="status">Analysing image…</div>}
                  {visionResult?.estimate?.detections?.map((detection, index) => <span key={index} className="detection-box" style={{ left: `${(detection.x / (visionResult.estimate.image_width || 1)) * 100}%`, top: `${(detection.y / (visionResult.estimate.image_height || 1)) * 100}%`, width: `${(detection.width / (visionResult.estimate.image_width || 1)) * 100}%`, height: `${(detection.height / (visionResult.estimate.image_height || 1)) * 100}%` }} />)}
                </div>
              ) : (
                <div className="vision-preview vision-preview-empty">
                  <span className="preview-icon" aria-hidden="true">＋</span>
                  <strong>Image preview</strong>
                  <span>Your selected room image will appear here.</span>
                </div>
              )}
            </div>
            {visionResult && visionObservation && <div className="vision-result"><strong>{visionObservation.estimated_visible_person_count} visible people estimated</strong><span>{visionObservation.room_name} ({visionObservation.room_id}) · {formatTimestamp(visionObservation.observed_at)}</span><p>This is a count of detections in this image. Actual room occupancy may differ, and this estimate is not class enrollment or attendance.</p><p>Detector: {visionObservation.model}. Image-based estimate; not a live sensor reading.</p>{visionResult.estimate.limitations?.map((limitation) => <small key={limitation}>{limitation}</small>)}</div>}
            {visionObservation && <div className="dashboard-summary"><div><h3>Observation retained</h3><p>{visionObservation.estimated_visible_person_count} visible people estimated in {visionObservation.room_name} at {formatTimestamp(visionObservation.observed_at)}. It stays separate from enrollment when you start a new simulation.</p></div><button type="button" className="secondary-button" onClick={() => setActiveSection('simulation')}>Open Simulation Studio</button></div>}
          </section>
        )}

        {activeSection === 'assistant' && (
          <section className="panel workspace-panel">
            <div className="panel-header"><div><p className="eyebrow">CAMPUS ASSISTANT</p><h2>Ask about your campus</h2></div><span className="status-badge neutral">Grounded in campus records</span></div>
            <div className="suggestion-row">{['Which rooms could fit a class of 30?', 'Why might a relocation be rejected?', 'What data is needed to estimate energy savings?'].map((prompt) => <button type="button" className="suggestion-chip" key={prompt} onClick={() => setQuestion(prompt)}>{prompt}</button>)}</div>
            <form className="chat-form" onSubmit={submitQuestion}><label htmlFor="campus-question">Your question</label><textarea id="campus-question" rows="4" maxLength="2000" value={question} onChange={(event) => setQuestion(event.target.value)} required /><button className="primary-button" disabled={chatLoading || !question.trim()}>{chatLoading ? 'Preparing an answer…' : 'Ask EcoTwin'}</button></form>
            {chatError && <p className="form-error" role="alert">{chatError}</p>}
            {chatResult && <article className="assistant-answer"><span className="status-badge neutral">{responseSourceLabel(chatResult)}</span><p>{chatResult.answer}</p><small>Based on campus records; some data is illustrative. Scheduling decisions remain subject to the deterministic checks.</small></article>}
          </section>
        )}

        {activeSection === 'simulation' && (
          <div className="bottom-grid">
            <section className="panel simulation-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">REQUEST WORKSPACE</p>
                  <h2>Simulation request</h2>
                </div>
                <span className="status-badge neutral">Timetable relocation</span>
              </div>
              <form className="simulation-form" onSubmit={runSimulation}>
                <label>
                  Timetable entry
                  <select value={timetableEntryId} onChange={(event) => setTimetableEntryId(event.target.value)} required>
                    <option value="">Select a scheduled class</option>
                    {campusData.timetable.map((entry) => (
                      <option key={entry.timetable_entry_id} value={entry.timetable_entry_id}>
                        {entry.timetable_entry_id} | {entry.subject} | {entry.section} | {entry.room_id} | {entry.day} {entry.start_time}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="empty-note">
                  Source room: {selectedTimetableEntry?.room_id ?? 'Select a timetable entry'}.
                  {selectedTimetableEntry
                    ? ` ${selectedTimetableEntry.day}, ${selectedTimetableEntry.start_time}-${selectedTimetableEntry.end_time}, semester ${selectedTimetableEntry.semester}.`
                    : ''}
                </p>
                <label>
                  Destination room
                  <select value={targetRoomId} onChange={(event) => setTargetRoomId(event.target.value)} required>
                    <option value="">Select destination room</option>
                    {allRooms.map((room) => (
                      <option key={room.room_id} value={room.room_id}>
                        {room.room_id} | {room.room_name} | capacity {room.capacity ?? 'unknown'}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Class enrollment (required for capacity check)
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={studentCount}
                    onChange={(event) => setStudentCount(event.target.value)}
                    required
                  />
                </label>
                <p className="empty-note">Enter the enrolled class size. A visible-person image estimate is a separate observation and will never fill this value.</p>
                {visionObservation && <div className="occupancy-context-card">
                  <strong>Image observation available</strong>
                  <span>{visionObservation.estimated_visible_person_count} visible people · {visionObservation.room_name} ({visionObservation.room_id})</span>
                  <small>Image-based estimate from {formatTimestamp(visionObservation.observed_at)}. It is not enrollment and is excluded from capacity checks.</small>
                  <label className="scenario-check"><input type="checkbox" checked={includeOccupancyContext} onChange={(event) => setIncludeOccupancyContext(event.target.checked)} />Include this observation as scenario context only</label>
                  {includeOccupancyContext && ![selectedTimetableEntry?.room_id, targetRoomId].includes(visionObservation.room_id) && <small className="form-error">Choose a timetable entry or destination room that matches this observation before running the scenario.</small>}
                </div>}
                <label>
                  Class sizes for additional room changes
                    <textarea
                    rows="3"
                    value={affectedStudentCountsText}
                    onChange={(event) => setAffectedStudentCountsText(event.target.value)}
                      placeholder="TT0031=25"
                    aria-describedby="cascade-counts-help"
                  />
                </label>
                <p id="cascade-counts-help" className="empty-note">
                  Enter a timetable ID and its known class size on each line, for example TT0031=25.
                  Without a size, the evaluator will mark that reassignment incomplete rather than assume capacity.
                </p>
                <button type="submit" className="primary-button" disabled={simulationLoading}>
                  {simulationLoading ? 'Evaluating...' : 'Evaluate relocation'}
                </button>
                <p className="empty-note">
                  This deterministic check moves one scheduled entry, preserving its semester, section, day, and time.
                  Conflicting entries may be reassigned if their known class sizes are supplied. Energy and walking impacts
                  are not calculated from the available records.
                </p>
                {simulationError && <p className="form-error" role="alert">{simulationError}</p>}
              </form>
            </section>

            <section className="panel results-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">RESULTS</p>
                  <h2>Comparison results</h2>
                </div>
                <span className={`status-badge ${simulationResult?.status === 'feasible' ? 'success' : simulationResult?.status === 'infeasible' ? 'danger' : 'neutral'}`}>
                  {simulationResult?.status ?? 'No result yet'}
                </span>
              </div>
              {simulationResult ? (
                <>
                  <div className={`verdict-banner ${simulationResult.status}`}>
                    <span className="verdict-label">Authoritative simulator verdict</span>
                    <strong>{simulationResult.status === 'feasible' ? 'Feasible proposal' : simulationResult.status === 'infeasible' ? 'Infeasible proposal' : 'More information required'}</strong>
                    <span>{simulationResult.status === 'feasible' ? 'All evaluated checks passed. This proposal is not an approval or a schedule change.' : simulationResult.status === 'infeasible' ? 'One or more evaluated constraints failed. Review the checks below.' : 'Some required information is unavailable, so feasibility cannot be confirmed.'}</span>
                  </div>
                  <div className="comparison-grid">
                    <div className="scenario-card baseline">
                      <h3>Baseline schedule</h3>
                      <ul>
                        <li>Timetable entry: {simulationResult.scenario_inputs.timetable_entry_id}</li>
                        <li>Room: {simulationResult.baseline.room_id}</li>
                        <li>Class size: {simulationResult.scenario_inputs.student_count ?? 'Not provided'}</li>
                      </ul>
                    </div>
                    <div className="scenario-card proposed">
                      <h3>Proposed schedule</h3>
                      <ul>
                        <li>Room: {simulationResult.proposed.room_id}</li>
                        <li>Feasibility: {simulationResult.feasible === null ? 'Incomplete' : simulationResult.feasible ? 'Feasible' : 'Infeasible'}</li>
                        <li>Data source: {simulationResult.data_classification === 'synthetic_or_illustrative' ? 'Demo campus records' : 'Campus records'}</li>
                      </ul>
                    </div>
                  </div>
                  <h3>Effects and affected entries</h3>
                  {simulationResult.effects.length > 0 ? (
                    <ul>
                      {simulationResult.effects.map((effect) => (
                        <li key={effect.timetable_entry_id}>
                          {effect.effect_type === 'primary_relocation' ? 'Primary move' : 'Cascading move'}:
                          {' '}{effect.timetable_entry_id} from {effect.from_room_id} to {effect.to_room_id} ({effect.status})
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="empty-note">No room assignment change was resolved.</p>
                  )}
                  <p><strong>Affected rooms:</strong> {simulationResult.projected_metrics.affected_room_ids.join(', ') || 'None'}</p>
                  <p><strong>Moved entries:</strong> {simulationResult.projected_metrics.moved_entry_count};
                    cascading moves: {simulationResult.projected_metrics.cascaded_entry_count}</p>
                  <p className="empty-note">{simulationResult.projected_metrics.utilization_definition}</p>
                  {simulationResult.projected_metrics.class_capacity_utilization.map((metric) => (
                    <p key={metric.timetable_entry_id}>
                      <strong>{metric.timetable_entry_id} class capacity utilization:</strong>
                      {' '}{metric.baseline.allocation_utilization_percent ?? 'Unknown'}% in {metric.baseline.room_id}
                      {' -> '}{metric.projected.allocation_utilization_percent ?? 'Unknown'}% in {metric.projected.room_id}
                    </p>
                  ))}
                  <h3>Validation checks</h3>
                  <ul>
                    {Object.entries(simulationResult.checks).map(([name, check]) => (
                      <li key={name}>{name.replaceAll('_', ' ')}: {check.status} - {check.message}</li>
                    ))}
                  </ul>
                  {simulationResult.validation_errors.length > 0 && (
                    <ul className="form-error">
                      {simulationResult.validation_errors.map((error) => <li key={error}>{error}</li>)}
                    </ul>
                  )}
                  <p><strong>Energy impact:</strong> {simulationResult.energy_impact.status} - {simulationResult.energy_impact.reason}</p>
                  <p><strong>Cost impact:</strong> {simulationResult.cost_impact.status} - {simulationResult.cost_impact.reason}</p>
                  <p><strong>Walking impact:</strong> {simulationResult.walking_impact.status} - {simulationResult.walking_impact.reason}</p>
                  {simulationResult.scenario_inputs.occupancy_scenario && <div className="occupancy-context-card">
                    <strong>Image observation included as context</strong>
                    <span>{simulationResult.scenario_inputs.occupancy_scenario.estimated_visible_person_count} visible people · {simulationResult.scenario_inputs.occupancy_scenario.room_id} · {formatTimestamp(simulationResult.scenario_inputs.occupancy_scenario.observed_at)}</span>
                    <small>Not used as class enrollment or in the capacity check.</small>
                  </div>}
                  {simulationExplanation && (
                    <div className="info-block">
                      <h3>{responseSourceLabel(simulationExplanation)}</h3>
                      <p><strong>Authoritative simulator verdict:</strong> {simulationExplanation.authoritative_status ?? simulationResult.status}</p>
                      <p>{simulationExplanation.explanation}</p>
                      <p><strong>Verification step:</strong> {simulationExplanation.next_step}</p>
                    </div>
                  )}
                  {explanationError && <p className="form-error" role="alert">{explanationError}</p>}
                </>
              ) : (
                <p className="empty-note">Submit a timetable relocation to see its capacity and schedule checks.</p>
              )}
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
                <span className="status-badge neutral">Campus actions</span>
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
                    <p><strong>Source:</strong> {recordSourceLabel(action.data_status)}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel insights-panel ai-results-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">ROOM INSIGHTS</p>
                  <h2>Campus recommendations</h2>
                </div>
                <span className="status-badge neutral">{displayedRecommendations.length} shown</span>
              </div>
              {campusData.recommendations.length > 0 && (
                <>
                  <label className="recommendation-search">
                    Find a recommendation
                    <input type="search" value={recommendationQuery} onChange={(event) => {
                      setRecommendationQuery(event.target.value);
                      setRecommendationLimit(10);
                    }} placeholder="Search by room, evidence, or action" />
                  </label>
                  <p className="subtle recommendation-count">
                    Showing {displayedRecommendations.length} of {visibleRecommendations.length} matching recommendations
                    ({campusData.recommendations.length} total).
                  </p>
                </>
              )}
              {displayedRecommendations.length > 0 ? (
                <div className="action-list">
                  {displayedRecommendations.map((recommendation) => (
                    <article className="action-card" key={recommendation.recommendation_id}>
                      <div className="action-header">
                        <h3>{recommendation.title}</h3>
                        <span>{recommendation.requires_verification ? 'Verify' : 'Review'}</span>
                      </div>
                      <p><strong>Room:</strong> {recommendation.room_id || 'Campus-wide'}</p>
                      <p><strong>Evidence:</strong> {recommendation.evidence.join('; ') || 'No supporting record specified'}</p>
                      <p><strong>Source:</strong> {recordSourceLabel(recommendation.data_source)}</p>
                      <details className="recommendation-details">
                        <summary>Next step and limitations</summary>
                        <p><strong>Next step:</strong> {recommendation.suggested_next_step}</p>
                        <p><strong>Limitations:</strong> {recommendation.confidence_limitations.join('; ') || 'None specified'}</p>
                      </details>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="empty-note">{campusData.recommendations.length ? 'No recommendations match this search.' : 'The backend returned no recommendations for the available records.'}</p>
              )}
              {displayedRecommendations.length < visibleRecommendations.length && (
                <button type="button" className="secondary-button show-more-button" onClick={() => setRecommendationLimit((limit) => limit + 10)}>
                  Show 10 more recommendations
                </button>
              )}
            </section>
          </>
        )}
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
              <li>Source: {recordSourceLabel(observation.data_status)}</li>
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
