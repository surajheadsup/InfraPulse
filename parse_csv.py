#!/usr/bin/env python3
"""
Parse 'Calude data - Team A.csv' and generate buildboard/data.js
with BB_DATA containing records and stats.
"""

import csv
import re
import json
import os
from collections import Counter

CSV_PATH = os.path.join(os.path.dirname(__file__), 'Calude data - Team A.csv')
OUT_PATH = os.path.join(os.path.dirname(__file__), 'buildboard', 'data.js')

# Person -> Team mapping (Vipin reassigned to TEAM D)
TEAM_MAP = {
    'rizwan': 'TEAM A',
    'rishabh': 'TEAM A',
    'ravi': 'TEAM A',
    'ritesh': 'TEAM A',
    'vikram': 'TEAM B',
    'piyush': 'TEAM B',
    'vipin': 'TEAM D',
    'dakshiani': 'TEAM D',
}


def parse_amount(val, team):
    """Parse amount string to number (in Crore) or None."""
    if not val or not str(val).strip():
        return None
    s = str(val).replace('\u20b9', '').replace(',', '').strip()
    # Skip non-numeric descriptions
    if 'greenfield' in s.lower() or 'researched' in s.lower():
        return None
    if s in ['-', '?']:
        return None
    # Check for "Bill will be submitted Monday" or similar text in amount field
    m = re.search(r'[\d.]+', s)
    if not m:
        return None
    n = float(m.group())
    if team == 'TEAM B':
        # Team B amounts are raw Indian Rupees, convert to Crore
        return round(n / 1e7, 2)
    else:
        # Team A and Team D amounts are already in Crore
        return n


def map_status(s):
    """Map raw status string to normalized status."""
    if not s or not str(s).strip():
        return 'pending'
    l = str(s).lower().strip()
    if l in ['contacted', 'conatcted']:
        return 'contacted'
    if 'not awarded' in l or 'no response' in l:
        return 'loss'
    if 'completed' in l:
        return 'win'
    if any(x in l for x in ['pending', 'section', 'finance', 'submit', 'monday',
                              'sparsh', 'dgm', 'ra to be']):
        return 'in_progress'
    if 'fix appointment' in l:
        return 'contacted'
    return 'pending'


def normalize_team(raw_team, person):
    """Determine team based on person mapping, falling back to CSV team column."""
    person_lower = person.strip().lower() if person else ''
    if person_lower in TEAM_MAP:
        return TEAM_MAP[person_lower]
    # Fallback to raw team column
    if raw_team:
        t = raw_team.strip()
        if 'a' in t.lower():
            return 'TEAM A'
        if 'b' in t.lower():
            return 'TEAM B'
        if 'd' in t.lower():
            return 'TEAM D'
    return 'TEAM A'


def normalize_person(name):
    """Capitalize person name properly."""
    if not name or not name.strip():
        return ''
    return name.strip().title()


def parse_date(val):
    """Try to normalize date to YYYY-MM-DD string, or return raw."""
    if not val or not str(val).strip():
        return ''
    raw = str(val).strip()

    # Already YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
        return raw

    # Try DD-MM-YYYY or DD.MM.YYYY
    m = re.match(r'^(\d{1,2})[-./](\d{1,2})[-./](\d{4})$', raw)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    # Try M/D/YYYY or MM/DD/YYYY (US-style from Excel)
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', raw)
    if m:
        mo, d, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    # Try "DD Mon YYYY" e.g. "12 Nov 2025"
    months = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
              'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
              'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
    m = re.match(r'^(\d{1,2})\s+(\w{3})\s+(\d{4})$', raw)
    if m:
        d, mon, y = m.groups()
        mon_num = months.get(mon.lower()[:3], '')
        if mon_num:
            return f"{y}-{mon_num}-{int(d):02d}"

    # Try just a year like "2025"
    if re.match(r'^\d{4}$', raw):
        return raw

    # Non-date values like "3rd RA" - return empty
    if not re.search(r'\d{2}', raw):
        return ''

    return raw


def main():
    records = []
    sno_counter = 0

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        # Strip header whitespace
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

        for row in reader:
            sno_counter += 1

            raw_team = row.get('Team', '').strip()
            person_raw = row.get('Allocated person', '').strip()
            person = normalize_person(person_raw)

            team = normalize_team(raw_team, person_raw)

            project = row.get('Project', '').strip()
            location = row.get('Location', '').strip()
            awarded = row.get('Awarded', '').strip()
            amount_raw = row.get('Amount', '').strip()
            date_raw = row.get('Project date', '').strip()
            org = row.get('Organisation', '').strip()
            status_raw = row.get('Status', '').strip()

            amount = parse_amount(amount_raw, team)
            status = map_status(status_raw)
            date = parse_date(date_raw)

            # Build amount display string
            if amount is not None:
                amount_str = f"{amount} Cr"
            else:
                amount_str = amount_raw if amount_raw else ''

            sno_val = row.get('S.no.', '').strip()
            if not sno_val:
                sno_val = str(sno_counter)

            record = {
                'sno': sno_val,
                'team': team,
                'project': project,
                'location': location,
                'awarded': awarded,
                'amount': amount,
                'amountStr': amount_str,
                'date': date,
                'person': person,
                'org': org,
                'status': status,
                'statusRaw': status_raw,
            }
            records.append(record)

    # Build stats
    total_projects = len(records)
    total_value = round(sum(r['amount'] for r in records if r['amount'] is not None), 2)

    team_counts = dict(Counter(r['team'] for r in records))
    person_counts = dict(Counter(r['person'] for r in records if r['person']))
    org_counts = dict(Counter(r['org'] for r in records if r['org']))
    status_counts = dict(Counter(r['status'] for r in records))

    # Top projects by value (top 20)
    valued = [r for r in records if r['amount'] is not None]
    valued.sort(key=lambda x: x['amount'], reverse=True)
    top_projects = []
    for r in valued[:20]:
        top_projects.append({
            'project': r['project'],
            'amount': r['amount'],
            'team': r['team'],
            'person': r['person'],
        })

    stats = {
        'totalProjects': total_projects,
        'totalValue': total_value,
        'teamCounts': team_counts,
        'personCounts': person_counts,
        'orgCounts': org_counts,
        'statusCounts': status_counts,
        'topProjectsByValue': top_projects,
    }

    data = {
        'records': records,
        'stats': stats,
    }

    json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(f'var BB_DATA = {json_str};\n')

    print(f"Generated {OUT_PATH}")
    print(f"  Total records: {total_projects}")
    print(f"  Total value: {total_value} Cr")
    print(f"  Team counts: {team_counts}")
    print(f"  Status counts: {status_counts}")
    print(f"  Person counts: {person_counts}")


if __name__ == '__main__':
    main()
