"""Guard for the search-page full-render fix.

Measured live (2026-09-04): a LinkedIn jobs search page holds 25
``li.scaffold-layout__list-item``, and all 25 carry a readable
``data-occludable-job-id`` attribute with zero scrolling. Only 9 of them
render an ``a[href*="/jobs/view/"]`` anchor unscrolled: LinkedIn virtualizes
the anchor/title content per card. ``_extract_job_ids`` read only the anchor
selector, so a single unscrolled page returned ~9-12 of the 25 available ids.

This fixture reproduces that split (25 list items, 9 anchors) with
``page.set_content()`` so the extractor's real JS runs against a real DOM,
no LinkedIn network call involved. Uses the same real-chromium pattern as
``tests/test_action_signals_dom.py``.
"""

from __future__ import annotations

import pytest
from patchright.async_api import async_playwright

from linkedin_mcp_server.scraping.extractor import LinkedInExtractor

pytestmark = pytest.mark.browser_dom

TOTAL_ITEMS = 25
ANCHOR_STEP = 3  # indices 0,3,6,...,24 -> 9 of 25 carry an anchor


def _search_page_html() -> str:
    cards = []
    for i in range(TOTAL_ITEMS):
        job_id = 1000000 + i
        inner = f"<div>Job title {i}</div>"
        if i % ANCHOR_STEP == 0:
            inner += f'<a href="/jobs/view/{job_id}/">Job title {i}</a>'
        cards.append(
            f'<li class="scaffold-layout__list-item" '
            f'data-occludable-job-id="{job_id}">{inner}</li>'
        )
    return (
        "<html><body><main><ul>" + "".join(cards) + "</ul></main></body></html>"
    )


@pytest.fixture
async def dom_page():
    """Real chromium page, or skip when no browser is installed."""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(channel="chromium", headless=True)
            page = await browser.new_page()
        except Exception as exc:  # browser binary missing
            pytest.skip(f"chromium unavailable: {exc}")
        try:
            yield page
        finally:
            await browser.close()


class TestSearchPageFullRender:
    async def test_extractor_returns_all_25_ids(self, dom_page):
        await dom_page.set_content(_search_page_html())
        extractor = LinkedInExtractor(dom_page)
        ids = await extractor._extract_job_ids()
        assert len(ids) == TOTAL_ITEMS, (
            f"expected {TOTAL_ITEMS} ids (25 list items with "
            f"data-occludable-job-id), got {len(ids)}: {ids}"
        )
