from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime
def build_pdf(path: str, title: str, lines: list[str], images: list[str] = None):
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 14); c.drawString(2*cm, height-2*cm, title)
    c.setFont("Helvetica", 10); c.drawString(2*cm, height-2.7*cm, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    y = height - 3.5*cm
    for line in lines:
        if y<2*cm: c.showPage(); c.setFont("Helvetica", 10); y = height - 2*cm
        c.drawString(2*cm, y, str(line)[:110]); y -= 0.6*cm
    if images:
        for img in images:
            c.showPage(); c.drawImage(img, 2*cm, 4*cm, width-4*cm, height-8*cm, preserveAspectRatio=True, anchor='c')
    c.save()
