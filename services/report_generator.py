"""
PlagioScan AI — PDF Report Generator
Generates professional PDF reports using ReportLab.
"""
import io
import os
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics import renderPDF
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


# ─── Brand Colors ─────────────────────────────────────────────────────────────
BRAND_PURPLE = colors.HexColor('#6c63ff')
BRAND_TEAL   = colors.HexColor('#00c9a7')
BRAND_DARK   = colors.HexColor('#0d0f1a')
BRAND_CARD   = colors.HexColor('#151827')
DANGER       = colors.HexColor('#e84393')
WARNING_C    = colors.HexColor('#f9ca24')
SUCCESS_C    = colors.HexColor('#00c9a7')
LIGHT_BG     = colors.HexColor('#f0f2ff')
GRAY         = colors.HexColor('#7986cb')
WHITE        = colors.white
BLACK        = colors.black


def _score_color(score: float, invert: bool = False):
    """Return a ReportLab color based on score."""
    if invert:
        if score < 20:   return SUCCESS_C
        if score < 50:   return WARNING_C
        return DANGER
    if score >= 75:      return SUCCESS_C
    if score >= 50:      return WARNING_C
    return DANGER


def _grade_color(grade: str):
    return {
        'A': SUCCESS_C, 'B': SUCCESS_C, 'C': WARNING_C,
        'D': DANGER, 'F': DANGER
    }.get(grade, GRAY)


def _make_qr_image(url: str, size: int = 120):
    """Generate a QR code image flowable for ReportLab."""
    try:
        import qrcode
        from reportlab.platypus import Image as RLImage
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return RLImage(buf, width=size, height=size)
    except Exception:
        return None


