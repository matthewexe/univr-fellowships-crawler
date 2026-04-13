"""
UNIVR Research Fellowship Crawler

Crawls https://www.univr.it/it/concorsi/borse-di-studio-di-ricerca for new
research fellowship postings, stores them in Supabase, and sends Telegram
notifications when new entries are found.
"""

import logging
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.univr.it/it/concorsi/borse-di-studio-di-ricerca"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1  # seconds between page requests


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def get_supabase_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fellowship_exists(client: Client, fellowship_id: str) -> bool:
    response = (
        client.table("fellowships")
        .select("id")
        .eq("id", fellowship_id)
        .execute()
    )
    return len(response.data) > 0


def insert_fellowship(client: Client, fellowship: dict) -> None:
    client.table("fellowships").insert(fellowship).execute()


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


def format_notification(fellowship: dict) -> str:
    lines = ["🎓 <b>New Research Fellowship</b>"]
    lines.append(f"<b>{fellowship['title']}</b>")
    if fellowship.get("deadline"):
        lines.append(f"📅 Deadline: {fellowship['deadline']}")
    if fellowship.get("date"):
        lines.append(f"🗓 Published: {fellowship['date']}")
    if fellowship.get("department"):
        lines.append(f"🏛 Department: {fellowship['department']}")
    if fellowship.get("url"):
        lines.append(f"🔗 <a href=\"{fellowship['url']}\">Read more</a>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def build_offset_url(offset: int) -> str:
    if offset == 0:
        return BASE_URL
    return f"{BASE_URL}?limitstart={offset}"


def fetch_page(url: str) -> BeautifulSoup | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; UniVR-Fellowship-Crawler/1.0; "
            "+https://github.com/matthewexe/univr-fellowships-crawler)"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None


def parse_fellowships(soup: BeautifulSoup, base_url: str = "https://www.univr.it") -> list[dict]:
    """Extract fellowship entries from a parsed page.

    The UNIVR fellowship listing page renders items inside a ``<table>`` or
    inside ``<div>`` blocks depending on the Joomla template version.  We try
    both approaches and return whichever finds entries.
    """
    entries: list[dict] = []

    # --- Strategy 1: table rows (most common for UNIVR concorsi pages) -----
    table = soup.find("table", class_=lambda c: c and "concorsi" in c.lower())
    if table is None:
        table = soup.find("table")

    if table:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue
            link_tag = row.find("a", href=True)
            if not link_tag:
                continue
            href = link_tag["href"]
            if not href.startswith("http"):
                href = base_url + href
            title = link_tag.get_text(strip=True)
            if not title:
                continue
            text_parts = [cell.get_text(strip=True) for cell in cells]
            fellowship = {
                "id": href,
                "title": title,
                "url": href,
                "date": _find_date(text_parts),
                "deadline": _find_deadline(text_parts),
                "department": _find_department(text_parts, title),
            }
            entries.append(fellowship)
        if entries:
            return entries

    # --- Strategy 2: article/div blocks ------------------------------------
    items = soup.find_all("div", class_=lambda c: c and any(
        kw in c.lower() for kw in ("concorso", "fellowship", "item", "article", "borse")
    ))
    if not items:
        items = soup.find_all("article")

    for item in items:
        link_tag = item.find("a", href=True)
        if not link_tag:
            continue
        href = link_tag["href"]
        if not href.startswith("http"):
            href = base_url + href
        title = link_tag.get_text(strip=True)
        if not title:
            heading = item.find(["h2", "h3", "h4"])
            title = heading.get_text(strip=True) if heading else ""
        if not title:
            continue
        text = item.get_text(separator=" ", strip=True)
        fellowship = {
            "id": href,
            "title": title,
            "url": href,
            "date": _find_date([text]),
            "deadline": _find_deadline([text]),
            "department": _find_department([text], title),
        }
        entries.append(fellowship)

    return entries


def _find_date(parts: list[str]) -> str | None:
    """Try to extract a publication date from a list of text strings."""
    date_re = re.compile(r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b")
    for part in parts:
        match = date_re.search(part)
        if match:
            return match.group()
    return None


def _find_deadline(parts: list[str]) -> str | None:
    """Try to extract a deadline from a list of text strings."""
    for part in parts:
        lower = part.lower()
        if any(kw in lower for kw in ("scadenza", "deadline", "entro il", "entro")):
            date_re = re.compile(r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b")
            match = date_re.search(part)
            if match:
                return match.group()
    return None


def _find_department(parts: list[str], title: str) -> str | None:
    """Try to extract the department name from text parts."""
    for part in parts:
        lower = part.lower()
        if any(kw in lower for kw in ("dipartimento", "department", "dept")):
            return part.strip()
    return None


def detect_page_size(soup: BeautifulSoup) -> int:
    """Detect how many items are shown per page from pagination links."""
    pagination = soup.find(class_=lambda c: c and "pagination" in c.lower())
    if not pagination:
        return 10  # sensible default for UNIVR/Joomla

    # Look for limitstart values in pagination links
    offsets: list[int] = []
    for a in pagination.find_all("a", href=True):
        match = re.search(r"limitstart=(\d+)", a["href"])
        if match:
            offsets.append(int(match.group(1)))

    if len(offsets) >= 2:
        offsets_sorted = sorted(set(offsets))
        if len(offsets_sorted) >= 2:
            return offsets_sorted[1] - offsets_sorted[0]
    return 10


def has_next_page(soup: BeautifulSoup, current_offset: int, page_size: int) -> bool:
    """Return True if there is a page after the current one."""
    pagination = soup.find(class_=lambda c: c and "pagination" in c.lower())
    if not pagination:
        return False
    for a in pagination.find_all("a", href=True):
        match = re.search(r"limitstart=(\d+)", a["href"])
        if match and int(match.group(1)) > current_offset:
            return True
    # Also check for a "next" button text
    for a in pagination.find_all("a"):
        text = a.get_text(strip=True).lower()
        if text in ("next", "successivo", "»", ">"):
            return True
    return False


# ---------------------------------------------------------------------------
# Main crawling logic
# ---------------------------------------------------------------------------

def crawl(client: Client) -> None:
    logger.info("Starting crawl of %s", BASE_URL)

    # Fetch the first page to detect page size
    first_soup = fetch_page(BASE_URL)
    if first_soup is None:
        logger.error("Could not fetch the first page. Aborting.")
        return

    page_size = detect_page_size(first_soup)
    logger.info("Detected page size: %d", page_size)

    offset = 0
    total_new = 0

    while True:
        if offset == 0:
            soup = first_soup
        else:
            url = build_offset_url(offset)
            logger.info("Fetching page at offset %d: %s", offset, url)
            soup = fetch_page(url)
            if soup is None:
                logger.error("Could not fetch page at offset %d. Stopping.", offset)
                break
            time.sleep(REQUEST_DELAY)

        fellowships = parse_fellowships(soup)
        if not fellowships:
            logger.info("No fellowships found at offset %d. Stopping.", offset)
            break

        logger.info("Found %d fellowships on page (offset=%d)", len(fellowships), offset)

        all_known = True
        for fellowship in fellowships:
            if fellowship_exists(client, fellowship["id"]):
                logger.debug("Already known: %s", fellowship["title"])
            else:
                all_known = False
                logger.info("New fellowship: %s", fellowship["title"])
                insert_fellowship(client, fellowship)
                total_new += 1
                send_telegram_message(format_notification(fellowship))

        # Early-stop: every entry on this page is already stored
        if all_known:
            logger.info(
                "All fellowships on offset=%d are already in the database. "
                "Stopping early.",
                offset,
            )
            break

        if not has_next_page(soup, offset, page_size):
            logger.info("No more pages. Crawl complete.")
            break

        offset += page_size

    logger.info("Crawl finished. %d new fellowship(s) found.", total_new)


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
