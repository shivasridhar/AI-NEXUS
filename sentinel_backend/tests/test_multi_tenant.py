import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_db, get_current_active_user
from app.models.tenant import Organization, Workspace, User
from app.models.machine_identity import MachineIdentity

client = TestClient(app)

@pytest.fixture
def setup_database(postgres_db):
    db = postgres_db
    
    # Create Tenant A
    org_a = Organization(name="Org A", slug="org-a")
    db.add(org_a)
    db.commit()
    ws_a = Workspace(organization_id=org_a.id, name="Workspace A")
    db.add(ws_a)
    user_a = User(organization_id=org_a.id, full_name="User A", email="usera@example.com", password_hash="hash")
    db.add(user_a)
    db.commit()
    
    # Create Tenant B
    org_b = Organization(name="Org B", slug="org-b")
    db.add(org_b)
    db.commit()
    ws_b = Workspace(organization_id=org_b.id, name="Workspace B")
    db.add(ws_b)
    user_b = User(organization_id=org_b.id, full_name="User B", email="userb@example.com", password_hash="hash")
    db.add(user_b)
    db.commit()
    
    # Create Identity for Tenant A
    ident_a = MachineIdentity(workspace_id=ws_a.id, arn="arn:aws:iam::111:user/A", identity_type="IAMUser", account_id="111")
    db.add(ident_a)
    db.commit()
    
    yield {"user_a": user_a, "user_b": user_b, "ws_a": ws_a, "ws_b": ws_b, "ident_a": ident_a}

@pytest.mark.pg
def test_tenant_isolation(postgres_db, setup_database):
    # Override get_db to use our testcontainer DB
    app.dependency_overrides[get_db] = lambda: postgres_db
    data = setup_database
    
    # Override current user to User B
    app.dependency_overrides[get_current_active_user] = lambda: data["user_b"]
    
    # User B requests identities
    response = client.get(
        "/api/v1/identities", 
        headers={"x-workspace-id": str(data["ws_b"].id)}
    )
    assert response.status_code == 200
    identities = response.json()
    
    # User B should NOT see User A's identity
    for ident in identities:
        assert ident["arn"] != "arn:aws:iam::111:user/A"
        
    assert len(identities) == 0 # User B has no identities
    
    # Override current user to User A
    app.dependency_overrides[get_current_active_user] = lambda: data["user_a"]
    
    # User A requests identities
    response = client.get(
        "/api/v1/identities", 
        headers={"x-workspace-id": str(data["ws_a"].id)}
    )
    assert response.status_code == 200
    identities = response.json()
    
    # User A SHOULD see User A's identity
    assert len(identities) == 1
    assert identities[0]["arn"] == "arn:aws:iam::111:user/A"
