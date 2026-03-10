import asyncio
import csv
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from playwright.async_api import async_playwright
import anthropic
import markdown

# Email Configuration
SENDER_EMAIL = "amitdas@gmail.com"
RECEIVER_EMAIL = "amit.das@think360.ai"
# You'll need a Gmail App Password, NOT your regular password.
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "pdxo suuj selu yndk")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "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")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

async def extract_text_from_url(page, url):
    try:
        # Navigate to the url, allowing redirects (like t.co -> actual site)
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        # Give it a second to render
        await page.wait_for_timeout(2000)
        # Extract the visible text from the body
        text = await page.evaluate("document.body.innerText")
        actual_url = page.url
        return text, actual_url
    except Exception as e:
        print(f"    ⚠️ Failed to fetch {url}: {e}")
        return "", url

def generate_summary(text, url):
    if not text.strip():
        return "Could not extract readable content from the page. It might be behind a paywall, a PDF, or blocked."
        
    prompt = f"""
    You are an expert research assistant. Read the following text extracted from a webpage ({url}).
    
    INSTRUCTIONS:
    1. If the text appears to be a research paper or scientific article, provide a summary capturing the **APPROACH** and **FINDINGS**.
    2. Otherwise, provide a concise ~250-word summary of the main points of the article/page.
    3. Format your response cleanly with markdown headers or bullet points if appropriate.
    
    TEXT TO SUMMARIZE:
    {text[:20000]} 
    """ # Limiting character count to stay well within token limits and reduce costs
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6", # Updated to a model available on this API key
            max_tokens=600,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error generating summary: {e}"

def send_email(html_content, markdown_content):
    if GMAIL_APP_PASSWORD == "PUT_YOUR_APP_PASSWORD_HERE":
        print("\n⚠️  Skipping email sending: Please put your Gmail App Password in newsletter.py to enable email delivery.")
        return
        
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Recent X Highlights'
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        part1 = MIMEText(markdown_content, 'plain')
        
        # Adding some basic CSS to the HTML to make it look like a professional newsletter
        html_template = f"""
        <html>
          <head>
            <style>
              body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f6f8; }}
              .container {{ background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
              h1 {{ color: #1DA1F2; border-bottom: 2px solid #1DA1F2; padding-bottom: 10px; }}
              h2 {{ color: #2C3E50; margin-top: 30px; }}
              h3 {{ color: #34495E; font-size: 1.1em; }}
              a {{ color: #1DA1F2; text-decoration: none; }}
              blockquote {{ border-left: 4px solid #1DA1F2; margin: 20px 0; padding: 15px 20px; color: #555; background: #f8fafc; border-radius: 0 4px 4px 0; font-style: italic; }}
              hr {{ border: 0; border-top: 1px solid #eaeaea; margin: 30px 0; }}
              .footer {{ text-align: center; margin-top: 40px; font-size: 0.85em; color: #888; }}
            </style>
          </head>
          <body>
            <div class="container">
              {html_content}
              <div class="footer">
                Automated by Antigravity X Scraper Pipeline
              </div>
            </div>
          </body>
        </html>
        """
        part2 = MIMEText(html_template, 'html')

        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ Email transmitted successfully to " + RECEIVER_EMAIL + "!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

async def main():
    print("Reading X Data CSVs...")
    items = []
    
    for filename in ['bookmarks.csv', 'likes.csv']:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # check if embedded_links exists and is not empty
                    if row.get('embedded_links'):
                        links = [l.strip() for l in row['embedded_links'].split(',') if l.strip()]
                        if links:
                            row['links_list'] = links
                            row['source'] = filename.replace('.csv', '').capitalize()
                            items.append(row)
                        
    if not items:
        print("No items with embedded links found in the CSVs.")
        print("Make sure you run scraper.py first!")
        return
        
    print(f"Found {len(items)} tweets with embedded links.")
    
    results = []
    
    async with async_playwright() as p:
        # We'll run this headless since we don't need to log in to read random web articles
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        for idx, item in enumerate(items, 1):
            print(f"\n[{idx}/{len(items)}] Processing tweet by {item['author']} from {item['source']}...")
            summaries = []
            for link in item['links_list']:
                print(f"  -> Fetching link: {link}")
                text, actual_url = await extract_text_from_url(page, link)
                
                print(f"  -> Generating AI summary for: {actual_url}")
                summary = generate_summary(text, actual_url)
                
                summaries.append({
                    'original_url': link,
                    'actual_url': actual_url,
                    'summary': summary
                })
            
            item['summaries'] = summaries
            results.append(item)
            
        await browser.close()
        
    date_str = datetime.now().strftime("%Y-%m-%d")
    md_filename = f"Newsletter_{date_str}.md"
    
    print("\nDrafting Newsletter...")
    md_content = f"# 🗞️ X/Twitter Insights & Research Digest\n"
    md_content += f"**Generated on:** {date_str}\n\n"
    md_content += "---\n\n"
    
    for idx, item in enumerate(results, 1):
        md_content += f"## {idx}. Tweet by {item['author']} (Saved in {item['source']})\n"
        md_content += f"[Link to Tweet]({item['url']})\n\n"
        
        # Format blockquote nicely
        formatted_text = item['text'].replace('\n', '\n> ')
        md_content += f"> {formatted_text}\n\n"
        
        md_content += "### Extracted Articles & Summaries:\n"
        for summary_info in item['summaries']:
            url_display = summary_info['actual_url'] if summary_info['actual_url'] else summary_info['original_url']
            md_content += f"**🔗 Source URL:** [{url_display}]({url_display})\n\n"
            md_content += f"**📝 Summary & Findings:**\n\n"
            md_content += f"{summary_info['summary']}\n\n"
        
        md_content += "---\n\n"
        
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(md_content)
            
    print(f"\n✅ Newsletter successfully generated locally: {md_filename}")
    
    # Convert to HTML and send email
    print("Formatting email HTML...")
    html_content = markdown.markdown(md_content)
    send_email(html_content, md_content)

if __name__ == "__main__":
    asyncio.run(main())
