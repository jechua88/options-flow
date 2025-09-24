from __future__ import annotations

from fastapi.testclient import TestClient

from option_flow.api.main import app


def test_top_endpoint_returns_rows():
    client = TestClient(app)
    response = client.get('/top')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data, 'expected at least one row in demo dataset'


def test_export_csv_returns_payload():
    client = TestClient(app)
    response = client.get('/export.csv')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/csv')
    assert 'symbol' in response.text
