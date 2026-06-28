import requests

# 1. Define the connection parameters for your local Orthanc server
# Default port is 8042. We explicitly pass the default credentials.
BASE_URL = "http://localhost:8042"
AUTH = ("orthanc", "orthanc")  # (Username, Password)


def get_clinical_patient_ids():
    print("🔄 Connecting to local Orthanc PACS pipeline...")

    try:
        # 2. Call the top-level endpoint to get all Orthanc internal Patient Hashes
        # This matches doing a GET request to http://localhost:8042/patients
        response = requests.get(f"{BASE_URL}/patients", auth=AUTH)

        # Check if our HTTP request succeeded (Status Code 200)
        response.raise_for_status()

        # Parse the response body as JSON. It looks like an array: ["hash1", "hash2"]
        patient_hashes = response.json()

        # Guard clause: stop if the PACS database has no images uploaded yet
        if not patient_hashes:
            print("⚠️ The database is empty. Please upload a DICOM file first.")
            return

        print(f"📦 Found {len(patient_hashes)} patient records in Orthanc.\n")
        print(f"{'Orthanc Resource Hash':<40} | {'Clinical Patient ID (MRN)':<25}")
        print("-" * 70)

        # 3. Loop through every single internal patient hash to extract the real DICOM tags
        for p_hash in patient_hashes:
            # Make a targeted request for this specific patient: /patients/{id}
            detail_response = requests.get(
                f"{BASE_URL}/patients/{p_hash}", auth=AUTH
            )
            detail_response.raise_for_status()

            patient_data = detail_response.json()

            # 4. Extract the 'PatientID' tag from the MainDicomTags dictionary
            # This is the exact value embedded in the original image header
            clinical_id = patient_data.get("MainDicomTags", {}).get(
                "PatientID", "UNKNOWN"
            )

            # Print out the results in a clean table format
            print(f"{p_hash:<40} | {clinical_id:<25}")

    except requests.exceptions.ConnectionError:
        print(
            "❌ Connection Failed! Verify Orthanc is running on http://localhost:8042"
        )
    except requests.exceptions.HTTPError as err:
        print(f"❌ HTTP Error occurred: {err}")


# This line tells Python to execute our function when the file is run directly
if __name__ == "__main__":
    get_clinical_patient_ids()