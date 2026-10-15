def test_database_initialization_creates_tables(test_engine):
    with test_engine.connect() as connection:
        table_names = set(test_engine.dialect.get_table_names(connection))
    assert {"buildings", "rooms", "timetable"} <= table_names


def test_health_reports_database_connectivity(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
