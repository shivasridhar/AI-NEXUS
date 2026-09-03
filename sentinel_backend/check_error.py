from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.get("/api/v1/auth/me") # No token
print("401 Response:", response.json())

response = client.post("/api/v1/integrations/aws", json={}) # Missing payload/validation
print("422 Response:", response.json())
