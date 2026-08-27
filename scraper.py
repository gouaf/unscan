"""
Daily UN / multilateral job scanner.

Sources:
  - ReliefWeb API (official, JSON, no scraping — https://apidoc.reliefweb.int)
  - UN Talent (untalent.org) listing pages (HTML)
  - UNjobs.org search results (HTML)

Scores each posting against profile_config.KEYWORDS and writes:
  - output/matches.csv          (all matches, append-only history avoided via seen-jobs cache)
  - output/digest.html          (today's new matches, nicely formatted for email)
  - seen_jobs.json              (persisted between runs so you don't get repeat emails)

Run: python scraper.py
"""

import json
import os
import re
import time
import html
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from profile_config import (
    KEYWORDS, TARGET_GRADES, GRADE_BONUS, TARGET_LOCATIONS,
    LOCATION_BONUS, MIN_SCORE, LOOKBACK_DAYS, APP_NAME,
)

SEEN_JOBS_PATH = "seen_jobs.json"
OUTPUT_DIR = "output"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; personal-job-scanner/1.0)"}


# --------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_PATH):
        with open(SEEN_JOBS_PATH, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_jobs(seen):
    # Keep the file from growing forever — cap at the most recent 5000 ids.
    trimmed = list(seen)[-5000:]
    with open(SEEN_JOBS_PATH, "w") as f:
        json.dump(trimmed, f)


def score_job(title, description, location, grade_text):
    text = f"{title} {description}".lower()
    score = 0
    matched_keywords = []

    for kw, weight in KEYWORDS.items():
        if kw in text:
            score += weight
            matched_keywords.append(kw)

    grade_text = (grade_text or "").upper()
    if any(g in grade_text or g in title.upper() for g in TARGET_GRADES):
        score += GRADE_BONUS

    loc_lower = (location or "").lower()
    if not TARGET_LOCATIONS or any(loc in loc_lower for loc in TARGET_LOCATIONS):
        score += LOCATION_BONUS

    return score, matched_keywords


def safe_get(url, params=None, retries=3, timeout=20):
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"  [warn] failed to fetch {url}: {e}")
                return None
            time.sleep(2)
    return None


# --------------------------------------------------------------------------
# Source: ReliefWeb API
# --------------------------------------------------------------------------

