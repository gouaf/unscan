# UN Job Scanner

Checks ReliefWeb, UN Talent, and UNjobs.org daily for postings that match your profile,
scores them by keyword relevance, and emails you a digest — plus keeps a CSV history in the repo.

## What it does

1. Pulls fresh postings from three sources every day (via GitHub Actions on a schedule).
2. Scores each posting against `profile_config.py` (your keywords, target grades, target locations).
3. Skips anything you've already seen (tracked in `seen_jobs.json`).
4. Emails you an HTML digest of new matches, and writes `output/matches.csv` for a running record.

## One-time setup (about 10 minutes)

### 1. Create the repo
- Create a new **private** GitHub repository.
- Upload all these files (`scraper.py`, `send_email.py`, `profile_config.py`,
  `requirements.txt`, `.github/workflows/daily-job-scan.yml`, `seen_jobs.json`, `output/.gitkeep`),
  preserving the folder structure.

### 2. Set up an email sender
The easiest option is a Gmail **App Password** (works even if you don't want to expose your main password):
1. Turn on 2-Step Verification on the Google account you want to send from (Google Account → Security).
2. Go to Google Account → Security → App passwords, create one named "job-scanner", and copy the 16-character code.
3. You'll use that code as `SMTP_PASS` below (not your normal Gmail password).

Any SMTP provider works the same way (Outlook, Fastmail, SendGrid, etc.) — just change `SMTP_HOST`/`SMTP_PORT`.

### 3. Add repo secrets
In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**. Add:

| Secret       | Example value              |
|--------------|-----------------------------|
| `SMTP_HOST`  | `smtp.gmail.com`            |
| `SMTP_PORT`  | `587`                       |
| `SMTP_USER`  | `youraddress@gmail.com`     |
| `SMTP_PASS`  | the 16-character app password |
| `EMAIL_TO`   | the inbox you want digests sent to |

### 4. Enable the workflow
- Go to the **Actions** tab of your repo → you should see "Daily UN Job Scan."
- Click "Run workflow" once to test it manually before waiting for the schedule.
- Check the run logs, and check `output/digest.html` and `output/matches.csv` get updated/committed.

That's it — it will now run automatically every day at 12:00 UTC (edit the `cron` line in
`.github/workflows/daily-job-scan.yml` to change the time; use https://crontab.guru if you want a different schedule).

## Tuning your matches

Everything about *what counts as a match* lives in `profile_config.py` — no code changes needed:
- `KEYWORDS`: add/remove terms and adjust their weights.
- `TARGET_GRADES`: e.g. add `"P-2"` if you want to widen the net.
- `TARGET_LOCATIONS`: add or remove duty stations; leave empty to accept anywhere.
- `MIN_SCORE`: raise it to get fewer, higher-confidence matches; lower it to see more.

## Known limitations

- **HTML scraping is brittle.** UN Talent and UNjobs.org don't offer stable APIs, so if either
  site redesigns its listing pages, the CSS selectors in `fetch_untalent_jobs()` /
  `fetch_unjobs_org()` in `scraper.py` may need small updates. If a run finds 0 jobs from a
  source it used to find many, that's usually why — check the Action logs first.
- **ReliefWeb is the most reliable source** since it's a real, documented API
  (https://apidoc.reliefweb.int) rather than scraped HTML — but it skews humanitarian/field roles
  rather than HQ policy/comms roles, so don't be surprised if UN Talent and UNjobs.org surface
  more of the executive-communications-style postings you're after.
- If you'd rather not scrape at all, you can delete the `fetch_untalent_jobs` and
  `fetch_unjobs_org` calls in `scraper.py`'s `main()` and rely on ReliefWeb only, or add other
  official APIs/RSS feeds as you find them (e.g. individual agency career pages sometimes offer
  an RSS feed under "subscribe to vacancies").
- GitHub Actions free tier includes 2,000 minutes/month for private repos — this job takes under
  a minute per run, so a daily schedule costs a trivial amount of that budget.

## Files

```
un-job-scanner/
├── scraper.py                  # main scan + scoring logic
├── send_email.py               # emails the digest
├── profile_config.py           # your keywords/grades/locations — EDIT THIS to tune matches
├── requirements.txt
├── seen_jobs.json              # auto-updated; tracks what you've already been notified about
├── output/
│   ├── matches.csv             # auto-updated running record of matches
│   └── digest.html             # auto-updated, the latest email body
└── .github/workflows/daily-job-scan.yml
```
