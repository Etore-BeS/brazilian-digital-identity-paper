from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import random
import json
import time
import hashlib
import os

# POST_URL = 'https://www.instagram.com/p/DChnVHMxyBD/' # Test
# POST_URL = 'https://www.instagram.com/p/DVerZTClAbR/' # Fernanda Torres
# POST_URL = 'https://www.instagram.com/reel/DCFD_ZoyZwa/' # Bruno Mars
POST_URL = 'https://www.instagram.com/p/Cmw4CjNrctl/' # Cristiano Ronaldo

EXTRACT_JS = r"""
() => {
  const clean = s => (s || "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
  const results = [];
  const seen = new Set();

  // 1. Find every timestamp (the most stable anchor in a comment)
  document.querySelectorAll("time[datetime]").forEach(timeEl => {
    const date_iso = timeEl.getAttribute("datetime");
    const date_label = timeEl.getAttribute("title") || "";

    // 2. Find the header span that contains both the username and the time
    // This span always has the 18px line-height style for the header row
    const headerSpan = timeEl.closest('span[style*="--x-lineHeight: 18px"]');
    if (!headerSpan) return; 

    // 3. USERNAME: Find the link that points to a profile.
    // The time and username are in side-by-side spans. We go to their shared parent 
    // and grab the very first link, then take its visible text to avoid the hash.
    const profileLink = headerSpan.parentElement.querySelector('a[href][role="link"]');
    const username = clean(profileLink?.innerText || "");
    if (!username) return;

    // 4. COMMENT TEXT: 
    // Structure: <headerRowDiv> -> <commentDiv>
    const headerRowDiv = headerSpan.parentElement;
    const commentDiv = headerRowDiv?.nextElementSibling;
    
    // We look for the span with dir="auto". 
    // We exclude the headerSpan itself to ensure we don't grab the username/time again.
    const commentSpan = commentDiv?.querySelector('span[dir="auto"]');
    const comment = clean(commentSpan?.innerText || "");

    // 5. LIKES:
    // Move up to the container level and look for the action bar (likes/reply)
    let likes = "0";
    let container = timeEl;
    for (let i = 0; i < 5; i++) container = container?.parentElement;
    
    if (container) {
      let nextSection = container.nextElementSibling;
      while (nextSection) {
        // The action bar has a specific smaller height (16px)
        if ((nextSection.getAttribute("style") || "").includes("--x-height: 16px")) {
          const spans = nextSection.querySelectorAll("span");
          for (const s of spans) {
            const t = clean(s.innerText);
            // Match patterns like "12 likes", "1 me gusta", "5 curtidas"
            if (/\d+\s*(me gusta|likes?|curtidas?)/i.test(t)) {
              likes = t;
              break;
            }
          }
          break;
        }
        nextSection = nextSection.nextElementSibling;
      }
    }

    const key = username + "|" + date_iso + "|" + comment.substring(0,10);
    if (seen.has(key)) return;
    seen.add(key);
    
    results.push({ 
      username, 
      comment, 
      likes, 
      date_iso, 
      date_label 
    });
  });

  return results;
}
"""


SCROLL_JS = r"""
() => {
    // Grab every potential container on the page
    const containers = Array.from(document.querySelectorAll('div, ul, section'));
    
    for (const el of containers) {
        // Is this box mathematically capable of scrolling?
        if (el.scrollHeight > el.clientHeight + 10 && el.clientHeight > 0) {
            
            // Does this scrollable box actually contain our comments?
            if (el.querySelectorAll('time[datetime]').length > 0) {
                
                const before = el.scrollTop;
                // Physical Test: Force it down by 50px
                el.scrollTop += 50;
                
                // If it moved, OR if it's already resting at the absolute bottom
                if (el.scrollTop > before || (before > 0 && Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight) < 10)) {
                    
                    // JACKPOT. Yank it to the bottom.
                    el.scrollTop = el.scrollHeight;
                    return true;
                }
            }
        }
    }
    return false;
}
"""


