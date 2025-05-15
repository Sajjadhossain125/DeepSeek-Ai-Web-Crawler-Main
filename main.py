import asyncio
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

from config import BASE_URL, CSS_SELECTOR, REQUIRED_KEYS
from utils.data_utils import save_venues_to_csv
from utils.scraper_utils import (
    fetch_and_process_page,
    get_browser_config,
    get_llm_strategy,
)

load_dotenv()

async def crawl_venues():
    """
    Main function to crawl venue data from the website.
    """
    browser_config = get_browser_config()
    llm_strategy = get_llm_strategy(REQUIRED_KEYS)  
    session_id = "venue_crawl_session"

    page_number = 1
    all_venues = []
    seen_names = set()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        while True:
            venues, no_results_found = await fetch_and_process_page(
                crawler=crawler,
                page_number=page_number,
                base_url=BASE_URL,
                css_selector=CSS_SELECTOR,
                llm_strategy=llm_strategy,
                session_id=session_id,
                required_keys=REQUIRED_KEYS,
                seen_names=seen_names,
            )

            if no_results_found or not venues:
                print(f"No venues found on page {page_number}. Ending crawl.")
                break

            all_venues.extend(venues)
            page_number += 1
            await asyncio.sleep(2)

    if all_venues:
        save_venues_to_csv(all_venues, "complete_venues.csv")
        print(f" Saved {len(all_venues)} venues to 'complete_venues.csv'.")
    else:
        print(" No venues were found during the crawl.")

    llm_strategy.show_usage()

async def main():
    await crawl_venues()

if __name__ == "__main__":
    asyncio.run(main())
