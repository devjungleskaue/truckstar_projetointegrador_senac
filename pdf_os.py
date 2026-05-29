"""
Gera PDF profissional da Ordem de Serviço.
"""
import html
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from datetime import datetime

import validacoes as v


def _esc_paragraph(texto) -> str:
    """Escapa conteúdo de usuário para uso seguro em Paragraph (ReportLab usa
    markup HTML-like — `<` e `>` em texto cru viram tags inválidas e quebram)."""
    return html.escape(str(texto) if texto is not None else '', quote=True)


def _fmt_data(d):
    if isinstance(d, datetime):
        return d.strftime('%d/%m/%Y %H:%M')
    if d is None or d == '':
        return '---'
    return str(d)


def _endereco_completo(dados: dict) -> str:
    partes = []
    log = dados.get('cliente_logradouro') or ''
    num = dados.get('cliente_numero') or ''
    if log:
        l = log
        if num:
            l += ", " + num
        partes.append(l)
    comp = dados.get('cliente_complemento') or ''
    if comp:
        partes.append(comp)
    bairro = dados.get('cliente_bairro') or ''
    if bairro:
        partes.append(bairro)
    cid = dados.get('cliente_cidade') or ''
    est = dados.get('cliente_estado') or ''
    if cid or est:
        partes.append("{}/{}".format(cid, est).strip('/'))
    cep = dados.get('cliente_cep') or ''
    if cep:
        partes.append("CEP " + v.formatar_cep(cep))
    return " - ".join([p for p in partes if p]) or '---'


def gerar_pdf_os(dados: dict, caminho_arquivo: str) -> str:
    doc = SimpleDocTemplate(
        caminho_arquivo, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle('T', parent=estilos['Heading1'],
                            alignment=1, textColor=colors.HexColor('#1a4d8f'), fontSize=22)
    sub = ParagraphStyle('S', parent=estilos['Normal'],
                         alignment=1, fontSize=10, textColor=colors.grey)
    h3 = ParagraphStyle('H3', parent=estilos['Heading3'],
                        textColor=colors.HexColor('#1a4d8f'), fontSize=11, spaceAfter=4)

    el = []
    el.append(Paragraph("TRUCKSTAR", titulo))
    el.append(Paragraph("Mecânica de Caminhões — Ordem de Serviço", sub))
    el.append(Spacer(1, 0.4*cm))

    # cabeçalho azul
    num = "OS Nº {:06d}".format(int(dados.get('id', 0)))
    cab = Table([[num, "Status: " + str(dados.get('status', ''))]],
                colWidths=[8*cm, 8*cm])
    cab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1a4d8f')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 12),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    el.append(cab)
    el.append(Spacer(1, 0.5*cm))

    # CLIENTE
    el.append(Paragraph("DADOS DO CLIENTE", h3))
    cpf_fmt = v.formatar_cpf_ou_cnpj(dados.get('cliente_cpf') or '')
    cli = [
        ['Nome:', str(dados.get('cliente_nome') or '')],
        ['CPF/CNPJ:', cpf_fmt],
        ['Telefone:', str(dados.get('cliente_telefone') or '')],
        ['Email:', str(dados.get('cliente_email') or '')],
        ['Endereço:', _endereco_completo(dados)],
    ]
    t = Table(cli, colWidths=[3*cm, 13*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#e8eef5')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    el.append(t)
    el.append(Spacer(1, 0.4*cm))

    # VEÍCULO
    el.append(Paragraph("DADOS DO VEÍCULO", h3))
    placa_fmt = v.formatar_placa(dados.get('placa') or '')
    veic = [
        ['Placa:', placa_fmt, 'Marca:', str(dados.get('marca') or '')],
        ['Modelo:', str(dados.get('modelo') or ''), 'Ano:', str(dados.get('ano') or '')],
        ['Cor:', str(dados.get('cor') or ''), 'Chassi:', str(dados.get('chassi') or '')],
    ]
    t = Table(veic, colWidths=[2.5*cm, 5.5*cm, 2.5*cm, 5.5*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#e8eef5')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#e8eef5')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    el.append(t)
    el.append(Spacer(1, 0.4*cm))

    # ATENDIMENTO
    el.append(Paragraph("ATENDIMENTO", h3))
    at = [
        ['Mecânico Responsável:', str(dados.get('funcionario_nome') or '')],
        ['Data de Abertura:', _fmt_data(dados.get('data_abertura'))],
        ['Data de Fechamento:', _fmt_data(dados.get('data_fechamento'))],
    ]
    t = Table(at, colWidths=[4.5*cm, 11.5*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#e8eef5')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    el.append(t)
    el.append(Spacer(1, 0.4*cm))

    # TEXTOS
    def secao_texto(titulo_s, conteudo):
        el.append(Paragraph(titulo_s, h3))
        # Escapa primeiro, depois substitui \n por <br/> (markup ReportLab valido)
        txt = _esc_paragraph(conteudo or '---').replace('\n', '<br/>')
        el.append(Paragraph(txt, estilos['Normal']))
        el.append(Spacer(1, 0.3*cm))

    secao_texto("PROBLEMA RELATADO", dados.get('descricao_problema'))
    secao_texto("SERVIÇOS REALIZADOS", dados.get('servicos_realizados'))
    secao_texto("PEÇAS UTILIZADAS", dados.get('pecas_utilizadas'))

    # VALORES
    v_mo = float(dados.get('valor_mao_obra') or 0)
    v_pc = float(dados.get('valor_pecas') or 0)
    v_tt = float(dados.get('valor_total') or 0)
    val = [
        ['Mão de Obra:', 'R$ {:,.2f}'.format(v_mo).replace(',', 'X').replace('.', ',').replace('X', '.')],
        ['Peças:', 'R$ {:,.2f}'.format(v_pc).replace(',', 'X').replace('.', ',').replace('X', '.')],
        ['TOTAL:', 'R$ {:,.2f}'.format(v_tt).replace(',', 'X').replace('.', ',').replace('X', '.')],
    ]
    t = Table(val, colWidths=[12*cm, 4*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,1), 11),
        ('FONTSIZE', (0,2), (-1,2), 13),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#1a4d8f')),
        ('TEXTCOLOR', (0,2), (-1,2), colors.white),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    el.append(t)
    el.append(Spacer(1, 1.5*cm))

    # ASSINATURAS
    ass = Table([['_'*35, '_'*35],
                 ['Assinatura do Cliente', 'Assinatura do Responsável']],
                colWidths=[8*cm, 8*cm])
    ass.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,1), (-1,1), 4),
    ]))
    el.append(ass)

    el.append(Spacer(1, 0.8*cm))
    el.append(Paragraph(
        "<i>Truckstar Mecânica de Caminhões — Documento gerado em " +
        datetime.now().strftime('%d/%m/%Y às %H:%M') + "</i>", sub))

    doc.build(el)
    return caminho_arquivo
