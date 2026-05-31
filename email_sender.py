"""
Envio de email via Resend (https://resend.com).
- Roda em thread separada (não trava a UI).
- Se RESEND_API_KEY não configurada, NÃO envia mas registra no log.
- Toda tentativa é registrada em email_logs (sucesso ou falha).
- Compatível com a API pública anterior (enviar_email + templates).
"""
import html
import threading
from datetime import datetime

import resend

import config


def _esc(s) -> str:
    """Escapa string para inserção segura em corpo HTML de email."""
    return html.escape(str(s) if s is not None else '', quote=True)


def _esta_configurado() -> bool:
    return bool(getattr(config, 'RESEND_API_KEY', '') and getattr(config, 'EMAIL_FROM', ''))


def _registrar_log(destinatario: str, assunto: str, sucesso: bool, erro: str = ''):
    """Salva no banco. Importa db aqui pra evitar import circular."""
    try:
        from db import cursor
        with cursor() as (conn, cur):
            cur.execute("""
                INSERT INTO email_logs (destinatario, assunto, sucesso, erro, enviado_em)
                VALUES (%s, %s, %s, %s, %s)
            """, (destinatario or '', assunto or '', 1 if sucesso else 0,
                  (erro or '')[:500], datetime.now()))
    except Exception as e:
        print("[email_log] Falha ao registrar:", e)


def _montar_html(corpo_html: str) -> str:
    return """\
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background:#f4f4f4; padding:20px;">
  <div style="max-width:600px; margin:auto; background:white; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
    <div style="background:#1a4d8f; color:white; padding:20px; text-align:center;">
      <h1 style="margin:0;">TRUCKSTAR</h1>
      <p style="margin:4px 0 0; font-size:13px; opacity:0.85;">Mecânica de Caminhões</p>
    </div>
    <div style="padding:25px; color:#333; line-height:1.6;">
      {corpo}
    </div>
    <div style="background:#f0f0f0; padding:15px; text-align:center; font-size:11px; color:#777;">
      Este é um email automático. Não responda.<br>
      Truckstar Mecânica de Caminhões
    </div>
  </div>
</body></html>""".format(corpo=corpo_html)


def _enviar_sincrono(destinatario: str, assunto: str, corpo_html: str) -> tuple:
    """Envia via Resend. Retorna (sucesso: bool, erro: str)."""
    if not destinatario:
        return False, "Destinatário vazio"
    if not _esta_configurado():
        return False, "Resend não configurado (RESEND_API_KEY/EMAIL_FROM em config.py)"

    resend.api_key = config.RESEND_API_KEY
    remetente = "{} <{}>".format(config.EMAIL_REMETENTE_NOME, config.EMAIL_FROM)

    payload = {
        "from": remetente,
        "to": [destinatario],
        "subject": assunto,
        "html": _montar_html(corpo_html),
    }
    reply_to = getattr(config, 'EMAIL_REPLY_TO', '') or ''
    if reply_to:
        payload["reply_to"] = [reply_to]

    try:
        resend.Emails.send(payload)
        return True, ''
    except Exception as e:
        return False, "Erro Resend: " + str(e)


def enviar_email(destinatario: str, assunto: str, corpo_html: str, em_thread: bool = True):
    """
    Envia email via Resend e registra no log.

    Quando em_thread=True (default): dispara em background e retorna None
      imediatamente. A UI nao sabe o resultado.

    Quando em_thread=False: roda sincrono e retorna (sucesso: bool, erro: str).
      Use isso na UI para mostrar mensagens corretas ao usuario (evita o
      problema de mostrar "email enviado" antes do Resend retornar erro).
    """
    def tarefa():
        sucesso, erro = _enviar_sincrono(destinatario, assunto, corpo_html)
        _registrar_log(destinatario, assunto, sucesso, erro)
        if sucesso:
            print("[email] Enviado para", destinatario)
        else:
            print("[email] Falha p/", destinatario, "-", erro)
        return sucesso, erro

    if em_thread:
        threading.Thread(target=tarefa, daemon=True).start()
        return None
    return tarefa()


