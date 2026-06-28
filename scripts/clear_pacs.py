import requests

# URL targeting the root patients endpoint
ORTHANC_URL = "http://localhost:8042/patients"
auth_credentials = ('orthanc', 'orthanc')

try:
    print("📡 Connecting to Orthanc PACS to fetch active records...")
    # 1. Get a list of all current patient container IDs
    response = requests.get(ORTHANC_URL, auth=auth_credentials)
    response.raise_for_status()
    patient_ids = response.json()
    
    if not patient_ids:
        print("✨ Your Orthanc server is already completely empty! No action needed.")
    else:
        print(f"🗑️ Found {len(patient_ids)} patient record(s). Initializing full system purge...")
        
        # 2. Loop through and send a DELETE request to every single patient ID
        for patient_id in patient_ids:
            delete_url = f"{ORTHANC_URL}/{patient_id}"
            delete_response = requests.delete(delete_url, auth=auth_credentials)
            
            if delete_response.status_code == 200:
                print(f"✅ Successfully deleted patient container: {patient_id[:8]}...")
            else:
                print(f"⚠️ Failed to delete container {patient_id[:8]}: Status {delete_response.status_code}")
                
        print("\n🎉 Purge complete! Your local PACS node is now a completely blank canvas.")

except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Is your local Orthanc server running right now on port 8042?")
except Exception as e:
    print(f"❌ An error occurred during the purge: {e}")