"""
UNIVR Research Fellowship Crawler

Crawls https://www.univr.it/it/concorsi/borse-di-studio-di-ricerca for new
research fellowship postings, stores them in Supabase, and sends Telegram
notifications when new entries are found.
"""

import logging
import os
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

from page import Record, Page

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.univr.it/it/concorsi/borse-di-studio-di-ricerca?_it_univr_aolux_portlet_albo_ConcorsiPortlet_page=1&_it_univr_aolux_portlet_albo_ConcorsiPortlet_query=&_it_univr_aolux_portlet_albo_ConcorsiPortlet_attivo=1"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1  # seconds between page requests


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------


def get_supabase_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fellowship_exists(client: Client, fellowship_link: str) -> bool:
    response = (
        client.table("fellowships").select("id").eq("id", fellowship_link).execute()
    )
    return len(response.data) > 0


def insert_fellowship(client: Client, fellowship: Record) -> None:
    record = {
        "id": fellowship.link,  # Using the link as a unique ID
        "title": fellowship.title,
        "url": fellowship.link,
        "deadline": fellowship.start_date,
        "date": fellowship.end_date,
    }
    client.table("fellowships").insert(record).execute()


# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------


def send_telegram_message(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to send Telegram message: %s", exc)


def format_notification(fellowship: Record) -> str:
    lines = [
        "🎓 <b>New Research Fellowship</b>",
        f"<b>{fellowship.title}</b>",
        f"📅 Deadline: {fellowship.end_date}",
        f"🗓 Published: {fellowship.start_date}",
        f'🔗 <a href="{fellowship.link}">Read more</a>',
    ]
    return "\n".join(lines)


def fetch_page(url: str) -> Page | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; UniVR-Fellowship-Crawler/1.0; "
            "+https://github.com/matthewexe/univr-fellowships-crawler)"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        return Page(soup)
    except requests.RequestException as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Main crawling logic
# ---------------------------------------------------------------------------


def crawl(client: Client) -> None:
    logger.info("Starting crawl of %s", BASE_URL)

    # Fetch the first page to detect page size
    link = BASE_URL

    while link:
        logger.info("Fetching page: %s", link)
        page = fetch_page(link)
        if page is None:
            logger.error("Could not fetch the page. Stopping.")
            break
        logger.info("Processing page: %s", page.soup.title.string.strip())
        fellowships = page.get_all_records()
        logger.info("Found %d fellowships on this page.", len(fellowships))

        for fellowship in fellowships:
            if fellowship_exists(client, fellowship.link):
                logger.debug("Already known: %s", fellowship.title)
            else:
                logger.info("New fellowship: %s", fellowship.title)
                insert_fellowship(client, fellowship)
                send_telegram_message(format_notification(fellowship))

        link = page.get_next_link()
        time.sleep(REQUEST_DELAY)


def main() -> None:
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    client = get_supabase_client()
    crawl(client)


if __name__ == "__main__":
    main()
