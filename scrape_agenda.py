import requests
import sys

URL = "https://datatracker.ietf.org/api/meeting/123/agenda-data"

try:
    response = requests.get(URL, timeout=10)
    response.raise_for_status()
    data = response.json()
except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError) as e:
    print(f"Error: Could not retrieve or parse agenda data. {e}", file=sys.stderr)
    sys.exit(1)

for session in data.get("schedule", []):
    wg_name = session.get("groupName")
    agenda_url = session.get("agenda", {}).get("url")

    if wg_name and session.get("type") == "regular":
        print(f"{wg_name}: {agenda_url or 'None'}")
