import json
import os
from typing import List, Set, Tuple, Optional, Dict, Any
from queue import Queue
from pydantic import create_model  # Added this import

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
)

from models.venue import Venue
from utils.data_utils import is_complete_venue, is_duplicate_venue

# Shared queue for log streaming
log_queue = Queue()

def stream_log(message: str):
    print(message)
    log_queue.put(message)

def get_browser_config() -> BrowserConfig:
    return BrowserConfig(
        browser_type="chromium",
        headless=False,
        verbose=True,
    )

def get_llm_strategy(required_keys: List[str]) -> LLMExtractionStrategy:
    """
    Generate LLM strategy based on user-defined required keys.
    """
    schema_dict = {key: (Optional[str], None) for key in required_keys}
    DynamicModel = create_model("DynamicVenue", **schema_dict)

    return LLMExtractionStrategy(
        provider="groq/deepseek-r1-distill-llama-70b",
        api_token=os.getenv("GROQ_API_KEY"),
        schema=DynamicModel.schema(),
        extraction_type="schema",
        instruction=(
            f"Extract venue data with the following fields: {', '.join(required_keys)}. "
            "Provide them from the given HTML content."
        ),
        input_format="markdown",
        verbose=True,
    )


async def check_no_results(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str,
) -> bool:
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
        ),
    )
    if result.success:
        return "No Results Found" in result.cleaned_html
    else:
        stream_log(f"[ERROR] Failed to check for 'No Results Found': {result.error_message}")
    return False

async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
) -> Tuple[List[dict], bool]:
    url = f"{base_url}?page={page_number}"
    stream_log(f"[LOAD] Page {page_number} - {url}")

    no_results = await check_no_results(crawler, url, session_id)
    if no_results:
        return [], True

    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=llm_strategy,
            css_selector=css_selector,
            session_id=session_id,
        ),
    )

    if not (result.success and result.extracted_content):
        stream_log(f"[ERROR] Failed to extract page {page_number}: {result.error_message}")
        return [], True  # Stop on failure

    try:
        extracted_data = json.loads(result.extracted_content)
    except json.JSONDecodeError:
        stream_log(f"[ERROR] JSON decode error on page {page_number}")
        return [], True  # Stop on decode error

    if not extracted_data:
        stream_log(f"[INFO] No venues extracted on page {page_number}. Stopping.")
        return [], True

    stream_log(f"[PARSE] Raw extracted data: {extracted_data}")

    complete_venues = []
    for venue in extracted_data:
        stream_log(f"[CHECK] Processing venue: {venue}")

        if venue.get("error") is False:
            venue.pop("error", None)

        if not is_complete_venue(venue, required_keys):
            continue

        if is_duplicate_venue(venue["name"], seen_names):
            stream_log(f"[SKIP] Duplicate venue '{venue['name']}'")
            continue

        seen_names.add(venue["name"])
        complete_venues.append(venue)

    if not complete_venues:
        stream_log(f"[INFO] No complete venues on page {page_number}. Stopping.")
        return [], True

    stream_log(f"[SUCCESS] Page {page_number}: {len(complete_venues)} venues extracted")
    return complete_venues, False

async def start_scraping_job(
    base_url: str,
    css_selector: str,
    required_keys: List[str],
    max_pages: int = 10
) -> List[dict]:
    """
    Starts a scraping job with dynamic inputs.

    Args:
        base_url (str): The target website URL.
        css_selector (str): CSS selector for venue blocks.
        required_keys (List[str]): Required data fields.
        max_pages (int): Maximum number of pages to scrape.

    Returns:
        List[dict]: All valid extracted venues.
    """
    browser_config = get_browser_config()
    llm_strategy = get_llm_strategy(required_keys)  # Fixed: passing required_keys
    session_id = "user-session-123"

    all_venues = []
    seen_names = set()
    page = 1

    async with AsyncWebCrawler(config=browser_config) as crawler:
        while page <= max_pages:
            stream_log(f"[INFO] Scraping page {page} of max {max_pages}...")
            venues, stop = await fetch_and_process_page(
                crawler=crawler,
                page_number=page,
                base_url=base_url,
                css_selector=css_selector,
                llm_strategy=llm_strategy,
                session_id=session_id,
                required_keys=required_keys,
                seen_names=seen_names,
            )
            all_venues.extend(venues)
            if stop:
                stream_log(f"[STOP] Ending early after page {page} due to condition.")
                break
            page += 1
        else:
            stream_log(f"[LIMIT] Reached maximum page limit: {max_pages}. Stopping...")

    stream_log(f"[DONE] Scraping finished. {len(all_venues)} total venues collected.")
    return all_venues