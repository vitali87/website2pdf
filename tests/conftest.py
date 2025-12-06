#!/usr/bin/env python3
import pytest
import tempfile
import os
from pikepdf import Pdf


@pytest.fixture
def temp_pdf():
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        pdf = Pdf.new()
        pdf.add_blank_page(page_size=(200, 200))
        pdf.save(tmp_file.name)
        yield tmp_file.name
        if os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)


@pytest.fixture
def temp_pdf_pair():
    files = []
    for _ in range(2):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf = Pdf.new()
            pdf.add_blank_page(page_size=(200, 200))
            pdf.save(tmp_file.name)
            files.append(tmp_file.name)
    yield files
    for f in files:
        if os.path.exists(f):
            os.unlink(f)
