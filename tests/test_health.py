def test_database_initialization_creates_tables(test_engine):
    with test_engine.connect() as connection:
        table_names = set(test_engine.dialect.get_table_names(connection))
    assert {"buildings", "rooms", "timetable"} <= table_names


def test_health_reports_database_connectivity(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_cors_allows_deployed_frontend_origin(client):
    response = client.options(
        "/api/buildings",
        headers={
            "Origin": "https://campusdigitaltwin.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://campusdigitaltwin.vercel.app"


def test_cors_does_not_allow_unconfigured_frontend_origin(client):
    response = client.options(
        "/api/buildings",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers
