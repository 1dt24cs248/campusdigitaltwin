export const campusData = {
  campus_name: 'EcoTwin AI Demonstration Campus',
  data_status: 'Synthetic demonstration data — canonical CSV package not present in this repository',
  buildings: [
    {
      building_id: 'A_BLOCK',
      building_name: 'A Block',
      floors: [
        {
          floor_number: -1,
          floor_name: 'Basement',
          rooms: [
            {
              room_id: 'A-BM-01',
              room_name: 'Research Lab',
              facility_type: 'Laboratory',
              department: 'Computer Science',
              capacity: 42,
              equipment: ['Workstations', 'Projector', 'Air quality sensor'],
              room_status: 'Occupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 8.2,
              latest_occupancy: {
                observed_person_count: 31,
                occupancy_percentage: 74,
                observation_timestamp: '2026-10-15T09:15:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.88,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'CS101 | CS102 | A1',
              energy_estimate_kwh: 37.5,
              illustrative_cost: 42.6,
              source_label: 'Demo fixture aligned to canonical schema'
            },
            {
              room_id: 'A-BM-02',
              room_name: 'Storage Annex',
              facility_type: 'Support facility',
              department: 'Operations',
              capacity: 18,
              equipment: ['Storage racks', 'Charging stations'],
              room_status: 'Unoccupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 2.1,
              latest_occupancy: {
                observed_person_count: 4,
                occupancy_percentage: 22,
                observation_timestamp: '2026-10-15T08:45:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.71,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'Support room',
              energy_estimate_kwh: 11.3,
              illustrative_cost: 12.8,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 0,
          floor_name: 'Ground Floor',
          rooms: [
            {
              room_id: 'A-101',
              room_name: 'Lecture Hall A1',
              facility_type: 'Lecture theatre',
              department: 'Computer Science',
              capacity: 120,
              equipment: ['Projector', 'Wireless mic', 'Lecture capture'],
              room_status: 'Occupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 12.4,
              latest_occupancy: {
                observed_person_count: 68,
                occupancy_percentage: 57,
                observation_timestamp: '2026-10-15T10:05:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.9,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'CS101 | 09:00 - 10:30',
              energy_estimate_kwh: 61.7,
              illustrative_cost: 70.1,
              source_label: 'Demo fixture aligned to canonical schema'
            },
            {
              room_id: 'A-102',
              room_name: 'Innovation Studio',
              facility_type: 'Studio',
              department: 'Design',
              capacity: 48,
              equipment: ['Smart board', '3D printers', 'Collaborative tables'],
              room_status: 'Moderate',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 8.7,
              latest_occupancy: {
                observed_person_count: 29,
                occupancy_percentage: 60,
                observation_timestamp: '2026-10-15T09:40:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.83,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'DES201 | 11:00 - 12:15',
              energy_estimate_kwh: 43.2,
              illustrative_cost: 49.0,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 1,
          floor_name: 'First Floor',
          rooms: [
            {
              room_id: 'A-201',
              room_name: 'Seminar Room 1',
              facility_type: 'Seminar room',
              department: 'Mechanical',
              capacity: 60,
              equipment: ['Display wall', 'Whiteboard', 'Video conferencing'],
              room_status: 'Occupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 9.5,
              latest_occupancy: {
                observed_person_count: 42,
                occupancy_percentage: 70,
                observation_timestamp: '2026-10-15T11:00:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.86,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'ME211 | 10:45 - 12:00',
              energy_estimate_kwh: 52.8,
              illustrative_cost: 59.7,
              source_label: 'Demo fixture aligned to canonical schema'
            },
            {
              room_id: 'A-202',
              room_name: 'Programming Lab',
              facility_type: 'Laboratory',
              department: 'Computer Science',
              capacity: 36,
              equipment: ['Developer workstations', 'Dual displays'],
              room_status: 'Occupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 7.9,
              latest_occupancy: {
                observed_person_count: 31,
                occupancy_percentage: 86,
                observation_timestamp: '2026-10-15T09:55:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.91,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'CS250 | 09:30 - 11:00',
              energy_estimate_kwh: 41.4,
              illustrative_cost: 47.1,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 2,
          floor_name: 'Second Floor',
          rooms: [
            {
              room_id: 'A-301',
              room_name: 'CAD Studio',
              facility_type: 'Studio',
              department: 'Civil',
              capacity: 32,
              equipment: ['CAD workstations', 'Plotter'],
              room_status: 'Moderate',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 6.8,
              latest_occupancy: {
                observed_person_count: 18,
                occupancy_percentage: 56,
                observation_timestamp: '2026-10-15T12:10:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.82,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'CE240 | 12:00 - 13:30',
              energy_estimate_kwh: 30.9,
              illustrative_cost: 35.0,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 3,
          floor_name: 'Third Floor',
          rooms: [
            {
              room_id: 'A-401',
              room_name: 'Research Forum',
              facility_type: 'Conference room',
              department: 'Research',
              capacity: 28,
              equipment: ['Display screen', 'Whiteboard', 'Recording kit'],
              room_status: 'Unoccupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 4.1,
              latest_occupancy: {
                observed_person_count: 8,
                occupancy_percentage: 29,
                observation_timestamp: '2026-10-15T08:30:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.74,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'Research review | 14:00 - 15:15',
              energy_estimate_kwh: 18.5,
              illustrative_cost: 20.9,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 4,
          floor_name: 'Fourth Floor',
          rooms: [
            {
              room_id: 'A-501',
              room_name: 'Project Room',
              facility_type: 'Project room',
              department: 'Engineering',
              capacity: 24,
              equipment: ['Wall monitor', 'Meeting table'],
              room_status: 'Occupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 3.7,
              latest_occupancy: {
                observed_person_count: 17,
                occupancy_percentage: 71,
                observation_timestamp: '2026-10-15T10:50:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.84,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'ENG420 | 10:45 - 12:00',
              energy_estimate_kwh: 19.8,
              illustrative_cost: 22.5,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 5,
          floor_name: 'Fifth Floor',
          rooms: [
            {
              room_id: 'A-601',
              room_name: 'Innovation Hub',
              facility_type: 'Innovation space',
              department: 'Innovation Cell',
              capacity: 30,
              equipment: ['Display wall', 'Idea boards', 'Collaboration tables'],
              room_status: 'Moderate',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 5.1,
              latest_occupancy: {
                observed_person_count: 14,
                occupancy_percentage: 47,
                observation_timestamp: '2026-10-15T09:20:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.8,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'Incubator session | 13:00 - 14:30',
              energy_estimate_kwh: 22.3,
              illustrative_cost: 25.3,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        }
      ]
    },
    {
      building_id: 'B_BLOCK',
      building_name: 'B Block',
      floors: [
        {
          floor_number: -1,
          floor_name: 'Basement',
          rooms: [
            {
              room_id: 'B-BM-01',
              room_name: 'Server Room',
              facility_type: 'Infrastructure',
              department: 'IT',
              capacity: 10,
              equipment: ['Servers', 'UPS backup', 'Cooling'],
              room_status: 'Unoccupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 11.8,
              latest_occupancy: {
                observed_person_count: 2,
                occupancy_percentage: 20,
                observation_timestamp: '2026-10-15T07:55:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.69,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'Infrastructure support',
              energy_estimate_kwh: 44.2,
              illustrative_cost: 50.1,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 0,
          floor_name: 'Ground Floor',
          rooms: [
            {
              room_id: 'B-101',
              room_name: 'Lecture Hall B1',
              facility_type: 'Lecture theatre',
              department: 'Electrical',
              capacity: 110,
              equipment: ['Projector', 'Audio array', 'Smart board'],
              room_status: 'Occupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 10.9,
              latest_occupancy: {
                observed_person_count: 73,
                occupancy_percentage: 66,
                observation_timestamp: '2026-10-15T09:10:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.89,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'EE205 | 08:45 - 10:00',
              energy_estimate_kwh: 58.6,
              illustrative_cost: 66.4,
              source_label: 'Demo fixture aligned to canonical schema'
            },
            {
              room_id: 'B-102',
              room_name: 'Electronics Lab',
              facility_type: 'Laboratory',
              department: 'Electronics',
              capacity: 40,
              equipment: ['Oscilloscopes', 'Workbench benches', 'DAQ units'],
              room_status: 'Moderate',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 8.3,
              latest_occupancy: {
                observed_person_count: 24,
                occupancy_percentage: 60,
                observation_timestamp: '2026-10-15T10:20:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.81,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'EE241 | 10:15 - 11:45',
              energy_estimate_kwh: 39.8,
              illustrative_cost: 45.1,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 1,
          floor_name: 'First Floor',
          rooms: [
            {
              room_id: 'B-201',
              room_name: 'Seminar Hall',
              facility_type: 'Seminar room',
              department: 'Administration',
              capacity: 70,
              equipment: ['Display wall', 'Hybrid AV', 'Wireless mic'],
              room_status: 'Unoccupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 9.2,
              latest_occupancy: {
                observed_person_count: 11,
                occupancy_percentage: 16,
                observation_timestamp: '2026-10-15T08:15:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.64,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'Admin briefing | 12:00 - 13:15',
              energy_estimate_kwh: 28.6,
              illustrative_cost: 32.4,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 2,
          floor_name: 'Second Floor',
          rooms: [
            {
              room_id: 'B-301',
              room_name: 'Applied Physics Lab',
              facility_type: 'Laboratory',
              department: 'Physics',
              capacity: 38,
              equipment: ['Lab benches', 'Sensors', 'Projector'],
              room_status: 'Occupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 7.4,
              latest_occupancy: {
                observed_person_count: 26,
                occupancy_percentage: 68,
                observation_timestamp: '2026-10-15T11:35:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.86,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'PHY230 | 11:30 - 13:00',
              energy_estimate_kwh: 34.9,
              illustrative_cost: 39.6,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 3,
          floor_name: 'Third Floor',
          rooms: [
            {
              room_id: 'B-401',
              room_name: 'Design Review Room',
              facility_type: 'Review room',
              department: 'Architecture',
              capacity: 26,
              equipment: ['Large display', 'Presentation desk', 'Whiteboard'],
              room_status: 'Occupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 4.3,
              latest_occupancy: {
                observed_person_count: 18,
                occupancy_percentage: 69,
                observation_timestamp: '2026-10-15T10:45:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.78,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'ARC310 | 10:30 - 12:00',
              energy_estimate_kwh: 20.5,
              illustrative_cost: 23.3,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 4,
          floor_name: 'Fourth Floor',
          rooms: [
            {
              room_id: 'B-501',
              room_name: 'Smart Classroom',
              facility_type: 'Classroom',
              department: 'Mathematics',
              capacity: 50,
              equipment: ['Interactive panel', 'Projector', 'Recording kit'],
              room_status: 'Moderate',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 6.6,
              latest_occupancy: {
                observed_person_count: 25,
                occupancy_percentage: 50,
                observation_timestamp: '2026-10-15T09:45:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.8,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'MTH201 | 09:30 - 10:45',
              energy_estimate_kwh: 31.7,
              illustrative_cost: 36.0,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        },
        {
          floor_number: 5,
          floor_name: 'Fifth Floor',
          rooms: [
            {
              room_id: 'B-601',
              room_name: 'Research Commons',
              facility_type: 'Study space',
              department: 'Library',
              capacity: 34,
              equipment: ['Collaborative tables', 'Display screen'],
              room_status: 'Unoccupied',
              data_status: 'Synthetic demonstration',
              estimated_connected_load_kw: 3.6,
              latest_occupancy: {
                observed_person_count: 8,
                occupancy_percentage: 24,
                observation_timestamp: '2026-10-15T08:20:00Z',
                detection_method: 'Synthetic observation placeholder',
                confidence_score: 0.7,
                verification_status: 'Synthetic sample',
                data_status: 'Synthetic demonstration data'
              },
              timetable: 'Open study | 09:00 - 17:00',
              energy_estimate_kwh: 16.1,
              illustrative_cost: 18.3,
              source_label: 'Demo fixture aligned to canonical schema'
            }
          ]
        }
      ]
    }
  ],
  timetable: [
    {
      semester: '2026-27',
      section: 'A1',
      department: 'Computer Science',
      day: 'Monday',
      period: 'P1',
      start_time: '09:00',
      end_time: '10:15',
      subject: 'CS101',
      room_id: 'A-101',
      building_id: 'A_BLOCK',
      room_name: 'Lecture Hall A1',
      session_type: 'Lecture',
      data_status: 'Synthetic demonstration data'
    },
    {
      semester: '2026-27',
      section: 'A1',
      department: 'Computer Science',
      day: 'Monday',
      period: 'P2',
      start_time: '10:30',
      end_time: '11:45',
      subject: 'CS250',
      room_id: 'A-202',
      building_id: 'A_BLOCK',
      room_name: 'Programming Lab',
      session_type: 'Practical',
      data_status: 'Synthetic demonstration data'
    },
    {
      semester: '2026-27',
      section: 'B1',
      department: 'Electrical',
      day: 'Tuesday',
      period: 'P3',
      start_time: '11:00',
      end_time: '12:15',
      subject: 'EE205',
      room_id: 'B-101',
      building_id: 'B_BLOCK',
      room_name: 'Lecture Hall B1',
      session_type: 'Lecture',
      data_status: 'Synthetic demonstration data'
    }
  ],
  simulationScenarios: [
    {
      scenario_id: 'SIM-001',
      scenario_name: 'Baseline relocation test',
      source_room_id: 'A-101',
      target_room_id: 'A-102',
      status: 'Pending backend validation',
      baseline_energy_kwh: 61.7,
      proposed_energy_kwh: 57.8,
      notes: 'Example scenario used for UI demonstration only, not a verified simulation result.',
      data_status: 'Example fixture only'
    },
    {
      scenario_id: 'SIM-002',
      scenario_name: 'High-usage scheduling test',
      source_room_id: 'B-101',
      target_room_id: 'B-201',
      status: 'Awaiting simulator contract',
      baseline_energy_kwh: 58.6,
      proposed_energy_kwh: 53.4,
      notes: 'Example scenario used for UI demonstration only, not a verified simulation result.',
      data_status: 'Example fixture only'
    }
  ],
  sustainabilityActions: [
    {
      action_id: 'ACT-001',
      action_name: 'Shift low-usage session to underutilized room',
      category: 'Scheduling',
      priority: 'Medium',
      trigger_condition: 'Room occupancy below 45% for two consecutive classes',
      suggested_action: 'Move the session to a closer, lower-demand room.',
      approval_required: 'No',
      status: 'Suggested',
      data_status: 'Synthetic demonstration data'
    },
    {
      action_id: 'ACT-002',
      action_name: 'Switch off idle AV equipment',
      category: 'Energy',
      priority: 'High',
      trigger_condition: 'Equipment stays idle during unassigned periods',
      suggested_action: 'Disable idle devices outside scheduled use windows.',
      approval_required: 'Yes',
      status: 'Suggested',
      data_status: 'Synthetic demonstration data'
    }
  ]
};
