import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "destination_email@example.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

if not GMAIL_APP_PASSWORD:
    print("Cannot send failure alert because GMAIL_APP_PASSWORD is not set.")
    exit(1)

msg = MIMEMultipart('alternative')
msg['Subject'] = '⚠️ X/Twitter Scraper Action Failed'
msg['From'] = SENDER_EMAIL
msg['To'] = RECEIVER_EMAIL

html_content = f"""
<html>
    <head>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            .card {{ background: #fff5f5; border-left: 5px solid #ff4d4f; padding: 20px; border-radius: 4px; }}
            .btn {{ display: inline-block; background: #1DA1F2; color: #ffffff !important; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>⚠️ Automated Cloud Scrape Failed</h2>
            <p>Your automated X/Twitter scraper running on GitHub Actions encountered an error. This usually happens if your session cookies expired, or if Twitter blocked the GitHub IP address.</p>
            <p><strong>To fix this or run it manually, click the button below to launch it directly from your Mac using your local session.</strong></p>
            <a href="xscraper://run" class="btn">🚀 Run on My Mac</a>
        </div>
    </body>
</html>
"""

msg.attach(MIMEText("Your scraper failed. Click the xscraper://run link on your mac to re-run it.", 'plain'))
msg.attach(MIMEText(html_content, 'html'))

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
    server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    server.quit()
    print("Sent failure alert email successfully.")
except Exception as e:
    print(f"Failed to send failure alert email: {e}")
