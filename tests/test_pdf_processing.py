#!/usr/bin/env python3
import tempfile
import os
import pytest
from pikepdf import Pdf, OutlineItem


class TestPdfProcessing:

    def test_pdf_creation(self):
        pdf = Pdf.new()
        pdf.add_blank_page(page_size=(200, 200))
        assert len(pdf.pages) == 1

    def test_pdf_read_write(self, temp_pdf):
        pdf = Pdf.open(temp_pdf)
        assert len(pdf.pages) > 0

    def test_pdf_combination(self, temp_pdf_pair):
        combined = Pdf.new()
        for path in temp_pdf_pair:
            src = Pdf.open(path)
            combined.pages.extend(src.pages)
        assert len(combined.pages) == 2

    def test_outline_creation(self, temp_pdf_pair):
        combined = Pdf.new()
        page_count = 0

        with combined.open_outline() as outline:
            for i, path in enumerate(temp_pdf_pair):
                src = Pdf.open(path)
                outline.root.append(OutlineItem(f"Section {i+1}", page_count))
                page_count += len(src.pages)
                combined.pages.extend(src.pages)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            combined.save(tmp.name)
            try:
                result = Pdf.open(tmp.name)
                assert len(result.pages) == 2
                with result.open_outline() as outline:
                    assert len(outline.root) == 2
            finally:
                os.unlink(tmp.name)


@pytest.mark.integration
class TestApplicationIntegration:

    def test_import_main_modules(self):
        from pikepdf import Pdf, OutlineItem
        from playwright.async_api import async_playwright
        from bs4 import BeautifulSoup
        import typer

    def test_normalize_url_import(self):
        from main import normalize_url
        assert normalize_url("https://www.example.com/path/") == "https://example.com/path"
        assert normalize_url("https://example.com:443/") == "https://example.com"
        assert normalize_url("https://example.com?b=2&a=1") == "https://example.com?a=1&b=2"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
