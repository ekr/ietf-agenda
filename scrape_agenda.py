import argparse
import os
import re
import requests
import subprocess
import sys

parser = argparse.ArgumentParser(description="Scrape IETF meeting agendas.")
parser.add_argument("meeting_number", help="The IETF meeting number.")
parser.add_argument('wg_acronyms', nargs='*', help="An optional list of WG acronyms to process.")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
parser.add_argument("-n", "--no-fetch", action="store_true", help="Do not fetch agendas.")
parser.add_argument("-p", "--pdf", action="store_true", help="Convert drafts to PDF.")
args = parser.parse_args()

def debug(*pargs, **kwargs):
    if args.verbose:
        print(*pargs, **kwargs)

meeting_number = args.meeting_number
target_wgs = set(args.wg_acronyms)
URL = f"https://datatracker.ietf.org/api/meeting/{meeting_number}/agenda-data"
headers = {"User-Agent": "ietf-agenda/0.1 (+https://github.com/ekr/ietf-agenda)"}

if not args.no_fetch:
    os.makedirs(meeting_number, exist_ok=True)

try:
    response = requests.get(URL, headers=headers, timeout=10)
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
    global args
    wg_dir = os.path.join(meeting_number, wg)
    os.makedirs(wg_dir, exist_ok=True)
    try:
        agenda_response = requests.get(agenda_url, headers=headers, timeout=10)
        agenda_response.raise_for_status()
        agenda_text = agenda_response.text
        wg_agendas[wg_name] = agenda_text
        drafts = re.findall(r'draft-[\w-]+', agenda_text)
        debug(f"Fetched agenda for {wg_name}")

        for draft in set(drafts):
            meta_url = f"https://datatracker.ietf.org/api/v1/doc/document/{draft}"
            try:
                meta_response = requests.get(meta_url, headers=headers, timeout=10)
                meta_response.raise_for_status()
                meta_data = meta_response.json()
                rev = meta_data.get('rev')
                if not rev:
                    debug(f"Could not find revision for draft {draft}", file=sys.stderr)
                    continue
            except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError) as e:
                debug(f"Error fetching metadata for draft {draft} from {meta_url}: {e}", file=sys.stderr)
                continue

            draft_with_rev = f"{draft}-{rev}"
            draft_url = f"https://www.ietf.org/archive/id/{draft_with_rev}.txt"
            draft_path = os.path.join(wg_dir, f"{draft_with_rev}.txt")

            if os.path.exists(draft_path):
                debug(f"Draft {draft_with_rev} already exists in {wg_dir}")
                continue

            try:
                draft_response = requests.get(draft_url, headers=headers, timeout=10)
                draft_response.raise_for_status()
                with open(draft_path, "w") as f:
                    f.write(draft_response.text)
                debug(f"Downloaded {draft_with_rev} to {draft_path}")

                if args.pdf:
                    pdf_path = os.path.splitext(draft_path)[0] + ".pdf"
                    if os.path.exists(pdf_path):
                        debug(f"PDF {pdf_path} already exists.")
                    else:
                        try:
                            enscript = subprocess.Popen(['enscript', '-o', '-', draft_path], stdout=subprocess.PIPE)
                            ps2pdf = subprocess.run(['ps2pdf', '-', pdf_path], stdin=enscript.stdout, check=True, capture_output=True)
                            enscript.stdout.close()
                            enscript.wait()
                            debug(f"Converted {draft_path} to {pdf_path}")
                        except FileNotFoundError:
                            debug("enscript or ps2pdf not found. Please install them to convert drafts to PDF.", file=sys.stderr)
                        except subprocess.CalledProcessError as e:
                            debug(f"Error converting {draft_path} to PDF: {e.stderr.decode()}", file=sys.stderr)

            except requests.exceptions.RequestException as e:
                debug(f"Error downloading draft {draft_with_rev} from {draft_url}: {e}", file=sys.stderr)
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
