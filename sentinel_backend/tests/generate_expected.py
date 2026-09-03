import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Add the backend to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.cloudtrail_parser import CloudTrailParser

def generate_expected():
    fixtures_dir = Path(__file__).parent / "fixtures"
    golden_input_path = fixtures_dir / "cloudtrail_golden.json"
    
    with open(golden_input_path, "r") as f:
        json_data = json.load(f)
        
    events = CloudTrailParser.parse_log_file(json_data)
    
    # 1. Expected parsed events
    parsed_events_dict = [e.model_dump(mode='json') for e in events]
    with open(fixtures_dir / "cloudtrail_golden_parsed_expected.json", "w") as f:
        json.dump(parsed_events_dict, f, indent=2)
        
    # 2. Expected access log extraction
    access_logs = [CloudTrailParser.extract_access_log_data(e) for e in events]
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
            
    with open(fixtures_dir / "cloudtrail_golden_access_logs_expected.json", "w") as f:
        json.dump(access_logs, f, indent=2, default=default_serializer)
        
    print("Expected fixtures generated successfully.")

if __name__ == "__main__":
    generate_expected()
