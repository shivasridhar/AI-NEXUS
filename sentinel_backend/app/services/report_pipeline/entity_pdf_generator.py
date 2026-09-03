import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime
from typing import Dict, Any, List, Optional

class EntityPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
        # Add custom paragraph styles for premium look
        self.title_style = ParagraphStyle(
            'ReportTitle',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6
        )
        
        self.subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=20
        )
        
        self.h1_style = ParagraphStyle(
            'SectionH1',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=15,
            spaceAfter=10,
            keepWithNext=True
        )
        
        self.h2_style = ParagraphStyle(
            'SectionH2',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#4f46e5'),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True
        )

        self.body_style = ParagraphStyle(
            'ReportBody',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            spaceAfter=8
        )
        
        self.body_bold_style = ParagraphStyle(
            'ReportBodyBold',
            parent=self.body_style,
            fontName='Helvetica-Bold'
        )

        self.code_style = ParagraphStyle(
            'ReportCode',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#0f172a'),
            backColor=colors.HexColor('#f1f5f9'),
            borderColor=colors.HexColor('#cbd5e1'),
            borderWidth=0.5,
            borderPadding=6,
            spaceAfter=8
        )
        
        self.meta_label_style = ParagraphStyle(
            'MetaLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#475569')
        )
        
        self.meta_value_style = ParagraphStyle(
            'MetaValue',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#0f172a')
        )

    def _get_severity_color(self, severity: str) -> colors.HexColor:
        sev = severity.upper()
        if sev == "CRITICAL":
            return colors.HexColor('#be123c')  # Deep rose/red
        elif sev == "HIGH":
            return colors.HexColor('#d97706')  # Orange/amber
        elif sev == "MEDIUM":
            return colors.HexColor('#ca8a04')  # Dark yellow
        else:
            return colors.HexColor('#059669')  # Emerald green

    def generate_finding_report(self, finding: Any, identity: Any, evidence: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=36)
        
        story = []
        
        # Header / Title Bar
        story.append(Paragraph("SENTINELAI SECURITY RISK REPORT", self.title_style))
        story.append(Paragraph(f"Exhaustive Analysis of Risk Finding #{str(finding.id)[:8].upper()}", self.subtitle_style))
        
        # Horizontal line
        line_data = [['']]
        line_table = Table(line_data, colWidths=[504], rowHeights=[2])
        line_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#4f46e5')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 15))
        
        # Metadata Card (Table)
        story.append(Paragraph("Finding Information", self.h2_style))
        severity_color = self._get_severity_color(finding.severity)
        
        meta_data = [
            [
                Paragraph("Finding ID:", self.meta_label_style),
                Paragraph(str(finding.id), self.meta_value_style),
                Paragraph("Severity:", self.meta_label_style),
                Paragraph(f"<b><font color='{severity_color.hexval()}'>{finding.severity.upper()}</font></b>", self.meta_value_style)
            ],
            [
                Paragraph("Type:", self.meta_label_style),
                Paragraph(finding.finding_type, self.meta_value_style),
                Paragraph("Detected:", self.meta_label_style),
                Paragraph(finding.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if finding.created_at else 'N/A', self.meta_value_style)
            ],
            [
                Paragraph("Target ARN:", self.meta_label_style),
                Paragraph(identity.arn if identity else 'N/A', self.meta_value_style),
                Paragraph("Account ID:", self.meta_label_style),
                Paragraph(identity.account_id if identity else 'N/A', self.meta_value_style)
            ]
        ]
        
        meta_table = Table(meta_data, colWidths=[80, 172, 80, 172])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor('#e2e8f0')),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))
        
        # Description
        story.append(Paragraph("Description", self.h2_style))
        story.append(Paragraph(finding.description or "No description provided.", self.body_style))
        story.append(Spacer(1, 10))
        
        # Event Reference
        if finding.event_reference:
            story.append(Paragraph("Event Reference / Evidence ID", self.h2_style))
            story.append(Paragraph(finding.event_reference, self.code_style))
            story.append(Spacer(1, 10))
            
        # Explainability & AI analysis
        story.append(Paragraph("AI Analysis & Business Impact", self.h1_style))
        explainability_text = evidence.get("explainability", "AI explanation is not available.")
        # Replace newlines with <br/> for ReportLab Paragraph compatibility
        formatted_explainability = explainability_text.replace('\n', '<br/>')
        story.append(Paragraph(formatted_explainability, self.body_style))
        story.append(Spacer(1, 15))
        
        # Graph Metrics & Attack Path Summary
        metrics = evidence.get("graph_metrics", {})
        if metrics:
            story.append(Paragraph("Graph Analytics & Reachability", self.h1_style))
            metrics_data = [
                [
                    Paragraph("Shortest Path Hops", self.meta_label_style),
                    Paragraph("Reachable Critical Assets", self.meta_label_style),
                    Paragraph("Active Threat Cycles", self.meta_label_style),
                    Paragraph("Connected Entities", self.meta_label_style)
                ],
                [
                    Paragraph(str(metrics.get('shortest_path_hops', 'N/A')), self.body_style),
                    Paragraph(str(metrics.get('reachable_critical_assets', 0)), self.body_style),
                    Paragraph("Yes" if metrics.get('cycle_detected') else "No", self.body_style),
                    Paragraph(str(metrics.get('connected_components', 0)), self.body_style)
                ]
            ]
            metrics_table = Table(metrics_data, colWidths=[126, 126, 126, 126])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor('#cbd5e1')),
            ]))
            story.append(metrics_table)
            story.append(Spacer(1, 15))

        # Risk Factors
        risk_factors = evidence.get("risk_factors", [])
        if risk_factors:
            story.append(Paragraph("Risk Factors Evaluated", self.h1_style))
            factors_table_data = [[
                Paragraph("<b>Factor</b>", self.meta_label_style),
                Paragraph("<b>Details / Description</b>", self.meta_label_style)
            ]]
            for rf in risk_factors:
                factors_table_data.append([
                    Paragraph(rf.get('factor', 'Risk Heuristic'), self.body_bold_style),
                    Paragraph(rf.get('description', 'Condition observed'), self.body_style)
                ])
            factors_table = Table(factors_table_data, colWidths=[150, 354])
            factors_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor('#e2e8f0')),
            ]))
            story.append(factors_table)
            story.append(Spacer(1, 15))
            
        doc.build(story)
        return buffer.getvalue()

    def generate_identity_report(self, identity: Any, findings: List[Any], risk_score: Optional[int], risk_severity: str, attack_path: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=36)
        
        story = []
        
        # Header / Title Bar
        story.append(Paragraph("SENTINELAI IDENTITY PROFILE REPORT", self.title_style))
        story.append(Paragraph(f"Security Analysis of Machine Identity Profile", self.subtitle_style))
        
        # Horizontal line
        line_data = [['']]
        line_table = Table(line_data, colWidths=[504], rowHeights=[2])
        line_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#4f46e5')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 15))
        
        # Metadata Card (Table)
        story.append(Paragraph("Identity Properties", self.h2_style))
        severity_color = self._get_severity_color(risk_severity or "LOW")
        score = risk_score if risk_score is not None else 0
        
        meta_data = [
            [
                Paragraph("Identity ID:", self.meta_label_style),
                Paragraph(str(identity.id), self.meta_value_style),
                Paragraph("Risk Score:", self.meta_label_style),
                Paragraph(f"<b><font color='{severity_color.hexval()}'>{score} / 100 ({risk_severity.upper()})</font></b>", self.meta_value_style)
            ],
            [
                Paragraph("Type:", self.meta_label_style),
                Paragraph(identity.identity_type, self.meta_value_style),
                Paragraph("Total Events:", self.meta_label_style),
                Paragraph(str(identity.total_events or 0), self.meta_value_style)
            ],
            [
                Paragraph("ARN:", self.meta_label_style),
                Paragraph(identity.arn, self.meta_value_style),
                Paragraph("Account ID:", self.meta_label_style),
                Paragraph(identity.account_id, self.meta_value_style)
            ]
        ]
        
        meta_table = Table(meta_data, colWidths=[80, 172, 80, 172])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor('#e2e8f0')),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))
        
        # Risk Findings
        story.append(Paragraph("Associated Risk Findings", self.h1_style))
        if findings:
            findings_table_data = [[
                Paragraph("<b>Severity</b>", self.meta_label_style),
                Paragraph("<b>Finding Type / Description</b>", self.meta_label_style),
                Paragraph("<b>Detected</b>", self.meta_label_style)
            ]]
            for f in findings:
                f_color = self._get_severity_color(f.severity)
                findings_table_data.append([
                    Paragraph(f"<b><font color='{f_color.hexval()}'>{f.severity.upper()}</font></b>", self.meta_label_style),
                    Paragraph(f"<b>{f.finding_type}</b><br/>{f.description}", self.body_style),
                    Paragraph(f.created_at.strftime('%Y-%m-%d') if f.created_at else 'N/A', self.body_style)
                ])
            findings_table = Table(findings_table_data, colWidths=[80, 344, 80])
            findings_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor('#e2e8f0')),
            ]))
            story.append(findings_table)
        else:
            story.append(Paragraph("No active security findings discovered for this identity profile.", self.body_style))
        story.append(Spacer(1, 15))
        
        # Attack Path Context
        nodes = attack_path.get("nodes", [])
        edges = attack_path.get("edges", [])
        if nodes:
            story.append(Paragraph("Attack Path & Relationship Context", self.h1_style))
            story.append(Paragraph(f"This identity has <b>{len(nodes)}</b> connected nodes and <b>{len(edges)}</b> logical relationships in the active Threat Graph projection.", self.body_style))
            
            # Print a summary list of path nodes
            path_items = []
            for node in nodes:
                node_data = node.get("data", {})
                label = node_data.get("label", "Node")
                name = node_data.get("name", "")
                path_items.append(f"- <b>{label}</b>: {name}")
            
            formatted_nodes_list = "<br/>".join(path_items)
            story.append(Paragraph(formatted_nodes_list, self.body_style))
            story.append(Spacer(1, 15))
            
        doc.build(story)
        return buffer.getvalue()