def generate_pdf_report(analysis_data: Dict[str, Any],
                         username: str,
                         doc_name: str,
                         overall_score: float,
                         grade: str,
                         doc_hash: str = '',
                         results_url: str = '') -> bytes:
    """
    Generate a professional PDF report. Returns raw PDF bytes.
    """
    if not REPORTLAB_OK:
        raise RuntimeError('reportlab is not installed. Run: pip install reportlab')

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f'PlagioScan AI Report — {doc_name}',
        author='PlagioScan AI',
        subject='Plagiarism & Originality Analysis Report',
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Normal'],
        fontSize=22, textColor=BRAND_PURPLE, fontName='Helvetica-Bold',
        spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
        fontSize=11, textColor=GRAY, alignment=TA_CENTER, spaceAfter=2)
    section_style = ParagraphStyle('Section', parent=styles['Normal'],
        fontSize=13, textColor=BRAND_PURPLE, fontName='Helvetica-Bold',
        spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
        fontSize=9, textColor=BLACK, leading=14, alignment=TA_JUSTIFY)
    small_style = ParagraphStyle('Small', parent=styles['Normal'],
        fontSize=8, textColor=GRAY, leading=12)
    warn_style = ParagraphStyle('Warn', parent=styles['Normal'],
        fontSize=9, textColor=DANGER, leading=14)
    success_style = ParagraphStyle('Success', parent=styles['Normal'],
        fontSize=9, textColor=SUCCESS_C, leading=14)

    elements = []
    now = datetime.now().strftime('%d %B %Y, %H:%M')

    # ── Header / Title ───────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph('🛡 PlagioScan AI', title_style))
    elements.append(Paragraph('Intelligent Plagiarism Detection & Originality Analysis Platform', subtitle_style))
    elements.append(HRFlowable(width='100%', thickness=2, color=BRAND_PURPLE, spaceAfter=10))

    # ── Meta Table ───────────────────────────────────────────────────────────
    meta = [
        ['Document', doc_name,          'Analyzed By', username],
        ['Date',     now,               'Report ID',   f'PSA-{abs(hash(doc_name))%100000:05d}'],
        ['Grade',    grade,             'Overall Score', f'{overall_score:.1f}/100'],
    ]
    meta_table = Table(meta, colWidths=[3*cm, 6.5*cm, 3.5*cm, 4*cm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE',    (0,0), (-1,-1), 8),
        ('FONTNAME',    (0,0), (0,-1),  'Helvetica-Bold'),
        ('FONTNAME',    (2,0), (2,-1),  'Helvetica-Bold'),
        ('TEXTCOLOR',   (0,0), (0,-1),  BRAND_PURPLE),
        ('TEXTCOLOR',   (2,0), (2,-1),  BRAND_PURPLE),
        ('BACKGROUND',  (0,0), (-1,-1), LIGHT_BG),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [LIGHT_BG, WHITE]),
        ('GRID',        (0,0), (-1,-1), 0.3, GRAY),
        ('PADDING',     (0,0), (-1,-1), 5),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.4*cm))

    # ── Score Summary Table ───────────────────────────────────────────────────
    elements.append(Paragraph('📊 Analysis Score Summary', section_style))

    plag  = analysis_data.get('plagiarism_score', 0)
    orig  = analysis_data.get('originality_score', 100)
    wq    = analysis_data.get('writing_quality_score', 0)
    rd    = analysis_data.get('research_depth_score', 0)
    cont  = analysis_data.get('contribution_score', 0)
    read  = analysis_data.get('readability_score', 0)
    vocab = analysis_data.get('vocabulary_score', 0)
    acad  = analysis_data.get('academic_score', 0)

    score_rows = [
        ['Metric', 'Score', 'Status'],
        ['Plagiarism Detected',   f'{plag:.1f}%',   'HIGH RISK' if plag>50 else 'MODERATE' if plag>20 else 'CLEAR'],
        ['Originality Score',     f'{orig:.1f}/100', 'EXCELLENT' if orig>75 else 'GOOD' if orig>50 else 'POOR'],
        ['Writing Quality',       f'{wq:.1f}/100',   'EXCELLENT' if wq>75 else 'GOOD' if wq>50 else 'NEEDS WORK'],
        ['Research Depth',        f'{rd:.1f}/100',   'STRONG' if rd>65 else 'MODERATE' if rd>35 else 'WEAK'],
        ['Contribution Score',    f'{cont:.1f}/100', 'HIGH' if cont>65 else 'MODERATE' if cont>35 else 'LOW'],
        ['Readability',           f'{read:.1f}/100', 'GOOD' if read>60 else 'AVERAGE' if read>40 else 'COMPLEX'],
        ['Vocabulary Score',      f'{vocab:.1f}/100','RICH' if vocab>70 else 'AVERAGE' if vocab>40 else 'LIMITED'],
        ['Academic Score',        f'{acad:.1f}/100', 'EXCELLENT' if acad>75 else 'GOOD' if acad>50 else 'BELOW PAR'],
    ]

    def _status_color(val: str):
        pos = {'EXCELLENT','CLEAR','STRONG','HIGH','RICH','GOOD'}
        neg = {'HIGH RISK','POOR','WEAK','LOW','LIMITED','BELOW PAR','NEEDS WORK','COMPLEX'}
        if val in pos: return SUCCESS_C
        if val in neg: return DANGER
        return WARNING_C

    score_table = Table(score_rows, colWidths=[7*cm, 4*cm, 6*cm])
    style_cmds  = [
        ('FONTNAME',   (0,0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1),  9),
        ('BACKGROUND', (0,0), (-1, 0),  BRAND_PURPLE),
        ('TEXTCOLOR',  (0,0), (-1, 0),  WHITE),
        ('GRID',       (0,0), (-1,-1),  0.3, GRAY),
        ('PADDING',    (0,0), (-1,-1),  5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
    ]
    for r_idx, row in enumerate(score_rows[1:], start=1):
        status = row[2]
        c = _status_color(status)
        style_cmds.append(('TEXTCOLOR', (2, r_idx), (2, r_idx), c))
        style_cmds.append(('FONTNAME',  (2, r_idx), (2, r_idx), 'Helvetica-Bold'))
    score_table.setStyle(TableStyle(style_cmds))
    elements.append(score_table)
    elements.append(Spacer(1, 0.4*cm))

    # ── Algorithm Breakdown ───────────────────────────────────────────────────
    sim = analysis_data.get('similarity_breakdown', {})
    if any(sim.values()):
        elements.append(Paragraph('🔬 Similarity Algorithm Breakdown', section_style))
        alg_rows = [['Algorithm', 'Score', 'Weight'],
                    ['TF-IDF + Cosine Similarity', f"{sim.get('tfidf', 0):.1f}%",   '40%'],
                    ['N-Gram Similarity',           f"{sim.get('ngram', 0):.1f}%",   '20%'],
                    ['Jaccard Similarity',          f"{sim.get('jaccard', 0):.1f}%", '15%'],
                    ['Fuzzy String Matching',       f"{sim.get('fuzzy', 0):.1f}%",   '25%'],
                    ['Combined (Weighted)',         f"{sim.get('combined', 0):.1f}%", '—']]
        alg_table = Table(alg_rows, colWidths=[8*cm, 4*cm, 5*cm])
        alg_table.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1),  9),
            ('BACKGROUND', (0,0), (-1, 0),  BRAND_DARK),
            ('TEXTCOLOR',  (0,0), (-1, 0),  WHITE),
            ('GRID',       (0,0), (-1,-1),  0.3, GRAY),
            ('PADDING',    (0,0), (-1,-1),  5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
            ('FONTNAME',   (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR',  (1,-1), (1,-1),
             DANGER if sim.get('combined', 0) > 50 else
             WARNING_C if sim.get('combined', 0) > 20 else SUCCESS_C),
        ]))
        elements.append(alg_table)
        elements.append(Spacer(1, 0.4*cm))

    # ── Web Matches ───────────────────────────────────────────────────────────
    web_matches = analysis_data.get('web_matches', [])
    if web_matches:
        elements.append(Paragraph(f'🌐 Internet Matches Found ({len(web_matches)})', section_style))
        for i, m in enumerate(web_matches[:8], 1):
            sim_c = _score_color(m.get('similarity', 0), invert=True)
            elements.append(KeepTogether([
                Paragraph(
                    f'<b>{i}. {m.get("source","Unknown Source")}</b>  '
                    f'<font color="#{sim_c.hexval()[2:]}">Similarity: {m.get("similarity",0):.1f}%</font>',
                    body_style),
                Paragraph(f'URL: {m.get("url","")}', small_style),
                Paragraph(f'Matched sentence: <i>"{m.get("matched_sentence","")[:150]}"</i>', small_style),
                Spacer(1, 0.2*cm),
            ]))
    else:
        elements.append(Paragraph('🌐 Internet Plagiarism Check', section_style))
        elements.append(Paragraph('✅ No significant web matches found.', success_style))
    elements.append(Spacer(1, 0.3*cm))

    # ── Style Analysis ────────────────────────────────────────────────────────
    style_d = analysis_data.get('style_analysis', {})
    if style_d:
        elements.append(Paragraph('✍️ Writing Style Analysis', section_style))
        style_rows = [
            ['Metric', 'Value'],
            ['Total Words',            str(style_d.get('word_count', '—'))],
            ['Total Sentences',        str(style_d.get('sentence_count', '—'))],
            ['Paragraphs',             str(style_d.get('paragraph_count', '—'))],
            ['Avg Sentence Length',    f"{style_d.get('avg_sentence_length',0):.1f} words"],
            ['Vocabulary Richness',    f"{style_d.get('vocabulary_richness',0):.1f}%"],
            ['Flesch Reading Ease',    f"{style_d.get('reading_ease',0):.1f}/100"],
            ['FK Grade Level',         f"Grade {style_d.get('fk_grade',0):.1f}"],
            ['Passive Voice',          f"{style_d.get('passive_voice_pct',0):.1f}%"],
            ['Writing Tone',           style_d.get('tone', {}).get('tone', '—')],
        ]
        sty_table = Table(style_rows, colWidths=[9*cm, 8*cm])
        sty_table.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('BACKGROUND', (0,0), (-1, 0), BRAND_TEAL),
            ('TEXTCOLOR',  (0,0), (-1, 0), WHITE),
            ('GRID',       (0,0), (-1,-1), 0.3, GRAY),
            ('PADDING',    (0,0), (-1,-1), 5),
            ('FONTNAME',   (0,1), (0,-1), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
        ]))
        elements.append(sty_table)
        elements.append(Spacer(1, 0.4*cm))

    # ── Improvement Suggestions ───────────────────────────────────────────────
    suggestions = analysis_data.get('improvement_suggestions', [])
    if suggestions:
        elements.append(Paragraph('💡 Recommendations for Improvement', section_style))
        for sugg in suggestions:
            elements.append(Paragraph(f'• {sugg}', body_style))
            elements.append(Spacer(1, 0.15*cm))
        elements.append(Spacer(1, 0.2*cm))

    # ── Footer note ───────────────────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=1, color=BRAND_PURPLE, spaceBefore=10))
    elements.append(Paragraph(
        f'<i>Generated by PlagioScan AI • {now} • '
        'This report is for academic integrity guidance only. '
        'Results are based on algorithmic analysis and may not be 100% accurate.</i>',
        small_style
    ))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    def _watermark(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 60)
        canvas.setFillColorRGB(0.42, 0.39, 1.0, alpha=0.06)
        canvas.translate(A4[0]/2, A4[1]/2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, 'PlagioScan AI')
        # Page number
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(GRAY)
        canvas.setFillColorRGB(0.47, 0.53, 0.80)
        canvas.drawRightString(A4[0] - 2*cm, 1.2*cm,
                               f'Page {doc.page}')
        canvas.restoreState()

    doc.build(elements, onFirstPage=_watermark, onLaterPages=_watermark)
    return buf.getvalue()
