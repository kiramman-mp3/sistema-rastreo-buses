"""Layout helpers for the quality report (reportlab): UTA header, styles, tables, console blocks, figures."""
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph,
                                Preformatted, Spacer, Table, TableStyle)

FONTS = r'C:\Windows\Fonts'
HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_LEFT = os.path.join(HERE, 'recursos', 'logo_16.png')
LOGO_RIGHT = os.path.join(HERE, 'recursos', 'logo_17.png')

for name, file in (('TNR', 'times.ttf'), ('TNR-B', 'timesbd.ttf'), ('TNR-I', 'timesi.ttf'), ('TNR-BI', 'timesbi.ttf'),
                   ('Mono', 'consola.ttf')):
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, file)))
pdfmetrics.registerFontFamily('TNR', normal='TNR', bold='TNR-B', italic='TNR-I', boldItalic='TNR-BI')

BODY = ParagraphStyle('body', fontName='TNR', fontSize=11, leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
BULLET = ParagraphStyle('bullet', parent=BODY, leftIndent=22, bulletIndent=8, spaceAfter=3)
H1 = ParagraphStyle('h1', parent=BODY, fontName='TNR-B', fontSize=12, spaceBefore=10, spaceAfter=6, alignment=TA_LEFT, keepWithNext=1)
H2 = ParagraphStyle('h2', parent=H1, fontSize=11.5, spaceBefore=8, leftIndent=0)
H3 = ParagraphStyle('h3', parent=H1, fontSize=11, spaceBefore=6, spaceAfter=3)
CAPTION = ParagraphStyle('caption', parent=BODY, fontName='TNR-B', fontSize=10, spaceBefore=6, spaceAfter=3, alignment=TA_LEFT, keepWithNext=1)
FIGCAP = ParagraphStyle('figcap', parent=BODY, fontName='TNR', fontSize=10, alignment=TA_LEFT, spaceBefore=2, spaceAfter=8)
CELL = ParagraphStyle('cell', parent=BODY, fontSize=9.5, leading=11.5, alignment=TA_LEFT, spaceAfter=0)
CELLC = ParagraphStyle('cellc', parent=CELL, alignment=TA_CENTER)
CELLB = ParagraphStyle('cellb', parent=CELL, fontName='TNR-B')
CELLBC = ParagraphStyle('cellbc', parent=CELLB, alignment=TA_CENTER)
MONO = ParagraphStyle('mono', fontName='Mono', fontSize=7.2, leading=8.6, textColor=colors.HexColor('#d4d4d4'))
REF = ParagraphStyle('ref', parent=BODY, alignment=TA_LEFT, leftIndent=22, firstLineIndent=-22, fontSize=10.5, leading=13)

PAGE_W, PAGE_H = letter
LEFT = RIGHT = 0.95 * inch
CONTENT_W = PAGE_W - LEFT - RIGHT


def draw_header(canvas, doc):
    canvas.saveState()
    canvas.drawImage(LOGO_LEFT, 60, PAGE_H - 76, 45, 45, mask='auto')
    canvas.drawImage(LOGO_RIGHT, PAGE_W - 105, PAGE_H - 76, 45, 45, mask='auto')
    canvas.setFont('TNR-B', 14)
    canvas.drawCentredString(PAGE_W / 2, PAGE_H - 44, 'UNIVERSIDAD TÉCNICA DE AMBATO')
    canvas.setFont('TNR-B', 9)
    canvas.drawCentredString(PAGE_W / 2, PAGE_H - 56, 'FACULTAD DE INGENIERÍA EN SISTEMAS ELECTRÓNICA E INDUSTRIAL')
    canvas.drawCentredString(PAGE_W / 2, PAGE_H - 66, 'CARRERA DE SOFTWARE')
    canvas.drawCentredString(PAGE_W / 2, PAGE_H - 76, 'CICLO ACADÉMICO: JULIO – DICIEMBRE 2026')
    canvas.setLineWidth(1.6)
    canvas.line(60, PAGE_H - 84, PAGE_W - 60, PAGE_H - 84)
    canvas.setFont('TNR', 9)
    canvas.drawCentredString(PAGE_W / 2, 30, 'Página %d' % doc.page)
    canvas.restoreState()


class Report(BaseDocTemplate):
    def __init__(self, path, title, author):
        super().__init__(path, pagesize=letter, leftMargin=LEFT, rightMargin=RIGHT, topMargin=1.5 * inch,
                         bottomMargin=0.8 * inch, title=title, author=author, subject='Informe técnico de calidad')
        frame = Frame(LEFT, 0.8 * inch, CONTENT_W, PAGE_H - 1.5 * inch - 0.8 * inch, id='main', leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id='uta', frames=[frame], onPage=draw_header)])