# ---------- TEMPLATES PRONTOS ----------
def email_os_criada(cliente_nome: str, os_id: int, placa: str, problema: str,
                    funcionario: str) -> tuple:
    """Retorna (assunto, corpo_html)."""
    assunto = "Truckstar - Ordem de Serviço Nº {:06d} criada".format(os_id)
    problema_html = _esc(problema or '---').replace('\n', '<br>')
    corpo = """
    <h2 style="color:#1a4d8f; margin-top:0;">Olá, {nome}!</h2>
    <p>Sua ordem de serviço foi <b>registrada com sucesso</b> em nosso sistema.</p>
    <table style="width:100%; border-collapse:collapse; margin:15px 0;">
      <tr><td style="padding:8px; background:#f0f4f8; border:1px solid #ddd;"><b>Nº da OS:</b></td>
          <td style="padding:8px; border:1px solid #ddd;">{os_id:06d}</td></tr>
      <tr><td style="padding:8px; background:#f0f4f8; border:1px solid #ddd;"><b>Veículo (placa):</b></td>
          <td style="padding:8px; border:1px solid #ddd;">{placa}</td></tr>
      <tr><td style="padding:8px; background:#f0f4f8; border:1px solid #ddd;"><b>Mecânico Responsável:</b></td>
          <td style="padding:8px; border:1px solid #ddd;">{func}</td></tr>
      <tr><td style="padding:8px; background:#f0f4f8; border:1px solid #ddd;"><b>Status:</b></td>
          <td style="padding:8px; border:1px solid #ddd;">Aberta</td></tr>
    </table>
    <p><b>Problema relatado:</b><br>{problema}</p>
    <p>Você pode acompanhar o andamento da sua OS acessando o portal Truckstar com seu CPF.</p>
    <p style="margin-top:20px;">Obrigado pela preferência!<br><b>Equipe Truckstar</b></p>
    """.format(
        nome=_esc(cliente_nome), os_id=os_id, placa=_esc(placa),
        func=_esc(funcionario), problema=problema_html
    )
    return assunto, corpo


def email_os_atualizada(cliente_nome: str, os_id: int, placa: str, status: str,
                        valor_total: float) -> tuple:
    assunto = "Truckstar - OS Nº {:06d} atualizada ({})".format(os_id, status)
    corpo = """
    <h2 style="color:#1a4d8f; margin-top:0;">Olá, {nome}!</h2>
    <p>A ordem de serviço do seu veículo foi atualizada.</p>
    <table style="width:100%; border-collapse:collapse; margin:15px 0;">
      <tr><td style="padding:8px; background:#f0f4f8; border:1px solid #ddd;"><b>Nº da OS:</b></td>
          <td style="padding:8px; border:1px solid #ddd;">{os_id:06d}</td></tr>
      <tr><td style="padding:8px; background:#f0f4f8; border:1px solid #ddd;"><b>Placa:</b></td>
          <td style="padding:8px; border:1px solid #ddd;">{placa}</td></tr>
      <tr><td style="padding:8px; background:#f0f4f8; border:1px solid #ddd;"><b>Novo status:</b></td>
          <td style="padding:8px; border:1px solid #ddd;"><b style="color:#1a4d8f;">{status}</b></td></tr>
      <tr><td style="padding:8px; background:#f0f4f8; border:1px solid #ddd;"><b>Valor total:</b></td>
          <td style="padding:8px; border:1px solid #ddd;">R$ {valor:.2f}</td></tr>
    </table>
    <p style="margin-top:20px;"><b>Equipe Truckstar</b></p>
    """.format(nome=_esc(cliente_nome), os_id=os_id, placa=_esc(placa),
               status=_esc(status), valor=valor_total)
    return assunto, corpo


def email_boas_vindas(cliente_nome: str) -> tuple:
    assunto = "Bem-vindo(a) à Truckstar!"
    corpo = """
    <h2 style="color:#1a4d8f; margin-top:0;">Bem-vindo(a), {nome}!</h2>
    <p>Seu cadastro foi realizado com sucesso na Truckstar.</p>
    <p>A partir de agora, você receberá <b>notificações automáticas por email</b>
    sempre que uma Ordem de Serviço do seu veículo for aberta ou atualizada.</p>
    <p>Para dúvidas ou agendamentos, basta responder este email — nossa equipe
    está à disposição.</p>
    <p style="margin-top:20px;">Obrigado por escolher a Truckstar!<br><b>Equipe Truckstar</b></p>
    """.format(nome=_esc(cliente_nome))
    return assunto, corpo
