import asyncio
import json
import os
import csv
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

STATE_FILE = "state.json"
BRAIN_FILE = "brain.json"
USERNAME = "das_think" # Set this to grab likes!

def load_brain():
    if os.path.exists(BRAIN_FILE):
        try:
            with open(BRAIN_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"seen_tweets": [], "seen_articles": [], "topics": {}}

def save_brain(data):
    with open(BRAIN_FILE, 'w') as f:
        json.dump(data, f, indent=2)

async def save_state(context):
    await context.storage_state(path=STATE_FILE)

async def get_tweets_from_page(page, brain_data, global_state, scroll_attempts=10):
    tweets_data = []
    seen_urls = set()
    brain_seen = set(brain_data.get("seen_tweets", []))
    
    print(f"Scrolling through page ({scroll_attempts} attempts max)...")
    
    for i in range(scroll_attempts):
        try:
            print(f"Current URL: {page.url}")
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)
            tweets = await page.query_selector_all('article[data-testid="tweet"]')
            
            all_tweets_seen_in_batch = True
            found_new_in_batch = False
            
            for tweet in tweets:
                if global_state['total_extracted'] >= global_state['limit']:
                    break
                    
                try:
                    time_element = await tweet.query_selector('a > time')
                    if time_element:
                        parent_a = await time_element.evaluate_handle('el => el.parentElement')
                        url = await parent_a.get_attribute('href')
                        url = f"https://x.com{url}"
                        timestamp = await time_element.get_attribute('datetime')
                    else:
                        url = ""
                        timestamp = ""

                    if url and url in brain_seen:
                        continue
                        
                    all_tweets_seen_in_batch = False
                    
                    if url and url not in seen_urls:
                        found_new_in_batch = True
                        seen_urls.add(url)
                        
                        text_element = await tweet.query_selector('div[data-testid="tweetText"]')
                        text = await text_element.inner_text() if text_element else ""

                        user_element = await tweet.query_selector('div[data-testid="User-Name"]')
                        author = await user_element.inner_text() if user_element else ""
                        
                        external_links = []
                        link_elements = await tweet.query_selector_all('a[href*="t.co"]')
                        for element in link_elements:
                            link_href = await element.get_attribute('href')
                            if link_href:
                                external_links.append(link_href)
                                
                        external_links_str = ", ".join(list(set(external_links)))
                        
                        tweets_data.append({
                            "url": url,
                            "author": author.replace('\n', ' '),
                            "text": text,
                            "timestamp": timestamp,
                            "embedded_links": external_links_str
                        })
                        
                        global_state['total_extracted'] += 1
                        brain_data.setdefault("seen_tweets", []).append(url)
                        brain_seen.add(url)
                except Exception:
                    pass
            
            if global_state['total_extracted'] >= global_state['limit']:
                print(f"Reached maximum limit of {global_state['limit']} extracted items. Stopping.")
                break
                
            if tweets and all_tweets_seen_in_batch and not found_new_in_batch:
                print("Hit memory boundary (all visible tweets already seen). Stopping scroll early.")
                break
                
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"No tweets found or timeout reached. Error details: {e}")
            await page.screenshot(path="debug_timeout.png")
            break
            
    return tweets_data

async def main():
    brain_data = load_brain()
    global_state = {'total_extracted': 0, 'limit': 50}
    
    async with async_playwright() as p:
        is_github = os.environ.get("GITHUB_ACTIONS") == "true"
        
        browser = await p.chromium.launch(
            headless=is_github,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"]
        )
        
        if is_github and "X_STATE_JSON" in os.environ:
            with open(STATE_FILE, "w") as f:
                f.write(os.environ["X_STATE_JSON"])
                
        needs_login = True
        if os.path.exists(STATE_FILE):
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
            
            await save_state(context)
            print("Session saved! Next time you run this, you will be logged in automatically.")
            
        print("\n=== Fetching Bookmarks ===")
        await page.goto("https://x.com/i/bookmarks")
        bookmarks = await get_tweets_from_page(page, brain_data, global_state, scroll_attempts=10) 
        
        likes = []
        if USERNAME != "<replace_with_your_x_username>":
            print(f"\n=== Fetching Likes for @{USERNAME} ===")
            await page.goto(f"https://x.com/{USERNAME}/likes")
            likes = await get_tweets_from_page(page, brain_data, global_state, scroll_attempts=10)
        else:
            print("\nSkipping Likes because USERNAME was not set in the script.")
            print("Edit scraper.py and set the USERNAME variable at the top to scrape your likes.")
            
        await save_state(context)
        await browser.close()
        
        save_brain(brain_data)
        
        if bookmarks:
            with open('bookmarks.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["url", "author", "text", "timestamp", "embedded_links"])
                writer.writeheader()
                writer.writerows(bookmarks)
            print(f"\n✅ Saved {len(bookmarks)} bookmarks to bookmarks.csv")
            
        if likes:
            with open('likes.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["url", "author", "text", "timestamp", "embedded_links"])
                writer.writeheader()
                writer.writerows(likes)
            print(f"✅ Saved {len(likes)} likes to likes.csv")

if __name__ == "__main__":
    asyncio.run(main())
