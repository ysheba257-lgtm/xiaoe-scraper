"""
Video downloader — captures m3u8 URLs from the browser
and downloads via ffmpeg immediately (before signed URLs expire).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright, Page

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "-", name)
    return re.sub(r"\s+", " ", name).strip()


class XiaoeDownloader:
    """Download a list of course videos via CDP + ffmpeg."""

    def __init__(
        self,
        items: list[dict],
        output_dir: str | Path,
        cdp_url: str = "http://localhost:9222",
        concurrency: int = 1,
    ):
        self.items = items
        self.output_dir = Path(output_dir)
        self.cdp_url = cdp_url
        self.concurrency = concurrency

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def download_all(self) -> dict:
        """Download every video.  Returns {success, failed, skipped}."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(self.cdp_url)
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
            pages = ctx.pages
            page = pages[0] if pages else await ctx.new_page()

            # m3u8 capture
            m3u8 = [None]

            def on_request(request):
                if ".m3u8" in request.url:
                    m3u8[0] = request.url

            page.on("request", on_request)

            stats = {"success": 0, "failed": 0, "skipped": 0}

            for i, item in enumerate(self.items):
                rid = item.get("id", "")
                name = item.get("name", f"video_{i + 1}")
                title = sanitize_filename(name)
                fname = f"{i + 1:02d}_{title}.mp4"
                out = self.output_dir / fname

                if out.exists():
                    print(f"[{i + 1}/{len(self.items)}] {name}  (skip — exists)")
                    stats["skipped"] += 1
                    continue

                m3u8[0] = None

                try:
                    url = item.get("video_url") or self._build_url(rid)
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(3)

                    if m3u8[0]:
                        print(f"[{i + 1}/{len(self.items)}] {name}")
                        ok = self._ffmpeg(m3u8[0], out)
                        if ok:
                            stats["success"] += 1
                        else:
                            stats["failed"] += 1
                    else:
                        print(f"[{i + 1}/{len(self.items)}] {name}  (no m3u8)")
                        stats["failed"] += 1
                except Exception as exc:
                    print(f"[{i + 1}/{len(self.items)}] {name}  ERROR: {exc}")
                    stats["failed"] += 1

            print(
                f"\nDone — success: {stats['success']}, "
                f"failed: {stats['failed']}, skipped: {stats['skipped']}"
            )
            return stats

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_url(resource_id: str) -> str:
        # fallback — items from extractor should already carry video_url
        return f"https://appj38rwidh9532.h5.xet.pomoho.com/p/course/video/{resource_id}"

    @staticmethod
    def _ffmpeg(m3u8_url: str, output_path: Path) -> bool:
        cmd = [
            "ffmpeg", "-y",
            "-protocol_whitelist",
            "file,http,https,tcp,tls,crypto,httpproxy",
            "-i", m3u8_url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            str(output_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if result.returncode == 0:
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"  [OK] {size_mb:.1f} MB")
                return True
            err_lines = result.stderr.strip().split("\n")[-3:]
            print(f"  [FAIL] {' | '.join(err_lines)}")
            return False
        except subprocess.TimeoutExpired:
            print("  [FAIL] timeout (>1 h)")
            return False
        except Exception as exc:
            print(f"  [FAIL] {exc}")
            return False
