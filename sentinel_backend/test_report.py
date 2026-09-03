import pytest
import requests

@pytest.fixture(scope="module")
def api_base_url():
    return 'http://127.0.0.1:8000/api/v1'

@pytest.fixture(scope="module")
def check_backend():
    try:
        requests.get('http://127.0.0.1:8000/docs', timeout=2)
    except requests.ConnectionError:
        pytest.skip("Backend is unavailable, skipping integration tests.")

def test_report_generation(check_backend, api_base_url):
    register_data = {
        "email": "testreport4@example.com",
        "password": "Password123456!",
        "full_name": "Test User",
        "organization_name": "Test Co 4",
        "workspace_name": "Default 4"
    }
    res_reg = requests.post(f'{api_base_url}/auth/register', json=register_data)
    
    # Ignore 400 since it might already exist
    if res_reg.status_code not in (201, 400):
        pytest.fail(f"Register failed: {res_reg.text}")

    login_data = {
        "email": "testreport4@example.com",
        "password": "Password123456!"
    }
    res = requests.post(f'{api_base_url}/auth/login', json=login_data)
    if res.status_code != 200:
        pytest.fail(f"Login failed: {res.text}")
        
    token = res.json()["access_token"]
    
    # Get workspace ID
    # Note: Using the updated schema /organizations/me gives back 'workspaces' array
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

    payload = {
        "name": "Test Report",
        "report_type": "executive",
        "filters": {}
    }
    headers = {
        'Authorization': f'Bearer {token}',
        'X-Workspace-ID': workspace_id
    }
    res = requests.post(f'{api_base_url}/reports/generate', json=payload, headers=headers)
    
    assert res.status_code in (200, 201), f"Report generation failed: {res.text}"

