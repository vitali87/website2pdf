# Web-to-PDF Crawler

Crawl websites and save them as a single PDF with clickable table of contents.

## Installation

```bash
uv sync
playwright install chromium
```

## Usage

```bash
wtp <url> [options]
```

### Options

- `-e, --exclude`: Link texts to exclude (repeatable)
- `-L, --level`: Max crawl depth (default: 0 = root only)

### Examples

```bash
wtp https://example.com
wtp https://example.com -L 2 -e "Privacy" -e "Terms"
```

## Output

- Individual PDFs: `website_pdfs/`
- Combined PDF: `final_combined_output.pdf`

## License

MIT
