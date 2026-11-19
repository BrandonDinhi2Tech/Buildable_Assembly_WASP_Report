"""Send an email with attachments.

Backend is chosen with MAIL_BACKEND in .env:
  outlook (default) - sends through the Outlook desktop app that is signed in on this PC (Windows, pywin32)
  smtp              - sends through an SMTP server (needs SMTP_* settings below)

.env settings for smtp:
  SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD, MAIL_FROM
"""
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_email(to, subject, body, attachments=None):
    """to: list of addresses. attachments: list of file paths."""
    if isinstance(to, str):
        to = [to]
    attachments = [str(Path(a).resolve()) for a in (attachments or [])]
    backend = os.getenv("MAIL_BACKEND", "outlook").lower()

    if backend == "outlook":
        _send_outlook(to, subject, body, attachments)
    elif backend == "smtp":
        _send_smtp(to, subject, body, attachments)
    else:
        raise ValueError("Unknown MAIL_BACKEND: " + backend)


def _send_outlook(to, subject, body, attachments):
    import win32com.client as win32  # pip install pywin32

    outlook = win32.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)  # 0 = mail item
    mail.To = "; ".join(to)
    mail.Subject = subject
    mail.Body = body
    for path in attachments:
        mail.Attachments.Add(path)
    mail.Send()


def _send_smtp(to, subject, body, attachments):
    msg = EmailMessage()
    msg["From"] = os.getenv("MAIL_FROM") or os.getenv("SMTP_USER")
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body)

    for path in attachments:
        with open(path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=os.path.basename(path),
        )

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", 587))
    # port 465 = SSL from the first byte; other ports (587) upgrade with STARTTLS
    if port == 465:
        server_cm = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server_cm = smtplib.SMTP(host, port, timeout=30)
    with server_cm as server:
        if port != 465:
            server.starttls()
        user = os.getenv("SMTP_USER")
        if user:
            server.login(user, os.getenv("SMTP_PASSWORD"))
        server.send_message(msg)
