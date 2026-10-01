"""
PlagioScan AI — Text Extractor Service
Extracts plain text from PDF, DOCX, TXT, RTF, ODT, Images (OCR), ZIP files.
"""
import os
import re
import zipfile
import tempfile
import logging

logger = logging.getLogger('plagioscan')

# ─── PDF ────────────────────────────────────────────────────────────────────
def _extract_pdf(filepath: str) -> str:
    text = ''
    try:
        import pypdf
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + '\n'
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f'pypdf extraction failed: {e}')

    # Try PyMuPDF as fallback
    if not text.strip():
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text() + '\n'
            doc.close()
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f'PyMuPDF extraction failed: {e}')

    # Scanned PDF → OCR fallback
    if not text.strip():
        text = _ocr_pdf(filepath)

    return text.strip()


def _ocr_pdf(filepath: str) -> str:
    """Convert PDF pages to images and run OCR."""
    text = ''
    try:
        import fitz
        from PIL import Image
        import pytesseract
        import io

        doc = fitz.open(filepath)
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes('png')))
            text += pytesseract.image_to_string(img) + '\n'
        doc.close()
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f'OCR on PDF failed: {e}')
    return text


# ─── DOCX ───────────────────────────────────────────────────────────────────
def _extract_docx(filepath: str) -> str:
    try:
        from docx import Document
        doc = Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        # Also grab table text
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text)
        return '\n'.join(paragraphs)
    except ImportError:
        raise RuntimeError('python-docx is not installed.')
    except Exception as e:
        raise RuntimeError(f'DOCX extraction failed: {e}')


# ─── TXT / RTF / ODT ────────────────────────────────────────────────────────
def _extract_txt(filepath: str) -> str:
    for enc in ('utf-8', 'utf-16', 'latin-1', 'cp1252'):
        try:
            with open(filepath, 'r', encoding=enc, errors='ignore') as f:
                return f.read()
        except Exception:
            continue
    return ''


def _extract_rtf(filepath: str) -> str:
    """Basic RTF strip — remove control words."""
    try:
        text = _extract_txt(filepath)
        text = re.sub(r'\\[a-z]+\d*\s?', ' ', text)
        text = re.sub(r'[{}\\]', '', text)
        return re.sub(r'\s+', ' ', text).strip()
    except Exception:
        return ''


def _extract_image(filepath: str) -> str:
    """OCR on image files."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(filepath)
        return pytesseract.image_to_string(img)
    except ImportError:
        return '[OCR unavailable: install pytesseract + Pillow]'
    except Exception as e:
        return f'[Image OCR failed: {e}]'


# ─── ZIP ────────────────────────────────────────────────────────────────────
def _extract_zip(filepath: str) -> str:
    texts = []
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(filepath, 'r') as zf:
            zf.extractall(tmpdir)
            for root, _, files in os.walk(tmpdir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        t = extract_text(fpath, fname)
                        if t.strip():
                            texts.append(f'--- {fname} ---\n{t}')
                    except Exception:
                        pass
    return '\n\n'.join(texts)


# ─── PUBLIC API ─────────────────────────────────────────────────────────────
def extract_text(filepath: str, filename: str = '') -> str:
    """
    Extract plain text from any supported file.
    Returns clean plain text string.
    """
    fname = (filename or os.path.basename(filepath)).lower()
    ext   = fname.rsplit('.', 1)[-1] if '.' in fname else ''

    extractors = {
        'pdf':  _extract_pdf,
        'docx': _extract_docx,
        'doc':  _extract_docx,
        'txt':  _extract_txt,
        'rtf':  _extract_rtf,
        'odt':  _extract_txt,   # Basic: odt is zip-based but readable as text fallback
        'png':  _extract_image,
        'jpg':  _extract_image,
        'jpeg': _extract_image,
        'zip':  _extract_zip,
    }

    extractor = extractors.get(ext, _extract_txt)
    text = extractor(filepath)
    return _clean_text(text)


def _clean_text(text: str) -> str:
    """Normalize whitespace, remove control chars."""
    if not text:
        return ''
    # Remove null bytes and control characters (except newlines/tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Normalize multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Normalize multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()
