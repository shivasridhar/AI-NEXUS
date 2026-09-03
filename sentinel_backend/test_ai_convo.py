import requests
import uuid

BASE_URL = "http://localhost:8000/api/v1"
rand_hex = uuid.uuid4().hex[:6]
TEST_EMAIL = f"test_ai_{rand_hex}@example.com"
TEST_PASSWORD = "Password1234!"
TEST_ORG = f"Test Org {rand_hex}"

def test():
    # 1. Register and login
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": "AI Tester",
        "organization_name": TEST_ORG,
        "workspace_name": "AI Workspace"
    })
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    token = res.json()["access_token"]
    
    # 2. Get Workspace ID
    res = requests.get(f"{BASE_URL}/organizations/me", headers={"Authorization": f"Bearer {token}"})
    workspace_id = res.json()["workspaces"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": workspace_id}

    # 3. Test POST /ai-conversations/
    payload = {
        "title": "Test AI Conversation",
        "identity_id": None,
        "message": {"role": "user", "content": "Hello AI"}
    }
    print(f"Calling POST /ai-conversations with headers: {headers}")
    res = requests.post(f"{BASE_URL}/ai-conversations/", json=payload, headers=headers)
    
    print(f"Status Code: {res.status_code}")
    if res.status_code in [200, 201]:
        print(f"Success! Response: {res.json()}")
    else:
        print(f"Error! Response: {res.text}")

if __name__ == "__main__":
    test()
