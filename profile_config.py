"""
Match criteria for the job scanner.
Edit this file to tune what counts as a good match — no need to touch scraper.py.
"""

# Keywords pulled from your CV / career focus. Each match adds points to a job's score.
# Weight higher = more important signal. Tune freely.
KEYWORDS = {
    # Core function match (highest weight)
    "executive communications": 5,
    "speechwriting": 5,
    "speech writing": 5,
    "thought leadership": 4,
    "editorial": 4,
    "communications director": 4,
    "communications specialist": 3,
    "communications officer": 3,
    "public affairs": 3,
    "strategic communications": 4,
    "media relations": 2,
    "crisis communications": 4,
    "risk communication": 3,
    "stakeholder engagement": 3,
    "digital content": 2,
    "social media strategy": 2,
    "op-ed": 3,
    "narrative strategy": 3,
    "content strategy": 2,
    "external relations": 2,

    # Institutional fit signals
    "multilateral": 2,
    "intergovernmental": 1,
    "protocol": 1,

    # Language
    "french": 2,
    "francophone": 2,
}

# Grade levels you're targeting. Jobs outside this list are still shown but scored lower.
TARGET_GRADES = ["P-3", "P-4", "P3", "P4"]
GRADE_BONUS = 3

# Locations you'd accept. Leave list empty to accept any location.
TARGET_LOCATIONS = [
    "new york", "washington", "geneva", "rome", "remote", "home-based",
]
LOCATION_BONUS = 3

# Minimum score (out of roughly 20-30 possible) for a job to be included in the digest.
MIN_SCORE = 4

# How many days back to look for "new" postings when a source doesn't give an exact date.
LOOKBACK_DAYS = 2

# Your name / org, used as the ReliefWeb API "appname" parameter (required courtesy field).
APP_NAME = "personal-job-scanner"
