import sys
import json

sys.path.append(r"c:\Users\acer\Desktop\sentinelai-repo-with-git\sentinel_backend")
from app.graph.neo4j_queries import GET_ATTACK_PATH
from neo4j import GraphDatabase

def test_attack_path():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password" # Trying default or simple password, or we can fetch from env
    # Actually, from the logs: NEO4J_PASSWORD length = 9 starts with = 12As...
    # I don't know the exact password.
    
    # Wait, I can just use the app's config!
    from app.core.config import settings
    driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    
    # Get identity ID from Postgres
    from app.db.session import SessionLocal
    from app.models.machine_identity import MachineIdentity
    db = SessionLocal()
    identity_id = "cbfea9d2-5d81-4b5f-8970-39a550a38a31"
    identity = db.query(MachineIdentity).filter(MachineIdentity.id == identity_id).first()
    
    if not identity:
        print("Identity not found!")
        return
        
    arn = identity.arn
    workspace_id = str(identity.workspace_id)
    
    with driver.session() as session:
        from app.services.attack_path_service import AttackPathService
        service = AttackPathService(session)
        print("Calling service...")
        graph_data = service.get_attack_path(arn, workspace_id)
        
        print("Attempting to JSON serialize...")
        try:
            import json
            # Use fastapi's jsonable_encoder to simulate exactly what happens
            from fastapi.encoders import jsonable_encoder
            jsonable_encoder(graph_data)
            print("FastAPI Serialization successful!")
            json.dumps(graph_data)
            print("Standard JSON Serialization successful!")
        except Exception as e:
            print("Serialization failed!")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_attack_path()
