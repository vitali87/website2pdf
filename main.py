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


async def crawl_and_save_pdf(url, visited, visited_hashes, browser, base_url,
                              depth, max_depth, exclude_texts, pdf_info):
    normalized_url = normalize_url(url)
    if normalized_url in visited or depth > max_depth:
        return
    visited.add(normalized_url)

    context = await browser.new_context()
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="networkidle")
        content = await page.content()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        if content_hash in visited_hashes:
            print(f"Duplicate content found at {url}, skipping.")
            return
        visited_hashes.add(content_hash)

        sanitized_url = re.sub(r"[^a-zA-Z0-9]", "_", normalized_url)
        page_path = OUTPUT_DIR / f"{sanitized_url}.pdf"
        await page.pdf(path=str(page_path))
        print(f"Saved: {url} to {page_path}")

        soup = BeautifulSoup(content, "html.parser")
        title = (h1.get_text(strip=True) if (h1 := soup.find("h1")) and h1.get_text(strip=True)
                 else await page.title())
        pdf_info.append({"title": title, "file_path": str(page_path)})

        base_netloc = urlparse(base_url).netloc
        for link_tag in soup.find_all("a", href=True):
            link_text = link_tag.get_text(strip=True)
            next_url = urljoin(base_url, link_tag["href"])
            normalized_next = normalize_url(next_url)

            if (any(ex.lower() in link_text.lower() for ex in exclude_texts) or
                urlparse(normalized_next).netloc != base_netloc or
                normalized_next in visited):
                continue

            await crawl_and_save_pdf(next_url, visited, visited_hashes, browser,
                                      base_url, depth + 1, max_depth, exclude_texts, pdf_info)
    except Exception as e:
        print(f"Error visiting {url}: {e}")
    finally:
        await page.close()
        await context.close()


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
    print(f"Combined PDF with outline saved as {output_filename}")


async def run(root_url: str, exclude: list, max_depth: int):
    OUTPUT_DIR.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        visited, visited_hashes, pdf_info = set(), set(), []
        await crawl_and_save_pdf(root_url, visited, visited_hashes, browser,
                                  root_url, 0, max_depth, exclude, pdf_info)
        await browser.close()
    if pdf_info:
        combine_pdfs_with_outline("final_combined_output.pdf", pdf_info)


app = typer.Typer()


@app.command()
def main(
    root_url: str = typer.Argument(..., help="The root URL to start crawling from"),
    exclude: list[str] = typer.Option([], "-e", "--exclude", help="Link texts to exclude"),
    level: int = typer.Option(0, "-L", "--level", help="Max depth of the crawl (0 = root only)"),
):
    asyncio.run(run(root_url, exclude or [], level))


if __name__ == "__main__":
    app()
