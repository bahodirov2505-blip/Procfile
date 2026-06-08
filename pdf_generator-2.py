import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# O'zbek harflari uchun font
import subprocess

def get_font():
    """DejaVu fontini topadi yoki o'rnatadi"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('CustomFont', path))
                pdfmetrics.registerFont(TTFont('CustomFont-Bold', path.replace('Sans.ttf', 'Sans-Bold.ttf') if 'Sans.ttf' in path else path))
                return 'CustomFont', 'CustomFont-Bold'
            except:
                pass
    return 'Helvetica', 'Helvetica-Bold'

FONT_NORMAL, FONT_BOLD = get_font()

def clean_text(text):
    """Markdown belgilarini tozalaydi"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text, flags=re.DOTALL)
    return text.strip()

def create_pdf(content: str, filename: str, title: str, doc_type: str) -> str:
    """Matndan chiroyli PDF yaratadi"""
    
    import os as _os
    _home = _os.path.expanduser("~")
    filepath = _os.path.join(_home, filename)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title=title,
        author="Ta'lim Bot"
    )
    
    # Styles
    styles = {
        'title': ParagraphStyle(
            'DocTitle',
            fontName=FONT_BOLD,
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=12,
            spaceBefore=6,
            textColor=colors.HexColor('#1a237e'),
        ),
        'subtitle': ParagraphStyle(
            'Subtitle',
            fontName=FONT_NORMAL,
            fontSize=11,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#5c6bc0'),
        ),
        'heading1': ParagraphStyle(
            'H1',
            fontName=FONT_BOLD,
            fontSize=14,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor('#283593'),
        ),
        'heading2': ParagraphStyle(
            'H2',
            fontName=FONT_BOLD,
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#3949ab'),
        ),
        'body': ParagraphStyle(
            'Body',
            fontName=FONT_NORMAL,
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        'bullet': ParagraphStyle(
            'Bullet',
            fontName=FONT_NORMAL,
            fontSize=11,
            leading=15,
            leftIndent=20,
            spaceAfter=4,
        ),
        'answer': ParagraphStyle(
            'Answer',
            fontName=FONT_BOLD,
            fontSize=11,
            leftIndent=20,
            textColor=colors.HexColor('#1b5e20'),
            spaceAfter=8,
        ),
        'question': ParagraphStyle(
            'Question',
            fontName=FONT_BOLD,
            fontSize=11,
            spaceBefore=10,
            spaceAfter=4,
            textColor=colors.HexColor('#0d47a1'),
        ),
    }
    
    story = []
    
    # Header
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(title, styles['title']))
    story.append(Paragraph(f"Tur: {doc_type} | Ta'lim Bot tomonidan tayyorlandi", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#3949ab')))
    story.append(Spacer(1, 0.5*cm))
    
    # Matnni tahlil qilish va formatlash
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.2*cm))
            continue
        
        clean = clean_text(line)
        if not clean:
            continue
        
        # Sarlavhalar
        if line.startswith('###') or line.startswith('---'):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#c5cae9')))
            continue
        
        # KATTA SARLAVHALAR (emoji bilan yoki raqamli bob)
        if (line.startswith('BOB') or line.startswith('KIRISH') or 
            line.startswith('XULOSA') or line.startswith('MUNDARIJA') or
            re.match(r'^[IVX]+\.', line) or re.match(r'^\d+\s*BOB', line)):
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph(clean, styles['heading1']))
            story.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor('#7986cb')))
            continue
        
        # Emoji bilan sarlavhalar
        if re.match(r'^[🎯📊📝📚✍️🔤❓🃏📰📌📋📄🎙️🎉🎨⬛🔹🔸💡✅❌⏱️1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣]', line):
            if len(clean) < 80:
                story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph(clean, styles['heading2']))
                continue
        
        # Test savollari (A) B) C) D))
        if re.match(r'^[ABCD]\)', line):
            story.append(Paragraph(f"    {clean}", styles['bullet']))
            continue
        
        # To'g'ri javob
        if line.startswith('To\'g\'ri javob:') or line.startswith('✅ To\'g\'ri'):
            story.append(Paragraph(clean, styles['answer']))
            continue
        
        # Savol raqamlari (1. 2. va hokazo)
        if re.match(r'^\d+[\.\-\)]\s', line) or re.match(r'^❓', line):
            story.append(Spacer(1, 0.1*cm))
            story.append(Paragraph(clean, styles['question']))
            continue
        
        # Bullet pointlar
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            story.append(Paragraph(f"  • {clean.lstrip('•-* ')}", styles['bullet']))
            continue
        
        # Oddiy matn
        try:
            story.append(Paragraph(clean, styles['body']))
        except:
            story.append(Paragraph(clean.encode('ascii', 'replace').decode(), styles['body']))
    
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#3949ab')))
    story.append(Paragraph("© Ta'lim Bot — Claude AI yordamida yaratildi", styles['subtitle']))
    
    doc.build(story)
    return filepath

