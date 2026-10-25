"""Last-resort web search: headless Chromium (Selenium) reading a search engine's results page.

Runs inside the worker container (Chromium and chromedriver are installed in its image), one browser
at a time to keep memory low. CAPTCHA and block pages raise EngineFailure so the chain moves on.
"""

from __future__ import annotations

import base64
import threading
from urllib.parse import parse_qs, quote_plus, urlparse

CHROMIUM = "/usr/bin/chromium"
CHROMEDRIVER = "/usr/bin/chromedriver"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
BLOCK_MARKERS = ("unusual traffic", "captcha", "bots use duckduckgo", "are you a robot", "verify you are human")
_one_browser = threading.Lock()

ENGINES: dict[str, tuple[str, str]] = {
    "duckduckgo": (
        "https://html.duckduckgo.com/html/?q={q}&kl={region}",
        """return Array.from(document.querySelectorAll('.result:not(.result--ad)')).map(r => {
             const a = r.querySelector('a.result__a'); const s = r.querySelector('.result__snippet');
             return a ? {url: a.href, title: a.innerText, snippet: s ? s.innerText : ''} : null;
           }).filter(Boolean);""",
    ),
    "bing": (
        "https://www.bing.com/search?q={q}&setlang=en&cc={country}",
        """return Array.from(document.querySelectorAll('li.b_algo')).map(li => {
             const a = li.querySelector('h2 a'); const p = li.querySelector('.b_caption p, p');
             return a ? {url: a.href, title: a.innerText, snippet: p ? p.innerText : ''} : null;
           }).filter(Boolean);""",
    ),
    "google": (
        "https://www.google.com/search?q={q}&hl=en&gl={country}&num=10",
        """return Array.from(document.querySelectorAll('#search a')).filter(a => a.querySelector('h3')).map(a => {
             const box = a.closest('div.g, div[data-hveid]');
             const s = box ? box.querySelector('[data-sncf], .VwiC3b') : null;
             return {url: a.href, title: a.querySelector('h3').innerText, snippet: s ? s.innerText : ''};
           });""",
    ),
}


class BrowserBlocked(Exception):
    pass


def real_url(url: str) -> str:
    """Undo DuckDuckGo (uddg=) and Bing (u=a1<base64>) redirect wrappers."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if parsed.netloc.endswith("duckduckgo.com") and "uddg" in query:
        return query["uddg"][0]
    if parsed.netloc.endswith("bing.com") and parsed.path.startswith("/ck/") and "u" in query:
        encoded = query["u"][0]
        if encoded.startswith("a1"):
            payload = encoded[2:]
            try:
                return base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
            except (ValueError, UnicodeDecodeError):
                return url
    return url


def search(engine: str, query: str, limit: int, country: str, timeout: float) -> list[dict[str, str]]:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    template, script = ENGINES[engine]
    url = template.format(q=quote_plus(query), country=country, region=f"{country}-en")
    options = Options()
    options.binary_location = CHROMIUM
    for arg in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                "--window-size=1280,2000", "--lang=en-US", f"--user-agent={USER_AGENT}"):
        options.add_argument(arg)

    with _one_browser:
        driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=options)
        try:
            driver.set_page_load_timeout(timeout)
            try:
                driver.get(url)
            except WebDriverException as exc:
                raise BrowserBlocked(f"page load failed: {exc.msg or exc}") from exc
            rows = driver.execute_script(script) or []
            if not rows:
                page = (driver.page_source or "").lower()
                if "/sorry/" in driver.current_url or any(marker in page for marker in BLOCK_MARKERS):
                    raise BrowserBlocked(f"{engine} showed a CAPTCHA or block page")
        finally:
            driver.quit()

    results: list[dict[str, str]] = []
    own_domains = ("duckduckgo.com", "bing.com", "google.com")
    for row in rows:
        target = real_url(str(row.get("url", "")))
        if target.startswith("http") and not urlparse(target).netloc.endswith(own_domains):
            results.append({"url": target, "title": str(row.get("title", "")),
                            "snippet": str(row.get("snippet", ""))})
        if len(results) >= limit:
            break
    return results