def main():
    # Use the sync version of Stealth
    # Note: Stealth().use_sync() is the sync equivalent
    with Stealth().use_sync(sync_playwright()) as p:
        # Launching with a persistent context
        context = p.chromium.launch_persistent_context(
            "./instagram_session",
            headless=False,
            # This helps prevent the "Automation Controlled" flag
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.instagram.com/")

        print("Browser is open. You can now use the Debug Console.")
        print("Try typing: page.locator('input').count()")
        
        page.pause()
        
        page.goto(POST_URL)
        
        page.wait_for_selector("time[datetime]", timeout=15000)
        time.sleep(2)
        
        FILE_PATH = f"{POST_URL.split('/')[-2]}_comments.json"
        
        collected = {}
        
        # 2. Check if the file exists, and load existing comments into our dictionary
        if os.path.exists(FILE_PATH):
            try:
                with open(FILE_PATH, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    for item in existing_data:
                        # Rebuild the dictionary using the saved hash_id
                        if 'hash_id' in item:
                            collected[item['hash_id']] = item
                print(f"Loaded {len(collected)} existing comments from {FILE_PATH}")
            except json.JSONDecodeError:
                print(f"Warning: {FILE_PATH} exists but is empty or corrupted. Starting fresh.")
        
        previous_db_count = len(collected)
        previous_visible_hashes = set()
        no_new_rounds = 0
        break_point = 0

        try:
            while True:
                while break_point < 3:
                    while no_new_rounds < 5:
                        # --- BATCH SCROLLING ---
                        # Scroll 3 times quickly before we bother extracting
                        for _ in range(5):
                            page.evaluate(SCROLL_JS)
                            page.wait_for_timeout(random.randrange(2000, 3000, 250))
                            
                        # --- NOW EXTRACT THE BATCH ---
                        items = page.evaluate(EXTRACT_JS)
                        current_visible_hashes = set()

                        for item in items:
                            raw_data = f"{item['username']}|{item['date_iso']}|{item['likes']}|{item['comment']}"
                            comment_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
                            current_visible_hashes.add(comment_hash)
                            
                            if comment_hash not in collected:
                                item['hash_id'] = comment_hash
                                collected[comment_hash] = item

                        current_db_count = len(collected)

                        if current_visible_hashes == previous_visible_hashes:
                            no_new_rounds += 1
                            print(f"No movement detected on screen. Round {no_new_rounds}/5")
                        else:
                            no_new_rounds = 0
                            if current_db_count > previous_db_count:
                                print(f"Batch Scraped! Added {current_db_count - previous_db_count} new comments. (Total Unique: {current_db_count})")
                            else:
                                print(f"Batch Scraped! Bypassing already saved comments... (Visible: {len(current_visible_hashes)})")

                        previous_db_count = current_db_count
                        previous_visible_hashes = current_visible_hashes

                        page.evaluate(SCROLL_JS)
                        page.wait_for_timeout(random.randrange(5000, 20000, 250))
                    

                    comments = list(collected.values())
                    print(f"\nDone with batch! Total unique comments: {len(comments)}")

                    with open(FILE_PATH, "w", encoding="utf-8") as f:
                        # We use 'w' to overwrite the file entirely with the updated JSON array
                        json.dump(comments, f, ensure_ascii=False, indent=2)
                        
                    print(f"Saved to {FILE_PATH}")
                    
                    # Wait 10 minutes (1200,000 ms) before restarting the loop
                    print("Waiting from 3 to 10 minutes before trying to load more...")
                    wait_time = random.randrange(180000, 600000, 60000)
                    print(f'Wait Time Select: {wait_time/60000} minutes')
                    page.wait_for_timeout(wait_time)
                    
                    
                    # Reset the counter to re-enter the inner loop
                    print("Resuming scrape...")
                    no_new_rounds = 0
                    break_point += 1
                    
                page.pause()
                
            # --- CATCH CTRL+C HERE ---
        except KeyboardInterrupt:
            print("\n\n🛑 Script interrupted by user (Ctrl+C). Initiating emergency save...")
            
        except Exception as e:
            print(f"\n\n❌ Script crashed with error: {e}. Initiating emergency save...")
            
        # --- FINALLY BLOCK ALWAYS RUNS, EVEN ON CRASH OR CTRL+C ---
        finally:
            if collected:
                comments = list(collected.values())
                with open(FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(comments, f, ensure_ascii=False, indent=2)
                print(f"✅ Emergency Save Complete! {len(comments)} comments secured in {FILE_PATH}.")
            
            # Close the browser cleanly so session cookies aren't corrupted
            context.close()
            print("Browser closed. Exiting safely.")


def main_v2():
    FILE_PATH = f"{POST_URL.split('/')[-2]}_comments.json"
    collected = {}
    
    # 1. Load existing data BEFORE the browser loop starts so we don't lose it on crash
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                for item in existing_data:
                    if 'hash_id' in item:
                        collected[item['hash_id']] = item
            print(f"Loaded {len(collected)} existing comments from {FILE_PATH}")
        except json.JSONDecodeError:
            print(f"Warning: {FILE_PATH} exists but is empty or corrupted. Starting fresh.")
    
    MAX_CRASH_RETRIES = 5
    crash_attempts = 0

    # --- OUTER CRASH RECOVERY LOOP ---
    while crash_attempts < MAX_CRASH_RETRIES:
        try:
            # We open the Playwright context inside the loop. 
            # If it crashes, the 'with' block closes cleanly, clearing the exhausted RAM.
            with Stealth().use_sync(sync_playwright()) as p:
                context = p.chromium.launch_persistent_context(
                    "./instagram_session",
                    headless=False,
                    # Added critical flags to reduce Chromium memory overhead and prevent Aw Snap
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",  # Forces Chrome to use disk instead of limited RAM
                        "--no-sandbox",
                        "--disable-gpu" 
                    ]
                )
                
                page = context.pages[0] if context.pages else context.new_page()
                
                # Add a crash listener to print out when the page dies visually
                page.on("crash", lambda: print("\n💥 Page crashed! (Aw, Snap!)"))
                
                page.goto("https://www.instagram.com/")
                time.sleep(2)
                
                page.goto(POST_URL)
                page.wait_for_selector("time[datetime]", timeout=15000)
                time.sleep(2)
                
                previous_db_count = len(collected)
                previous_visible_hashes = set()
                no_new_rounds = 0
                break_point = 0

                while True:
                    while break_point < 3:
                        while no_new_rounds < 5:
                            
                            # --- BATCH SCROLLING ---
                            for _ in range(5):
                                page.evaluate(SCROLL_JS)
                                page.wait_for_timeout(random.randrange(2000, 3000, 250))
                                
                            # --- EXTRACT THE BATCH ---
                            items = page.evaluate(EXTRACT_JS)
                            current_visible_hashes = set()

                            for item in items:
                                raw_data = f"{item['username']}|{item['date_iso']}|{item['likes']}|{item['comment']}"
                                comment_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
                                current_visible_hashes.add(comment_hash)
                                
                                if comment_hash not in collected:
                                    item['hash_id'] = comment_hash
                                    collected[comment_hash] = item

                            current_db_count = len(collected)

                            if current_visible_hashes == previous_visible_hashes:
                                no_new_rounds += 1
                                print(f"No movement detected on screen. Round {no_new_rounds}/5")
                            else:
                                no_new_rounds = 0
                                if current_db_count > previous_db_count:
                                    print(f"Batch Scraped! Added {current_db_count - previous_db_count} new comments. (Total Unique: {current_db_count})")
                                else:
                                    print(f"Batch Scraped! Bypassing already saved comments... (Visible: {len(current_visible_hashes)})")

                            previous_db_count = current_db_count
                            previous_visible_hashes = current_visible_hashes

                            page.evaluate(SCROLL_JS)
                            page.wait_for_timeout(random.randrange(5000, 20000, 250))
                        
                        comments = list(collected.values())
                        print(f"\nDone with batch! Total unique comments: {len(comments)}")

                        with open(FILE_PATH, "w", encoding="utf-8") as f:
                            json.dump(comments, f, ensure_ascii=False, indent=2)
                        print(f"Saved to {FILE_PATH}")
                        
                        print("Waiting from 3 to 10 minutes before trying to load more...")
                        wait_time = random.randrange(180000, 600000, 60000)
                        print(f'Wait Time Select: {wait_time/60000} minutes')
                        page.wait_for_timeout(wait_time)
                        
                        print("Resuming scrape...")
                        no_new_rounds = 0
                        break_point += 1
                        
                    # --- AUTOMATED RECOVERY PHASE ---
                    print("\n⚠️ Hit 3 full wait cycles. Instagram stopped loading comments.")
                    
                    # Initialize this variable right before your `while True:` loop starts at the top of main()
                    # consecutive_refreshes = 0 
                    
                    if consecutive_refreshes < 2:
                        consecutive_refreshes += 1
                        print(f"🔄 Auto-Recovery Attempt {consecutive_refreshes}/2: Trying to clear UI and refresh...")
                        
                        # Action 1: Try to dismiss any "Log in to see more" popups by pressing Escape
                        try:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(1000)
                            page.keyboard.press("Escape") 
                        except Exception:
                            pass
                        
                        # Action 2: Hard reload the page to clear soft rate-limits and DOM bloat
                        print("Reloading page...")
                        page.reload()
                        
                        try:
                            page.wait_for_selector("time[datetime]", timeout=15000)
                            page.wait_for_timeout(3000)
                            print("Page reloaded successfully. Fast-forwarding through saved comments...")
                        except Exception as e:
                            print(f"Warning during reload: {e}")
                        
                        # Reset loop variables to let the script try scraping again
                        break_point = 0
                        no_new_rounds = 0
                        previous_visible_hashes = set() # Force a fresh screen check
                        
                    else:
                        # --- LAST RESORT PAUSE ---
                        print("\n🚨 Auto-recovery failed 2 times in a row. Pausing as a last resort.")
                        print("Please look at the browser window to solve the block (CAPTCHA, Login popup, etc.).")
                        print("Click 'Resume' in the Playwright Inspector once you fix it.")
                        page.pause()
                        
                        # Reset everything so if you manually resume, it starts fresh
                        consecutive_refreshes = 0
                        break_point = 0
                        no_new_rounds = 0
                        previous_visible_hashes = set()
                    
        # Catch Ctrl+C manually to escape the outer loop
        except KeyboardInterrupt:
            print("\n\n🛑 Script interrupted by user (Ctrl+C). Initiating emergency save...")
            break 
            
        # Catch the "Target Closed" / "Page Crashed" Exception
        except Exception as e:
            crash_attempts += 1
            print(f"\n\n❌ Browser crashed with error: {e}")
            print(f"⚠️ Recovering... Crash {crash_attempts}/{MAX_CRASH_RETRIES}. Restarting to clear RAM...")
            time.sleep(5) # Let the OS fully kill Chromium and release the memory
            
        finally:
            # Runs on exit, Ctrl+C, or crash before the browser restarts
            if collected:
                comments = list(collected.values())
                with open(FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(comments, f, ensure_ascii=False, indent=2)
                print(f"✅ Data Secured! {len(comments)} comments saved.")


if __name__ == "__main__":
    main_v2()