"""
Sends the daily digest via email using SMTP (works with Gmail, Outlook, etc.).
Reads credentials from environment variables so nothing sensitive is stored in the repo:

  SMTP_HOST   e.g. smtp.gmail.com
  SMTP_PORT   e.g. 587
  SMTP_USER   the sending email address
  SMTP_PASS   an app password (NOT your regular password — see README)
  EMAIL_TO    where the digest should be sent
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone


def main():
    digest_path = os.path.join("output", "digest.html")
    if not os.path.exists(digest_path):
        print("No digest.html found — skipping email.")
        return

    with open(digest_path, "r") as f:
        html_body = f.read()

    # Skip sending if there's nothing new (keeps your inbox quiet).
    if "No new matching postings today" in html_body:
        print("No new matches today — skipping email to avoid noise.")
        return

    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    email_to = os.environ["EMAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"UN Job Matches — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    msg["From"] = smtp_user
    msg["To"] = email_to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [email_to], msg.as_string())

    print(f"Digest emailed to {email_to}")


if __name__ == "__main__":
    main()
