from fastapi.testclient import TestClient
from orchestration.router import app
client = TestClient(app)
response = client.post('/analyze/sync', json={'incident_id':'INC-999', 'alert_name':'db', 'severity':'high', 'service':'db'})
print(response.status_code)
print(response.json())
