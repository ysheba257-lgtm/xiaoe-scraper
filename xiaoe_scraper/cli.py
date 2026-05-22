"""
CLI entry point for xiaoe-scraper.

Usage:
  python -m xiaoe_scraper extract URL [--password X] [--out items.json]
  python -m xiaoe_scraper download items.json --out ./videos/
  python -m xiaoe_scraper all URL --password X --out ./videos/
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import __version__
from .extractor import XiaoeExtractor
from .downloader import XiaoeDownloader


def main():
    parser = argparse.ArgumentParser(
        description=f"xiaoe-scraper v{__version__} — one-click course video scraper"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- extract ----
    ext = sub.add_parser("extract", help="extract course metadata from a running Chrome")
    ext.add_argument("url", help="course / column page URL")
    ext.add_argument("--password", "-p", default="", help="password to unlock the course")
    ext.add_argument("--cdp", default="http://localhost:9222", help="Chrome CDP endpoint")
    ext.add_argument("--out", "-o", default="items.json", help="output JSON path")

    # ---- download ----
    dl = sub.add_parser("download", help="download videos from an items.json file")
    dl.add_argument("items_json", help="path to items.json")
    dl.add_argument("--out", "-o", default="./videos", help="output directory")
    dl.add_argument("--cdp", default="http://localhost:9222", help="Chrome CDP endpoint")

    # ---- all ----
    al = sub.add_parser("all", help="extract + download in one shot")
    al.add_argument("url", help="course page URL")
    al.add_argument("--password", "-p", default="", help="course password")
    al.add_argument("--out", "-o", default="./videos", help="output directory")
    al.add_argument("--cdp", default="http://localhost:9222", help="Chrome CDP endpoint")

    args = parser.parse_args()

    if args.command == "extract":
        asyncio.run(_cmd_extract(args))
    elif args.command == "download":
        asyncio.run(_cmd_download(args))
    elif args.command == "all":
        asyncio.run(_cmd_all(args))


async def _cmd_extract(args):
    ext = XiaoeExtractor(args.url, password=args.password, cdp_url=args.cdp)
    items = await ext.extract()
    out = Path(args.out)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(items)} items to {out}")


async def _cmd_download(args):
    items = json.loads(Path(args.items_json).read_text(encoding="utf-8"))
    dl = XiaoeDownloader(items, args.out, cdp_url=args.cdp)
    await dl.download_all()


async def _cmd_all(args):
    ext = XiaoeExtractor(args.url, password=args.password, cdp_url=args.cdp)
    items = await ext.extract()
    print(f"\nExtracted {len(items)} courses. Starting download …\n")
    dl = XiaoeDownloader(items, args.out, cdp_url=args.cdp)
    await dl.download_all()


if __name__ == "__main__":
    main()