class Counter:
    """Numbers the tables and the figures in the order they appear."""
    def __init__(self):
        self.table = 0
        self.image = 0


COUNT = Counter()


def p(text, style=BODY):
    return Paragraph(text, style)


def bullets(items, style=BULLET):
    return [Paragraph(item, style, bulletText='•') for item in items]


def numbered(items, style=BULLET):
    return [Paragraph(item, style, bulletText='%d.' % n) for n, item in enumerate(items, start=1)]


def cell(value, style=CELL):
    if isinstance(value, (Paragraph, Image, Table)) or isinstance(value, list):
        return value
    return Paragraph(str(value), style)


def table(rows, widths, header=True, align_center=(), caption=None, section_rows=(), repeat=1, font_scale=1.0):
    """rows: list of lists of strings (or flowables). widths: fractions of the content width.
    section_rows: row indexes drawn as a full-width bold band (like 'Pruebas funcionales')."""
    if caption:
        COUNT.table += 1
        caption_flow = Paragraph('Tabla %d. %s' % (COUNT.table, caption), CAPTION)
    data = []
    for r, row in enumerate(rows):
        if r in section_rows:
            data.append([cell(row[0], CELLB)] + [''] * (len(widths) - 1))
            continue
        styled = []
        for c, value in enumerate(row):
            bold = header and r == 0
            if c in align_center or (bold and False):
                styled.append(cell(value, CELLBC if bold else CELLC))
            else:
                styled.append(cell(value, CELLB if bold else CELL))
        data.append(styled)
    total = sum(widths)
    t = Table(data, colWidths=[CONTENT_W * w / total for w in widths], repeatRows=repeat if header else 0)
    style = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
             ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
             ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
    if header:
        style.append(('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')))
    for r in section_rows:
        style += [('SPAN', (0, r), (-1, r)), ('BACKGROUND', (0, r), (-1, r), colors.HexColor('#f3f3f3'))]
    t.setStyle(TableStyle(style))
    return ([caption_flow, t] if caption else [t]) + [Spacer(1, 8)]


def console(lines, caption, max_lines_per_row=12):
    """Dark console excerpt (real program output), split by rows so it can cross a page."""
    COUNT.image += 1
    rows = []
    for i in range(0, len(lines), max_lines_per_row):
        chunk = '\n'.join(line.rstrip()[:150] for line in lines[i:i + max_lines_per_row])
        rows.append([Preformatted(chunk, MONO)])
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1e1e1e')),
                           ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                           ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
    return [t, Paragraph('Imagen %d: %s' % (COUNT.image, caption), FIGCAP)]


def figure(path, caption, width=None):
    COUNT.image += 1
    from PIL import Image as PILImage
    with PILImage.open(path) as img:
        ratio = img.height / img.width
    width = width or CONTENT_W * 0.92
    return [KeepTogether([Image(path, width=width, height=width * ratio), Paragraph('Imagen %d: %s' % (COUNT.image, caption), FIGCAP)])]


def fmt(value, digits=4):
    """Spanish decimal comma."""
    return ('%.*f' % (digits, value)).replace('.', ',')


def pct(value, digits=2):
    return fmt(value, digits) + ' %'


def thousands(value):
    return '{:,}'.format(int(value)).replace(',', '.')
