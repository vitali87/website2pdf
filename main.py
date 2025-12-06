#!/usr/bin/env python3
import asyncio
import hashlib
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import typer
from bs4 import BeautifulSoup
from pikepdf import Pdf, OutlineItem, Name
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("website_pdfs")


def normalize_url(url: str) -> str:
    p = urlparse(url)._replace(fragment="")
    netloc = p.netloc.lower().removeprefix("www.").removesuffix(":80").removesuffix(":443")
    return urlunparse(p._replace(
        netloc=netloc, path=p.path.rstrip("/"), query=urlencode(sorted(parse_qsl(p.query)))
    )).lower()


async def process_url(url, depth, queue, visited, visited_hashes, browser, base_url,
                       max_depth, exclude_texts, pdf_info, semaphore):
    async with semaphore:
        normalized_url = normalize_url(url)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if content_hash in visited_hashes:
                return
            visited_hashes.add(content_hash)

            sanitized_url = re.sub(r"[^a-zA-Z0-9]", "_", normalized_url)
            page_path = OUTPUT_DIR / f"{sanitized_url}.pdf"
            await page.pdf(path=str(page_path))
            print(f"Saved: {url}")

            soup = BeautifulSoup(content, "html.parser")
            title = (h1.get_text(strip=True) if (h1 := soup.find("h1")) and h1.get_text(strip=True)
                     else await page.title())
            pdf_info.append({"title": title, "file_path": str(page_path), "url": normalized_url})

            if depth < max_depth:
                base_netloc = urlparse(base_url).netloc
                for tag in soup.find_all("a", href=True):
                    next_url = urljoin(base_url, tag["href"])
                    normalized_next = normalize_url(next_url)
                    if (urlparse(normalized_next).netloc == base_netloc and
                        normalized_next not in visited and
                        not any(ex.lower() in tag.get_text(strip=True).lower() for ex in exclude_texts)):
                        visited.add(normalized_next)
                        await queue.put((next_url, depth + 1))
        except Exception as e:
            print(f"Error: {url}: {e}")
        finally:
            await page.close()
            await context.close()


async def worker(queue, active, *args):
    while True:
        try:
            url, depth = await asyncio.wait_for(queue.get(), timeout=1.0)
            active[0] += 1
            await process_url(url, depth, queue, *args)
            active[0] -= 1
            queue.task_done()
        except asyncio.TimeoutError:
            if active[0] == 0 and queue.empty():
                break


async def run(root_url: str, exclude: list, max_depth: int, concurrency: int):
    OUTPUT_DIR.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        visited, visited_hashes, pdf_info, active = set(), set(), [], [0]
        queue, semaphore = asyncio.Queue(), asyncio.Semaphore(concurrency)
        visited.add(normalize_url(root_url))
        await queue.put((root_url, 0))

        workers = [asyncio.create_task(worker(queue, active, visited, visited_hashes, browser,
                   root_url, max_depth, exclude, pdf_info, semaphore)) for _ in range(concurrency)]
        await asyncio.gather(*workers)
        await browser.close()

    if pdf_info:
        pdf_info.sort(key=lambda x: x["url"])
        combine_pdfs_with_outline("final_combined_output.pdf", pdf_info)


def combine_pdfs_with_outline(output_filename: str, pdf_info: list):
    pdf = Pdf.new()
    page_count = 0
    with pdf.open_outline() as outline:
        for info in pdf_info:
            src = Pdf.open(info["file_path"])
            outline.root.append(OutlineItem(info["title"], page_count))
            page_count += len(src.pages)
            pdf.pages.extend(src.pages)
    pdf.Root.PageMode = Name.UseOutlines
    pdf.save(output_filename)
    print(f"Combined PDF saved as {output_filename}")


app = typer.Typer(add_completion=False)


@app.command()
def main(
    root_url: str = typer.Argument(..., help="Root URL"),
    exclude: list[str] = typer.Option([], "-e", "--exclude", help="Exclude links"),
    level: int = typer.Option(1, "-L", "--level", help="Max depth"),
    concurrency: int = typer.Option(50, "-c", "--concurrency", help="Concurrent pages"),
):
    asyncio.run(run(root_url, exclude, level, concurrency))


if __name__ == "__main__":
    app()
