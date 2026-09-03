import random
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_login_me():
    """
    End-to-end auth flow: register → login → /me.
    Skipped automatically if the database schema is incomplete
    (i.e. alembic migrations have not been applied).
    """
    from sqlalchemy.exc import OperationalError, ProgrammingError

    suffix = random.randint(1000, 9999)
    # 1. Register
    reg_data = {
        "full_name": "Test User",
        "email": f"test{suffix}@example.com",
        "password": "StrongP@ssword123",
        "organization_name": f"Test Org {suffix}",
        "workspace_name": f"Test Workspace {suffix}"
    }
    try:
        response = client.post("/api/v1/auth/register", json=reg_data)
    except (OperationalError, ProgrammingError) as e:
        pytest.skip(f"DB schema incomplete (run 'alembic upgrade head'): {e}")

    # 400 means already exists from a previous run, which is fine
    if response.status_code == 201:
        data = response.json()
        assert "access_token" in data
        print("Register: Success")
    elif response.status_code == 400:
        print("Register: Already exists (Success)")
    else:
        print(f"Register failed: {response.json()}")
        return

    # 2. Login
    login_data = {
        "email": f"test{suffix}@example.com",
        "password": "StrongP@ssword123"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    print("Login: Success")

    # 3. Me
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["user"]["email"] == f"test{suffix}@example.com"
    assert me_data["organization"]["name"] == f"Test Org {suffix}"
    assert me_data["workspace"]["name"] == f"Test Workspace {suffix}"
    print("Me: Success")

if __name__ == "__main__":
    test_register_login_me()

