# app/services/mailer.py
"""
Serviço de envio de e-mails.

Prioridade:
1) Resend API (produção / Render)
2) SMTP (apenas se você realmente usar fora do Render)
"""
import os
from email.mime.text import MIMEText
import smtplib


# === Base URL do seu backend ou frontend (onde fica a rota de verificação) ===
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000").rstrip("/")

# === RESEND (produção) ===
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
# Exemplo: "Market Albion <no-reply@marketalbionbr.com.br>"
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")
# Opcional: para receber respostas em outro e-mail (ex: Gmail)
RESEND_REPLY_TO = os.getenv("RESEND_REPLY_TO", "")

# === SMTP (opcional; NÃO funciona no Render) ===
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def _is_render() -> bool:
    return os.getenv("RENDER") is not None or "render.com" in os.getenv("RENDER_EXTERNAL_URL", "")


def _send_via_resend(to_email: str, subject: str, text: str, html: str | None = None) -> None:
    """Envia e-mail via Resend API."""
    try:
        import httpx
    except ImportError as e:
        raise RuntimeError("Para usar Resend, instale: pip install httpx") from e

    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY não configurada.")
    if not RESEND_FROM_EMAIL:
        raise RuntimeError(
            "RESEND_FROM_EMAIL não configurada. Exemplo: "
            '"Market Albion <no-reply@marketalbionbr.com.br>"'
        )

    payload = {
        "from": RESEND_FROM_EMAIL,      # IMPORTANTÍSSIMO: precisa ser do seu domínio verificado
        "to": [to_email],
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html
    if RESEND_REPLY_TO:
        payload["reply_to"] = RESEND_REPLY_TO

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20.0,
    )

    # Resend pode retornar 200 ou 201
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Erro ao enviar e-mail via Resend ({response.status_code}): {response.text}")


def _send_via_smtp(to_email: str, subject: str, text: str) -> None:
    """Envia e-mail via SMTP (use só fora do Render)."""
    import logging

    if _is_render():
        raise RuntimeError(
            "SMTP não funciona no Render (porta 587 normalmente bloqueada). "
            "Use Resend configurando RESEND_API_KEY e RESEND_FROM_EMAIL."
        )

    missing = [k for k, v in {
        "SMTP_HOST": SMTP_HOST,
        "SMTP_USER": SMTP_USER,
        "SMTP_PASS": SMTP_PASS,
        "SMTP_FROM": SMTP_FROM,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"SMTP não configurado. Variáveis faltando: {', '.join(missing)}")

    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    logging.info(f"SMTP {SMTP_HOST}:{SMTP_PORT} -> enviando para {to_email}")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())


def send_verification_email(to_email: str, token: str) -> None:
    """Envia e-mail de verificação."""
    verify_link = f"{FRONTEND_URL}/verify-email?token={token}"

    subject = "Confirme seu e-mail - Albion Market"

    text = (
        "Olá!\n\n"
        "Para confirmar seu e-mail, clique no link abaixo:\n"
        f"{verify_link}\n\n"
        "Se você não solicitou esse cadastro, ignore este e-mail.\n"
    )

    html = f"""
    <div style="font-family:Arial,sans-serif; line-height:1.5">
      <h2>Confirme seu e-mail</h2>
      <p>Para confirmar seu e-mail, clique no botão abaixo:</p>
      <p>
        <a href="{verify_link}"
           style="display:inline-block;padding:12px 16px;background:#111;color:#fff;text-decoration:none;border-radius:10px">
           Confirmar e-mail
        </a>
      </p>
      <p style="color:#666;font-size:12px">Se você não solicitou esse cadastro, ignore este e-mail.</p>
      <p style="color:#666;font-size:12px">Link direto: {verify_link}</p>
    </div>
    """

    # Sempre tenta Resend primeiro (produção)
    if RESEND_API_KEY and RESEND_FROM_EMAIL:
        _send_via_resend(to_email, subject, text=text, html=html)
        return

    # Fallback SMTP (apenas fora do Render)
    _send_via_smtp(to_email, subject, text=text)
