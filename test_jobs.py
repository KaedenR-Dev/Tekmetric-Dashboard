from tekmetric_api import TekmetricAPI
import json

api = TekmetricAPI()

job_id = 1240850381

print()
print(f"Getting Job {job_id}...")
print("=" * 60)

job = api.get(f"/jobs/{job_id}")

print()
print(json.dumps(job, indent=4))