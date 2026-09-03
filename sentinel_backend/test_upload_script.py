import pytest
import requests
import os

@pytest.fixture(scope="module")
def api_base_url():
    return 'http://127.0.0.1:8000/api/v1'

@pytest.fixture(scope="module")
def check_backend():
    try:
        requests.get('http://127.0.0.1:8000/docs', timeout=2)
    except requests.ConnectionError:
        pytest.skip("Backend is unavailable, skipping integration tests.")

def test_upload_script(check_backend, api_base_url):
    register_data = {
        "email": "test2@example.com",
        "password": "Password12345!",
        "full_name": "Test User",
        "organization_name": "Test Co 2",
        "workspace_name": "Default 2"
    }
    res_reg = requests.post(f'{api_base_url}/auth/register', json=register_data)
    if res_reg.status_code not in (201, 400):
        pytest.fail(f"Register failed: {res_reg.text}")

    # Login
    login_data = {
        "email": "test2@example.com",
        "password": "Password12345!"
    }
    res = requests.post(f'{api_base_url}/auth/login', json=login_data)
    if res.status_code != 200:
        pytest.fail(f"Login failed: {res.text}")
    token = res.json()["access_token"]

    # Get workspace
    res = requests.get(f'{api_base_url}/organizations/me', headers={"Authorization": f"Bearer {token}"})
    if res.status_code != 200:
        pytest.fail(f"Failed to fetch organization: {res.text}")
        
    org_data = res.json()
    workspace_id = None
    if "workspace" in org_data:
        workspace_id = org_data["workspace"]["id"]
    elif "workspaces" in org_data and len(org_data["workspaces"]) > 0:
        workspace_id = org_data["workspaces"][0]["id"]
        
    if not workspace_id:
        pytest.fail("No workspace found")

    # Upload file
    sample_path = os.path.join(os.path.dirname(__file__), '../valid_sample.json')
    if not os.path.exists(sample_path):
        pytest.skip("valid_sample.json not found, skipping upload test.")
        
    with open(sample_path, 'rb') as f:
        files = {'file': ('valid_sample.json', f, 'application/json')}
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Workspace-ID': workspace_id
        }
        res = requests.post(f'{api_base_url}/ingestion/upload', files=files, headers=headers)
        
    assert res.status_code in (200, 201), f"Upload response: {res.status_code} {res.text}"

