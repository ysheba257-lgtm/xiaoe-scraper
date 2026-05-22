"""
Course data extractor — connects to a running Chrome via CDP,
scroll-loads the full course catalog, and extracts video metadata.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class XiaoeExtractor:
    """Extract course metadata from a xiaoe-tech column page."""

    def __init__(
        self,
        course_url: str,
        password: str = "",
        cdp_url: str = "http://localhost:9222",
        headless: bool = False,
    ):
        self.course_url = course_url
        self.password = password
        self.cdp_url = cdp_url
        self.headless = headless

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def extract(self) -> list[dict]:
        """Return a list of dicts with keys: id, title, video_url."""
        async with async_playwright() as pw:
            page = await self._connect(pw)
            await self._navigate_and_unlock(page)
            await self._scroll_to_load_all(page)
            items = await self._get_items_from_vue(page)
            return items

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    async def _connect(self, pw) -> Page:
        if self.headless:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context()
            return await ctx.new_page()

        browser = await pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        pages = ctx.pages
        return pages[0] if pages else await ctx.new_page()

    async def _navigate_and_unlock(self, page: Page) -> None:
        print(f"[extract] loading {self.course_url}")
        await page.goto(self.course_url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

        # --- password dialog ---
        if not self.password:
            return

        # check whether password is needed
        state = await page.evaluate("""
            JSON.stringify((()=>{
                try {
                    let vm = document.getElementById('common_template_mounted_el_container').children[0].__vue__;
                    let g = vm.$store.state.goodsInfo;
                    let p = vm.$store.state.permission;
                    return {pw: g?g.have_password:0, visit: p?p.permission_visit:1};
                } catch(e) { return {error: e.message}; }
            })())
        """)
        try:
            info = json.loads(state)
            need = info.get("pw") == 1 and info.get("visit") == 0
        except Exception:
            need = False

        if not need:
            print("[extract] no password needed")
            return

        print("[extract] entering password …")
        try:
            btn = await page.query_selector("text=输入密码")
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        pw = await page.query_selector("input")
        if pw and await pw.is_visible():
            await pw.fill(self.password)
            await asyncio.sleep(0.5)
            for s in ["button:has-text('确认')", "button:has-text('确定')"]:
                b = await page.query_selector(s)
                if b and await b.is_visible():
                    await b.click()
                    break
            await asyncio.sleep(3)
        print("[extract] password submitted")

    async def _scroll_to_load_all(self, page: Page) -> int:
        """Scroll until no more items load."""
        print("[extract] scrolling to load all courses …")

        # click catalog tab if present
        try:
            tab = await page.query_selector("text=目录")
            if tab:
                await tab.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        prev = 0
        for i in range(15):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)
            cnt = await page.evaluate(
                "document.querySelectorAll('.content-list .list-item').length"
            )
            sys.stdout.write(f"\r  scroll {i+1}: {cnt} items")
            sys.stdout.flush()
            if cnt == prev and cnt > 8 and i >= 3:
                break
            prev = cnt
        print(f"\n[extract] {cnt} courses loaded")
        return cnt

    async def _get_items_from_vue(self, page: Page) -> list[dict]:
        """Read the Vue component's SingleItemList for ids + titles."""
        # resource ids
        ids_raw = await page.evaluate("""
            JSON.stringify((()=>{
                let el = document.querySelector('.content-list .list-item');
                if (!el) return [];
                let p = el.parentElement;
                while (p && !p.__vue__) p = p.parentElement;
                if (!p || !p.__vue__) return [];
                return p.__vue__.SingleItemList.map(i => ({
                    id: i.resource_id || '',
                    name: i.resource_title || ''
                }));
            })())
        """)
        items = json.loads(ids_raw)

        # clean titles via DOM (base64 to avoid encoding issues)
        titles_b64 = await page.evaluate("""
            JSON.stringify(
                Array.from(document.querySelectorAll('.content-list .list-item .content-title'))
                     .map(el => {
                         try { return btoa(unescape(encodeURIComponent(el.textContent.trim()))); }
                         catch(_) { return btoa(el.textContent.trim()); }
                     })
            )
        """)
        import base64
        b64_list = json.loads(titles_b64)
        dom_titles = [base64.b64decode(b).decode("utf-8") for b in b64_list]

        for i, item in enumerate(items):
            if i < len(dom_titles):
                item["name"] = dom_titles[i]
            item["video_url"] = (
                f"https://appj38rwidh9532.h5.xet.pomoho.com/p/course/video/"
                f"{item['id']}?product_id=p_68ea0743e4b0694ca128ea2d"
            )

        return items
