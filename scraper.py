import asyncio
import json
import os
import csv
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

STATE_FILE = "state.json"
USERNAME = "das_think" # Set this to grab likes!

async def save_state(context):
    await context.storage_state(path=STATE_FILE)
    
    # If on Github Actions, we don't have a persistent disk.
    # While we can't easily push the new session back to the repo secret, 
    # printing it or handling it can be complex. For now, the old valid cookies work for a long time.

async def get_tweets_from_page(page, scroll_attempts=5, days_limit=3):
    tweets_data = []
    seen_urls = set()
    
    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_limit)
    print(f"Scrolling through page ({scroll_attempts} attempts max)...")
    print(f"Filtering for tweets newer than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    for i in range(scroll_attempts):
        try:
            # Wait for tweets to load
            print(f"Current URL: {page.url}")
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)
            
            # Get all visible tweets
            tweets = await page.query_selector_all('article[data-testid="tweet"]')
            
            all_tweets_too_old = True
            found_new_tweets_in_batch = False
            
            for tweet in tweets:
                try:
                    # Get tweet link / timestamp
                    time_element = await tweet.query_selector('a > time')
                    if time_element:
                        parent_a = await time_element.evaluate_handle('el => el.parentElement')
                        url = await parent_a.get_attribute('href')
                        url = f"https://x.com{url}"
                        timestamp = await time_element.get_attribute('datetime')
                    else:
                        url = ""
                        timestamp = ""

                    tweet_date = None
                    if timestamp:
                        # Convert ISO format timestamp to datetime object
                        tweet_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        if tweet_date < cutoff_date:
                            continue # Skip this tweet, it's older than 3 days
                        all_tweets_too_old = False
                    
                    # If we make it here, the tweet is within the last 3 days (or has no date)
                    found_new_tweets_in_batch = True
                    
                    # Get tweet text
                    text_element = await tweet.query_selector('div[data-testid="tweetText"]')
                    text = await text_element.inner_text() if text_element else ""

                    # Get author info
                    user_element = await tweet.query_selector('div[data-testid="User-Name"]')
                    author = await user_element.inner_text() if user_element else ""
                    
                    # Get external links (t.co links)
                    external_links = []
                    # Twitter wraps all outgoing links in t.co
                    link_elements = await tweet.query_selector_all('a[href*="t.co"]')
                    for element in link_elements:
                        link_href = await element.get_attribute('href')
                        if link_href:
                            external_links.append(link_href)
                            
                    external_links_str = ", ".join(list(set(external_links)))
                    
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        tweets_data.append({
                            "url": url,
                            "author": author.replace('\n', ' '),
                            "text": text,
                            "timestamp": timestamp,
                            "embedded_links": external_links_str
                        })
                except Exception as e:
                    # Ignore partial parse errors for individual tweets
                    pass
            
            # If we successfully parsed tweets in this batch, and ALL of them were older than 3 days,
            # it means we've scrolled past the 3-day window. We can stop scrolling early!
            if tweets and all_tweets_too_old and not found_new_tweets_in_batch:
                print("Reached tweets older than 3 days. Stopping scroll early.")
                break
                
            # Scroll down to trigger lazy loading
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(3000) # Wait 3 seconds for new tweets to load
        except Exception as e:
            print(f"No tweets found or timeout reached. Error details: {e}")
            await page.screenshot(path="debug_timeout.png")
            break
            
    return tweets_data

async def main():
    async with async_playwright() as p:
        # Check if we are running in the cloud (Github Actions)
        is_github = os.environ.get("GITHUB_ACTIONS") == "true"
        
        # We need a visible browser to manually log in if needed locally
        browser = await p.chromium.launch(
            headless=is_github,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"]
        )
        
        # If we are in the cloud and passing the secret cookie state
        if is_github and "X_STATE_JSON" in os.environ:
            with open(STATE_FILE, "w") as f:
                f.write(os.environ["X_STATE_JSON"])
                
        # Try loading previous session if state.json exists
        needs_login = True
        if os.path.exists(STATE_FILE):
            # Check if it has the auth_token cookie
            with open(STATE_FILE, 'r') as f:
                try:
                    state_data = json.load(f)
                    cookies_list = state_data.get('cookies', [])
                    if any(c.get('name') == 'auth_token' for c in cookies_list):
                        needs_login = False
                        print("Loaded saved session.")
                    else:
                        print("Saved session is invalid/expired. Deleting and starting fresh.")
                        os.remove(STATE_FILE)
                except Exception:
                    print("Could not read session file. Starting fresh.")
                    os.remove(STATE_FILE)
        
        if not needs_login:
            context = await browser.new_context(
                storage_state=STATE_FILE,
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
        else:
            if is_github:
                print("❌ Running in GitHub Actions but no valid state.json found. Cannot manually sign in!")
                await browser.close()
                raise Exception("Missing or expired Twitter authentication in GitHub Actions.")
                
            print("No valid saved session found.")
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            page = await context.new_page()
            
            print("Opening X to log in...")
            await page.goto("https://x.com/login")
            print("\n*** ACTION REQUIRED ***")
            print("Please log in manually on the browser window.")
            print("Once you are fully logged in and see your home timeline, press Enter in this terminal.")
            input("Press Enter to continue...")
            
            # Save the session immediately after manual login
            await save_state(context)
            print("Session saved! Next time you run this, you will be logged in automatically.")
            
        print("\n=== Fetching Bookmarks ===")
        await page.goto("https://x.com/i/bookmarks")
        # You can increase scroll_attempts to scrape more deeply
        bookmarks = await get_tweets_from_page(page, scroll_attempts=10) 
        
        likes = []
        if USERNAME != "<replace_with_your_x_username>":
            print(f"\n=== Fetching Likes for @{USERNAME} ===")
            await page.goto(f"https://x.com/{USERNAME}/likes")
            likes = await get_tweets_from_page(page, scroll_attempts=10)
        else:
            print("\nSkipping Likes because USERNAME was not set in the script.")
            print("Edit scraper.py and set the USERNAME variable at the top to scrape your likes.")
            
        # Always save state at the very end to keep cookies fresh!
        await save_state(context)
        await browser.close()
        
        # Save Bookmarks to CSV
        if bookmarks:
            with open('bookmarks.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["url", "author", "text", "timestamp", "embedded_links"])
                writer.writeheader()
                writer.writerows(bookmarks)
            print(f"\n✅ Saved {len(bookmarks)} bookmarks to bookmarks.csv")
            
        # Save Likes to CSV
        if likes:
            with open('likes.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["url", "author", "text", "timestamp", "embedded_links"])
                writer.writeheader()
                writer.writerows(likes)
            print(f"✅ Saved {len(likes)} likes to likes.csv")

if __name__ == "__main__":
    asyncio.run(main())
