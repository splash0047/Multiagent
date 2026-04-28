"""
KEEP v2 — Report Export Utilities

Functions to export the generated research report (Markdown) 
to standalone Markdown and PDF files.
"""

import os
import markdown
import tempfile
from fpdf import FPDF
from bs4 import BeautifulSoup
from typing import Optional

def export_to_markdown(report_content: str) -> str:
    """
    Simply returns the Markdown string. Can be extended to 
    add frontmatter or inject external resources if needed.
    """
    return report_content

def export_to_pdf(report_content: str) -> Optional[bytes]:
    """
    Converts Markdown to PDF and returns it as a byte string.
    We convert Markdown to HTML, then parse the HTML to write to FPDF.
    For simplicity in this MVP, we use a basic FPDF implementation.
    """
    try:
        # Convert Markdown to HTML
        html_content = markdown.markdown(report_content)
        
        # Parse HTML to text (very basic approach for MVP)
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text()
        
        pdf = FPDF()
        pdf.add_page()
        
        # We need a font that supports unicode if possible, but FPDF default is latin-1.
        # For MVP, we will just encode to latin-1 and ignore errors to prevent crashing.
        pdf.set_font("Arial", size=12)
        
        # Add a title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="Research Report", ln=1, align='C')
        pdf.ln(10)
        
        # Add body
        pdf.set_font("Arial", size=12)
        for line in text_content.split('\n'):
            line = line.strip()
            if line:
                # Encode and decode to drop unsupported characters
                safe_line = line.encode('latin-1', 'replace').decode('latin-1')
                try:
                    pdf.multi_cell(w=0, h=6, text=safe_line)
                except Exception:
                    pass
                pdf.ln(2)
                
        return bytes(pdf.output())
    except Exception as e:
        print(f"Error exporting to PDF: {e}")
        return None