def fetch_reliefweb_jobs():
    """Official API — https://apidoc.reliefweb.int. No key required."""
    print("Fetching ReliefWeb jobs...")
    jobs = []
    url = "https://api.reliefweb.int/v2/jobs"
    payload = {
        "appname": APP_NAME,
        "limit": 100,
        "sort": ["date.created:desc"],
        "fields": {
            "include": [
                "title", "url_alias", "date.created", "country.name",
                "source.name", "type.name", "career_categories.name",
            ]
        },
    }
    resp = requests.post(url, json=payload, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        print(f"  [warn] ReliefWeb API returned {resp.status_code}")
        return jobs

    data = resp.json()
    for item in data.get("data", []):
        fields = item.get("fields", {})
        title = fields.get("title", "")
        job_url = fields.get("url_alias", "")
        source = ", ".join(s["name"] for s in fields.get("source", []) or [])
        country = ", ".join(c["name"] for c in fields.get("country", []) or [])
        categories = ", ".join(c["name"] for c in fields.get("career_categories", []) or [])
        description = f"{source} {categories}"

        jobs.append({
            "id": f"reliefweb-{item.get('id')}",
            "title": title,
            "org": source,
            "location": country,
            "grade": "",
            "url": job_url,
            "source": "ReliefWeb",
            "description": description,
        })
    print(f"  -> {len(jobs)} jobs found")
    return jobs


# --------------------------------------------------------------------------
# Source: UN Talent (untalent.org)
# --------------------------------------------------------------------------

def fetch_untalent_jobs(function_slug="communications", grades=("p-3", "p-4")):
    """
    Scrapes untalent.org's filterable listing pages, e.g.:
    https://untalent.org/jobs/in-communications/contract-all/new-york?contracts=p-3
    We hit a couple of broad function/location combos rather than every permutation.
    """
    print("Fetching UN Talent jobs...")
    jobs = []
    base = "https://untalent.org"
    locations = ["new-york", "washington", "rome", "geneva", "remote"]

    for loc in locations:
        for grade in grades:
            url = f"{base}/jobs/in-{function_slug}/contract-all/{loc}?contracts={grade}"
            resp = safe_get(url)
            if resp is None:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # Listing rows are links to /jobs/<id>/... — adjust selector if the site markup changes.
            for link in soup.select("a[href*='/jobs/']"):
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not title or len(title) < 8:
                    continue
                full_url = urljoin(base, href)
                job_id = re.sub(r"\D", "", href) or full_url

                jobs.append({
                    "id": f"untalent-{job_id}",
                    "title": title,
                    "org": "",
                    "location": loc.replace("-", " ").title(),
                    "grade": grade.upper(),
                    "url": full_url,
                    "source": "UN Talent",
                    "description": title,
                })
            time.sleep(1)  # be polite

    # De-dupe within this source
    dedup = {j["id"]: j for j in jobs}
    print(f"  -> {len(dedup)} jobs found")
    return list(dedup.values())


# --------------------------------------------------------------------------
# Source: UNjobs.org
# --------------------------------------------------------------------------

def fetch_unjobs_org(search_terms=("communications", "executive communications", "editorial")):
    """
    Scrapes UNjobs.org search result pages.
    UNjobs URL pattern: https://unjobs.org/duty_stations/new-york?q=<term>
    We keep this generic and location-agnostic, then filter by score afterward.
    """
    print("Fetching UNjobs.org jobs...")
    jobs = []
    base = "https://unjobs.org"

    for term in search_terms:
        url = f"{base}/search/{requests.utils.quote(term)}"
        resp = safe_get(url)
        if resp is None:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")

        for item in soup.select(".job, .job-item, li a[href*='/vacancies/']"):
            link = item if item.name == "a" else item.find("a", href=True)
            if not link:
                continue
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not title or len(title) < 8:
                continue
            full_url = urljoin(base, href)
            job_id = re.sub(r"\D", "", href) or full_url

            jobs.append({
                "id": f"unjobs-{job_id}",
                "title": title,
                "org": "",
                "location": "",
                "grade": "",
                "url": full_url,
                "source": "UNjobs.org",
                "description": title,
            })
        time.sleep(1)

    dedup = {j["id"]: j for j in jobs}
    print(f"  -> {len(dedup)} jobs found")
    return list(dedup.values())


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def build_digest_html(matches):
    if not matches:
        return "<p>No new matching postings today.</p>"

    rows = []
    for m in sorted(matches, key=lambda x: -x["score"]):
        kw = ", ".join(m["matched_keywords"]) or "—"
        rows.append(f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <a href="{html.escape(m['url'])}"><b>{html.escape(m['title'])}</b></a><br>
            <span style="color:#666;font-size:13px;">{html.escape(m['org'])} · {html.escape(m['location'])} · {html.escape(m['source'])}</span>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{m['score']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px;color:#888;">{html.escape(kw)}</td>
        </tr>""")

    return f"""
    <html><body style="font-family:Arial,sans-serif;">
    <h2>Daily UN Job Matches — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}</h2>
    <p>{len(matches)} new posting(s) scored above your threshold.</p>
    <table style="border-collapse:collapse;width:100%;">
      <tr style="background:#f5f5f5;">
        <th style="padding:8px;text-align:left;">Position</th>
        <th style="padding:8px;">Score</th>
        <th style="padding:8px;text-align:left;">Matched on</th>
      </tr>
      {''.join(rows)}
    </table>
    </body></html>
    """


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    seen = load_seen_jobs()

    all_jobs = []
    all_jobs += fetch_reliefweb_jobs()
    all_jobs += fetch_untalent_jobs()
    all_jobs += fetch_unjobs_org()

    print(f"\nTotal jobs fetched across sources: {len(all_jobs)}")

    new_matches = []
    for job in all_jobs:
        if job["id"] in seen:
            continue
        score, matched_keywords = score_job(
            job["title"], job.get("description", ""), job.get("location", ""), job.get("grade", "")
        )
        if score >= MIN_SCORE:
            job["score"] = score
            job["matched_keywords"] = matched_keywords
            new_matches.append(job)
        seen.add(job["id"])

    print(f"New matches above threshold ({MIN_SCORE}): {len(new_matches)}")

    # Write CSV
    csv_path = os.path.join(OUTPUT_DIR, "matches.csv")
    with open(csv_path, "w") as f:
        f.write("score,title,org,location,source,url,matched_keywords\n")
        for m in sorted(new_matches, key=lambda x: -x["score"]):
            row = [
                str(m["score"]), m["title"], m["org"], m["location"], m["source"],
                m["url"], "|".join(m["matched_keywords"]),
            ]
            f.write(",".join('"' + c.replace('"', "'") + '"' for c in row) + "\n")

    # Write HTML digest
    digest_html = build_digest_html(new_matches)
    with open(os.path.join(OUTPUT_DIR, "digest.html"), "w") as f:
        f.write(digest_html)

    save_seen_jobs(seen)
    print(f"\nWrote {csv_path} and output/digest.html")
    return new_matches


if __name__ == "__main__":
    main()
