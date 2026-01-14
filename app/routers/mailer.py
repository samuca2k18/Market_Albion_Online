# app/services/mailer.py
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")


def send_verification_email(to_email: str, token: str):
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_FROM]):
        raise RuntimeError("SMTP não configurado (SMTP_HOST/SMTP_USER/SMTP_PASS/SMTP_FROM).")

    verify_link = f"{APP_BASE_URL}/verify-email?token={token}"

    subject = "Confirme seu e-mail - Albion Market"
    body = f"""Olá!

Para confirmar seu e-mail, clique no link abaixo:
{verify_link}

Se você não solicitou esse cadastro, ignore este e-mail.
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
