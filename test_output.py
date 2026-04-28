"""
KEEP v2 — Phase 5 Output & Charting Validation Tests
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def test_chart_generator():
    """Verify that the chart generator safely executes code and returns a base64 string."""
    from src.tools.chart_generator import generate_chart_base64
    
    # Simple matplotlib code
    code = '''
import matplotlib.pyplot as plt
plt.plot([1, 2, 3], [4, 5, 6])
plt.title("Test Chart")
plt.savefig(OUTPUT_PATH)
'''
    
    result = generate_chart_base64(code)
    
    assert result is not None, "Chart generation failed"
    assert isinstance(result, str), "Result should be a base64 string"
    assert len(result) > 100, "Base64 string is suspiciously short"
    
    print("✅ Chart Generator: PASSED")


def test_pdf_export():
    """Verify that export_to_pdf generates valid PDF bytes."""
    from src.utils.export import export_to_pdf
    
    markdown_content = """
# Test Report

This is a test report.

### Key Findings
- Finding 1
- Finding 2
"""
    
    pdf_bytes = export_to_pdf(markdown_content)
    
    assert pdf_bytes is not None, "PDF generation failed"
    assert isinstance(pdf_bytes, bytes), "PDF result should be bytes"
    assert pdf_bytes.startswith(b"%PDF"), "Result does not appear to be a valid PDF"
    assert len(pdf_bytes) > 500, "PDF bytes suspiciously short"
    
    print("✅ PDF Export: PASSED")


def test_markdown_export():
    """Verify that export_to_markdown works as expected."""
    from src.utils.export import export_to_markdown
    
    markdown_content = "# Test"
    result = export_to_markdown(markdown_content)
    
    assert result == markdown_content, "Markdown export altered the content"
    
    print("✅ Markdown Export: PASSED")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KEEP v2 — Phase 5: Output & Charting Validation")
    print("=" * 60 + "\n")
    
    test_chart_generator()
    test_markdown_export()
    test_pdf_export()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60 + "\n")
