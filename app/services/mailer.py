# app/services/mailer.py
"""
Serviço de envio de e-mails para verificação.

Suporta dois modos:
1. SMTP direto (desenvolvimento/local ou produção com servidor SMTP próprio)
2. Resend API (recomendado para produção no Render/Vercel)

Configure as variáveis de ambiente conforme o modo escolhido.
"""
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

# Configurações SMTP (modo tradicional)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Configurações Resend API (recomendado para produção)
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")  # ex: "noreply@seudominio.com"

# URL base da aplicação
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")


def _send_via_resend(to_email: str, subject: str, body: str) -> None:
    """Envia e-mail usando Resend API (recomendado para produção)."""
    try:
        import httpx
    except ImportError:
        raise RuntimeError(
            "Para usar Resend API, instale: pip install httpx"
        )

    if not RESEND_API_KEY or not RESEND_FROM_EMAIL:
        raise RuntimeError(
            "Resend não configurado. Configure RESEND_API_KEY e RESEND_FROM_EMAIL."
        )

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "text": body,
        },
        timeout=10.0,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Erro ao enviar e-mail via Resend: {response.text}")


def _send_via_smtp(to_email: str, subject: str, body: str) -> None:
    """Envia e-mail usando SMTP direto."""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_FROM]):
        raise RuntimeError(
            "SMTP não configurado. Configure SMTP_HOST, SMTP_USER, SMTP_PASS e SMTP_FROM."
        )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())


def send_verification_email(to_email: str, token: str) -> None:
    """
    Envia e-mail de verificação.

    Prioridade:
    1. Se RESEND_API_KEY estiver configurado → usa Resend API
    2. Caso contrário → usa SMTP direto

    Args:
        to_email: E-mail do destinatário
        token: Token de verificação

    Raises:
        RuntimeError: Se nenhum método estiver configurado ou houver erro no envio
    """
    verify_link = f"{APP_BASE_URL}/verify-email?token={token}"

    subject = "Confirme seu e-mail - Albion Market"
    body = f"""Olá!

Para confirmar seu e-mail, clique no link abaixo:
{verify_link}

Se você não solicitou esse cadastro, ignore este e-mail.
"""

    # Tenta Resend primeiro (melhor para produção)
    if RESEND_API_KEY:
        _send_via_resend(to_email, subject, body)
    else:
        # Fallback para SMTP
        _send_via_smtp(to_email, subject, body)

