import requests
import json

# Replace 'your_api_key_here' with your actual Grafana API key
url = ""
api_key = "your_api_key_key"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

# Read the exported JSON file containing data sources
with open("prometheus-grafana/grafana/provisioning/datasources/data_sources.json", "r") as f:
    data_sources = json.load(f)

# Import each data source into Grafana
for ds in data_sources:
    # Remove 'id' field if exists, as it's specific to the original Grafana instance
    ds.pop('id', None)

    response = requests.post(
        f"http://{{url}}:3000/api/datasources",
        headers=headers,
        json=ds
    )

    if response.status_code == 200:
        print(f"Successfully imported data source {ds['name']}")
    else:
        print(f"Failed to import data source {ds['name']}: {response.content}")
