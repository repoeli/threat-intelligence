import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app


def test_openapi_schema_snapshot():
    client = TestClient(app)
    response = client.get('/openapi.json')
    assert response.status_code == 200
    current_schema = response.json()
    schema_path = Path(__file__).parent / 'schemas' / 'openapi.json'
    stored_schema = json.loads(schema_path.read_text())
    assert current_schema == stored_schema
