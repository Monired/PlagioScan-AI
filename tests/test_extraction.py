"""
PlagioScan AI — Unit Tests: Text Extraction
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from services.text_extractor import extract_text

def test_extract_txt(tmp_path):
    # Create a temporary txt file
    p = tmp_path / "sample.txt"
    p.write_text("This is a simple text file for testing extraction.", encoding="utf-8")
    
    content = extract_text(str(p), "sample.txt")
    assert "simple text file" in content

def test_extract_unsupported(tmp_path):
    p = tmp_path / "sample.xyz"
    p.write_text("Should not be parsed directly by extension if strict, but let's see fallback", encoding="utf-8")
    content = extract_text(str(p), "sample.xyz")
    assert "Should not be parsed" in content  # assuming it falls back to reading as text

