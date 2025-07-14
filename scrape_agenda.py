import requests
import sys

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <meeting_number> [wg_acronym1] [wg_acronym2] ...", file=sys.stderr)
    sys.exit(1)

meeting_number = sys.argv[1]
target_wgs = set(sys.argv[2:])
URL = f"https://datatracker.ietf.org/api/meeting/{meeting_number}/agenda-data"

try:
    response = requests.get(URL, timeout=10)
    response.raise_for_status()
    data = response.json()
except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError) as e:
    print(f"Error: Could not retrieve or parse agenda data. {e}", file=sys.stderr)
    sys.exit(1)

wg_agendas = {}
for session in data.get("schedule", []):
    wg_name = session.get("groupName")
    wg_acronym = session.get("groupAcronym")
    agenda_url = session.get("agenda", {}).get("url")

    if target_wgs and wg_acronym not in target_wgs:
        continue

    if wg_name and session.get("type") == "regular":
        if agenda_url:
            try:
                agenda_response = requests.get(agenda_url, timeout=10)
                agenda_response.raise_for_status()
                wg_agendas[wg_name] = agenda_response.text
                print(f"Fetched agenda for {wg_name}")
            except requests.exceptions.RequestException as e:
                print(f"Error fetching agenda for {wg_name} from {agenda_url}: {e}", file=sys.stderr)
        else:
            print(f"No agenda for {wg_name}")
