"""
emailer.py — send a markdown report as an HTML email using SMTP env vars.

Shared by the price scan (scanner.main) and the checklist hunt (scanner.hunt).
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown as md_lib

logger = logging.getLogger(__name__)


def send_email(md_body: str, subject: str) -> None:
    """Send the markdown report as an HTML email using SMTP env vars."""
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    email_from = os.environ.get("EMAIL_FROM", smtp_user)
    email_to = os.environ.get("EMAIL_TO", "")

    if not all([smtp_host, smtp_user, smtp_password, email_to]):
        logger.info("Email not configured — skipping (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_TO)")
        return

    # Convert markdown to HTML (tables extension required for the results table)
    html_body = md_lib.markdown(md_body, extensions=["tables"])
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: Arial, sans-serif; color: #222; max-width: 960px;
         margin: 0 auto; padding: 24px; font-size: 14px; }}
  h1 {{ color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 8px; }}
  h2 {{ color: #1a1a2e; margin-top: 32px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th {{ background: #1a1a2e; color: white; padding: 8px 12px; text-align: left; font-size: 13px; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; }}
  tr:nth-child(even) {{ background: #f7f7f7; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 24px 0; }}
  em {{ color: #888; font-size: 12px; }}
  li {{ margin: 4px 0; }}
</style>
</head>
<body>{html_body}</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    msg.attach(MIMEText(md_body, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, email_to, msg.as_string())
        print(f"  Email sent to {email_to}")
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
