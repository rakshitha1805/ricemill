import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from typing import Dict, Any

class ReportGenerator:
    """Generates professional executive PDF reports for PRs and Repositories using ReportLab."""

    @staticmethod
    def generate_pr_pdf_report(pr_title: str, repo_name: str, author: str, quality_score: int, security_score: int, arch_score: int, overall_score: int, summary: str, comments: list, output_filepath: str):
        """Builds a PDF report document on disk."""
        doc = SimpleDocTemplate(
            output_filepath,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=10
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=15
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=15,
            spaceAfter=10
        )

        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#334155'),
            leading=14
        )

        story = []

        # Header Title
        story.append(Paragraph("CodeGuard AI - Pull Request Audit Report", title_style))
        story.append(Paragraph(f"Repository: <b>{repo_name}</b> | PR: <b>{pr_title}</b> | Author: {author}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=15))

        # Executive Summary Section
        story.append(Paragraph("Executive Summary", section_heading))
        story.append(Paragraph(summary or "This report provides an automated AI analysis of code quality, security vulnerabilities, and architectural patterns.", body_style))
        story.append(Spacer(1, 15))

        # Scores Table
        story.append(Paragraph("Audit Scores", section_heading))
        score_data = [
            ['Category', 'Score', 'Assessment'],
            ['Overall Health', f"{overall_score} / 100", 'Excellent' if overall_score >= 80 else 'Needs Review'],
            ['Code Quality', f"{quality_score} / 100", 'Good' if quality_score >= 75 else 'Warning'],
            ['Security Risk Score', f"{security_score} / 100", 'Secure' if security_score >= 80 else 'Vulnerabilities Found'],
            ['Architecture Score', f"{arch_score} / 100", 'Solid' if arch_score >= 80 else 'Refactor Recommended']
        ]

        score_table = Table(score_data, colWidths=[180, 120, 200])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 20))

        # Findings Summary Section
        story.append(Paragraph(f"Detailed Findings ({len(comments)} Item(s))", section_heading))

        if not comments:
            story.append(Paragraph("No critical issues or code smells were identified in this review.", body_style))
        else:
            findings_table_data = [['Severity', 'Category', 'File', 'Title']]
            for c in comments[:10]: # Top 10 findings
                sev = c.get('severity', 'Low')
                cat = c.get('category', 'Quality')
                file_p = c.get('file_path', 'N/A')
                title = c.get('title', 'Finding')
                findings_table_data.append([sev, cat, file_p[:25], title[:35]])

            findings_table = Table(findings_table_data, colWidths=[70, 90, 140, 200])
            findings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            story.append(findings_table)

        story.append(Spacer(1, 20))
        story.append(Paragraph("Report generated automatically by <b>CodeGuard AI Platform</b>.", subtitle_style))

        doc.build(story)
        return output_filepath
