#!/usr/bin/env python3
"""Mark watched matters as listed when they appear in an SCI cause list.

Reads data/matters.json, loads the parsed SC cause lists published by
onecourtin/sc-cause-list for today .. today+N days, and for every watched
matter found there sets next_date / court / bench / listing from the list.
Every change is appended to data/history.json. A cause-list hit outranks
any date taken from news reports.

    python check_listings.py                    # fetch lists from GitHub
    python check_listings.py --data-dir DIR     # read YYYY-MM-DD.json from DIR
    python check_listings.py --today 2026-10-15 # pretend it is that day
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
MATTERS = ROOT / "data" / "matters.json"
HISTORY = ROOT / "data" / "history.json"
RAW = "https://raw.githubusercontent.com/onecourtin/sc-cause-list/main/data/{}.json"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def norm_case(s):
    """'W.P.(C) No. 276/2025' -> 'WPC276/2025'; 'Diary No. 63858-2026' -> 'DIARY63858/2026'."""
    s = s.upper()
    s = re.sub(r"\bNO\b\.?", "", s)
    s = re.sub(r"(\d+)-(\d+)/(\d{4})", r"\1/\2/\3", s)  # range: 8402-8403/2024
    s = re.sub(r"(\d+)-(\d{4})\b", r"\1/\2", s)  # diary numbers use a hyphen before the year
    return re.sub(r"[^A-Z0-9/]", "", s)


def case_in(watched, listed):
    """True when the watched case number appears in the cause-list entry.

    The listed text may hold several numbers ('MA 1357/2026 in W.P.(C) No. 704/2025')
    or a range ('C.A. No. 8402-8403/2024'), so test each number on its own.
    """
    w = norm_case(watched)
    for part in re.split(r"\bIN\b", listed.upper()):
        p = norm_case(part)
        if p == w:
            return True
        m = re.fullmatch(r"([A-Z()]+?)(\d+)/(\d+)/(\d{4})", p)  # range 8402-8403/2024 after norm
        if m:
            wm = re.fullmatch(r"([A-Z()]+?)(\d+)/(\d{4})", w)
            if wm and wm.group(1) == m.group(1) and wm.group(3) == m.group(4) \
                    and int(m.group(2)) <= int(wm.group(2)) <= int(m.group(3)):
                return True
    return False


def clean_judge(j):
    j = j.strip()
    if re.search(r"THE CHIEF JUSTICE", j, re.I):
        return "Chief Justice"
    j = re.sub(r"^HON'?BLE\s+(MR\.|MRS\.|MS\.|DR\.)?\s*JUSTICE\s+", "", j, flags=re.I)
    j = re.sub(r"^HON'?BLE\s+", "", j, flags=re.I)
    name = " ".join(w.title() for w in j.split())
    return name + " J" if name and not re.search(r"registrar", name, re.I) else name


def clean_court(c):
    c = c.strip()
    if re.fullmatch(r"CHIEF JUSTICE'?S COURT", c, re.I):
        return "Chief Justice's Court"
    m = re.match(r"COURT NO\.?\s*:?\s*(\d+)", c, re.I)
    return f"Court No. {m.group(1)}" if m else c.title()


def load_list(day, data_dir):
    name = day.isoformat()
    if data_dir:
        f = pathlib.Path(data_dir) / f"{name}.json"
        return json.loads(f.read_text()) if f.exists() else None
    try:
        with urllib.request.urlopen(RAW.format(name), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def hits_for(matter, cl):
    """Yield (bench, item, list_url) for every entry of matter in one day's list."""
    urls = {l["name"]: l.get("url") for l in cl.get("lists", [])}
    party_res = [re.compile(p, re.I) for p in matter.get("match_parties", [])]
    for b in cl.get("benches", []):
        for s in b.get("sections", []):
            for it in s.get("items", []):
                c = it.get("c", "")
                by_case = any(case_in(w, c) for w in matter.get("case_nos", []))
                text = f"{it.get('p', '')} | {it.get('r', '')}"
                by_party = any(r.search(text) for r in party_res)
                if by_case or by_party:
                    yield b, it, urls.get(b.get("list")), "case" if by_case else "party"


def check(matters, today, days, data_dir):
    lists = {}
    for i in range(days + 1):
        d = today + dt.timedelta(days=i)
        cl = load_list(d, data_dir)
        if cl:
            lists[d.isoformat()] = cl
    changes = []
    for m in matters:
        if m.get("date_status") == "decided":
            continue
        found = None
        for day in sorted(lists):
            for b, it, url, via in hits_for(m, lists[day]):
                found = (day, b, it, url, via)
                break
            if found:
                break
        if not found:
            continue
        day, b, it, url, via = found
        listing = {
            "date": day,
            "court": clean_court(b.get("court", "")),
            "judges": [clean_judge(j) for j in b.get("judges", [])],
            "time": b.get("time", ""),
            "item": it.get("n", ""),
            "case": it.get("c", ""),
            "list_url": url,
            "matched_by": via,
        }
        new = {
            "next_date": day,
            "date_status": "listed",
            "court": listing["court"],
            "bench": listing["judges"],
            "listing": listing,
        }
        diff = {k: (m.get(k), v) for k, v in new.items() if m.get(k) != v}
        if diff:
            m.update(new)
            changes.append({
                "id": m["id"],
                "fields": {k: {"old": o, "new": n} for k, (o, n) in diff.items()},
                "source": url,
                "by": "check_listings.py",
            })
    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", help="read cause-list JSON from this folder instead of GitHub")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today in IST)")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--matters", default=str(MATTERS))
    ap.add_argument("--history", default=str(HISTORY))
    a = ap.parse_args()

    now = dt.datetime.now(IST)
    today = dt.date.fromisoformat(a.today) if a.today else now.date()
    mpath, hpath = pathlib.Path(a.matters), pathlib.Path(a.history)
    doc = json.loads(mpath.read_text())
    changes = check(doc["matters"], today, a.days, a.data_dir)
    if not changes:
        print("No listing changes.")
        return 0
    stamp = now.strftime("%Y-%m-%d %H:%M IST")
    doc["updated"] = stamp
    mpath.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    hist = json.loads(hpath.read_text()) if hpath.exists() else []
    for c in changes:
        c["at"] = stamp
    hist.extend(changes)
    hpath.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n")
    for c in changes:
        print(f"{c['id']}: {', '.join(c['fields'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
