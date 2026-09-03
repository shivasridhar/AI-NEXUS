import sys
import os

sys.path.append(os.getcwd())
from app.services.cloudtrail_parser import CloudTrailParser

print("Evaluating empty Records array:")
try:
    result = CloudTrailParser.parse_log_file({"Records": []})
    print(f"Result: {result} (Type: {type(result)})")
except Exception as e:
    print(f"Raised {type(e).__name__}: {str(e)}")
