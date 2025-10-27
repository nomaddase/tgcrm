"""Utilities for extracting data from PDF invoices."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


class InvoiceData:
    """Structured invoice information."""

    def __init__(self, total_amount: float, line_items: List[Tuple[int, str]]):
        self.total_amount = total_amount
        self.line_items = line_items


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Return the full text content of a PDF file using PyMuPDF and Tesseract for images."""

    document = fitz.open(pdf_path)
    texts: List[str] = []
    for page in document:
        page_text = page.get_text().strip()
        if page_text:
            texts.append(page_text)
            continue

        # Fallback to OCR when the page has no embedded text.
        pix = page.get_pixmap()
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        texts.append(pytesseract.image_to_string(image))
    return "\n".join(texts)


def parse_invoice(pdf_path: Path) -> InvoiceData:
    """Parse the invoice text and return total amount and line items."""

    text = extract_text_from_pdf(pdf_path)
    total_amount = 0.0
    line_items: List[Tuple[int, str]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("итого") or "total" in line.lower():
            normalized_parts = line.replace(",", ".").split()
            parts = [
                part
                for part in normalized_parts
                if part.replace(".", "").isdigit()
            ]
            if parts:
                total_amount = float(parts[-1])
        elif line[0:1].isdigit():
            try:
                number_str, description = line.split(" ", 1)
                line_number = int("".join(filter(str.isdigit, number_str)))
                if description:
                    line_items.append((line_number, description.strip()))
            except ValueError:
                continue
    return InvoiceData(total_amount=total_amount, line_items=line_items)


__all__ = ["InvoiceData", "parse_invoice", "extract_text_from_pdf"]
