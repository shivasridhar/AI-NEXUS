import requests
import json
import time
import uuid

BASE_URL = "http://localhost:8000/api/v1"
rand_hex = uuid.uuid4().hex[:6]
TEST_EMAIL = f"e2e_{rand_hex}@example.com"
TEST_PASSWORD = "Password1234!"
TEST_ORG = f"Test Org {rand_hex}"

def print_header(title):
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

def main():
    print_header("Phase 1: Authenticate")
    register_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": "E2E User",
        "organization_name": TEST_ORG,
        "workspace_name": "E2E Workspace"
    }
    res_reg = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    if res.status_code != 200:
        print("Reg:", res_reg.text); print("Login failed:", res.text)
        return
    token = res.json()["access_token"]
    print("Got token")
    
    res = requests.get(f"{BASE_URL}/organizations/me", headers={"Authorization": f"Bearer {token}"})
    workspace_id = res.json()["workspaces"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": workspace_id}

    print_header("Phase 2 & 3: Upload and Process Dataset")
    
    # 1. Upload the file
    print("Uploading sample_cloudtrail.json...")
    with open("sample_cloudtrail.json", "rb") as f:
        files = {"file": ("sample_cloudtrail.json", f, "application/json")}
        try:
            response = requests.post(f"{BASE_URL}/ingestion/upload", files=files, headers=headers)
            if response.status_code == 200 or response.status_code == 202:
                print(f"[PASS] Upload succeeded: {response.json()}")
            else:
                print(f"[FAIL] Upload failed. Status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[ERROR] {e}")

    # Wait for the job to complete
    job_id = None
    try:
        job_id = response.json().get("job_id")
    except Exception:
        pass
        
    if job_id:
        print(f"Waiting for background ingestion tasks for job {job_id} to complete...")
        import time
        max_attempts = 30
        for i in range(max_attempts):
            res = requests.get(f"{BASE_URL}/ingestion/jobs/{job_id}/status", headers=headers)
            if res.status_code == 200:
                data = res.json()
                status = data.get("status")
                print(f"Poll {i+1}: Status = {status}")
                if status == "completed":
                    print(f"[PASS] Job completed. Risk findings generated: {data.get('risk_findings_generated', 0)}")
                    break
                elif status == "failed":
                    print(f"[FAIL] Job failed. Error: {data.get('error_message')}")
                    break
            time.sleep(1)
    else:
        print("No job ID found, sleeping fallback...")
        import time
        time.sleep(3)

    
    print_header("Phase 4: Verify PostgreSQL")
    # We will use sqlalchemy directly to verify Postgres
    from app.db.session import SessionLocal
    from app.models import IngestionJob, MachineIdentity, AccessLog, RiskScore, RiskFinding
    
    try:
        db = SessionLocal()
        jobs_count = db.query(IngestionJob).count()
        identities_count = db.query(MachineIdentity).count()
        logs_count = db.query(AccessLog).count()
        scores_count = db.query(RiskScore).count()
        findings_count = db.query(RiskFinding).count()
        
        print(f"IngestionJobs: {jobs_count}")
        print(f"MachineIdentities: {identities_count}")
        print(f"AccessLogs: {logs_count}")
        print(f"RiskScores: {scores_count}")
        print(f"RiskFindings: {findings_count}")
        
        if jobs_count > 0 and identities_count > 0 and logs_count > 0:
            print("[PASS] PostgreSQL data populated.")
        else:
            print("[FAIL] Missing data in PostgreSQL.")
    except Exception as e:
         print(f"[ERROR] Postgres connection/query failed: {e}")

    print_header("Phase 5: Verify Neo4j Graph")
    from app.graph.session import neo4j_manager
    try:
        neo4j_manager.connect()
        session = neo4j_manager.get_session()
        
        query_nodes = "MATCH (n) RETURN labels(n) as label, count(*) as count"
        nodes = session.run(query_nodes)
        print("Nodes:")
        for record in nodes:
            print(f"  {record['label']}: {record['count']}")
            
        query_edges = "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count"
        edges = session.run(query_edges)
        print("Edges:")
        for record in edges:
            print(f"  {record['type']}: {record['count']}")
            
        session.close()
            
        print("[PASS] Neo4j queried successfully.")
    except Exception as e:
        print(f"[ERROR] Neo4j verification failed: {e}")

if __name__ == "__main__":
    main()
