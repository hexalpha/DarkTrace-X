from io import BytesIO

from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.domain.schemas import ReportRequest
from app.services.intelligence import intelligence_service


class ReportService:
    """Creates portable exports from tenant-scoped evidence, never raw connector secrets."""

    def render(self, tenant_id: str, format_name: str, request: ReportRequest) -> tuple[str, str, bytes]:
        if format_name == "pdf":
            return "application/pdf", "darktracex-brief.pdf", self._pdf(tenant_id, request)
        if format_name == "docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "darktracex-brief.docx", self._docx(tenant_id, request)
        if format_name == "xlsx":
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "darktracex-brief.xlsx", self._xlsx(tenant_id, request)
        raise ValueError("Unsupported report format")

    def _rows(self, tenant_id: str) -> list[list[str]]:
        return [[alert.severity.value.upper(), str(alert.score), alert.status, alert.title] for alert in intelligence_service.list_alerts(tenant_id)]

    def _pdf(self, tenant_id: str, request: ReportRequest) -> bytes:
        buffer = BytesIO()
        styles = getSampleStyleSheet()
        document = SimpleDocTemplate(buffer, pagesize=letter, title=request.title, author="DarkTrace X")
        story = [Paragraph(request.title, styles["Title"]), Spacer(1, 12), Paragraph("Defensive intelligence summary — generated from tenant-scoped records.", styles["BodyText"])]
        if request.include_alerts:
            table = Table([["SEVERITY", "SCORE", "STATUS", "ALERT"], *self._rows(tenant_id)], colWidths=[72, 48, 84, 300])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10233D")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#C6D4E5")), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story += [Spacer(1, 16), Paragraph("Priority alerts", styles["Heading2"]), table]
        document.build(story)
        return buffer.getvalue()

    def _docx(self, tenant_id: str, request: ReportRequest) -> bytes:
        document = Document()
        document.core_properties.title = request.title
        document.add_heading(request.title, 0)
        document.add_paragraph("Defensive intelligence summary — tenant-scoped export.")
        if request.include_alerts:
            document.add_heading("Priority alerts", level=1)
            table = document.add_table(rows=1, cols=4)
            table.style = "Light Shading Accent 1"
            for cell, heading in zip(table.rows[0].cells, ["Severity", "Score", "Status", "Alert"]):
                cell.text = heading
            for row in self._rows(tenant_id):
                cells = table.add_row().cells
                for cell, value in zip(cells, row):
                    cell.text = value
        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    def _xlsx(self, tenant_id: str, request: ReportRequest) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Priority alerts"
        sheet.append([request.title])
        sheet.append(["Severity", "Score", "Status", "Alert"])
        for row in self._rows(tenant_id):
            sheet.append(row)
        for cell in sheet[2]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="10233D")
        sheet.freeze_panes = "A3"
        sheet.column_dimensions["A"].width = 14
        sheet.column_dimensions["B"].width = 10
        sheet.column_dimensions["C"].width = 18
        sheet.column_dimensions["D"].width = 64
        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()


report_service = ReportService()

