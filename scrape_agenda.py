import argparse
import requests
import sys

parser = argparse.ArgumentParser(description="Scrape IETF meeting agendas.")
parser.add_argument("meeting_number", help="The IETF meeting number.")
parser.add_argument('wg_acronyms', nargs='*', help="An optional list of WG acronyms to process.")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
parser.add_argument("--no-fetch", action="store_true", help="Do not fetch agendas.")
args = parser.parse_args()

def debug(*pargs, **kwargs):
    if args.verbose:
        print(*pargs, **kwargs)

meeting_number = args.meeting_number
target_wgs = set(args.wg_acronyms)
URL = f"https://datatracker.ietf.org/api/meeting/{meeting_number}/agenda-data"

try:
    response = requests.get(URL, timeout=10)
    response.raise_for_status()
    data = response.json()
except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError) as e:
    debug(f"Error: Could not retrieve or parse agenda data. {e}", file=sys.stderr)
    sys.exit(1)

wg_agendas = {}
wgs = 0
missing_agendas = 0
processed_wgs = set()

def process_wg(wg, agenda_name, agenda_url):
    try:
        agenda_response = requests.get(agenda_url, timeout=10)
        agenda_response.raise_for_status()
        wg_agendas[wg_name] = agenda_response.text
        debug(f"Fetched agenda for {wg_name}")
    except requests.exceptions.RequestException as e:
        debug(f"Error fetching agenda for {wg_name} from {agenda_url}: {e}", file=sys.stderr)


for session in data.get("schedule", []):
    wg_name = session.get("groupName")
    wg_acronym = session.get("groupAcronym")
    agenda_url = session.get("agenda", {}).get("url")

    if target_wgs and wg_acronym not in target_wgs:
        continue

    if wg_name and session.get("type") != "regular":
        continue

    if wg_acronym in processed_wgs:
        continue
    if wg_acronym:
        processed_wgs.add(wg_acronym)

    wgs += 1
    if not agenda_url:
        debug(f"No agenda for {wg_acronym}")
        missing_agendas += 1
        continue
    
    if not args.no_fetch:
        process_wg(wg_acronym, wg_name, agenda_url)

print(f"Missing {missing_agendas} agendas out of {wgs} working groups ({int(float(missing_agendas)/wgs*100)}%)")
