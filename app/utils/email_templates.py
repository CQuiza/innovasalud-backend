"""Plantillas HTML para correos electrónicos."""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Datos públicos de la marca (no dependen del entorno por lo que no usan .env)
PUBLIC_SITE_URL = "https://innova-salud.com.co"
PUBLIC_LOGO_URL = f"{PUBLIC_SITE_URL}/logo.png"
PUBLIC_WHATSAPP_URL = "https://wa.me/573197917718"
PUBLIC_FACEBOOK_URL = (
    "https://web.facebook.com/p/InnovaSalud-Colombia-61565874131259/?_rdc=1&_rdr#"
)
PUBLIC_INSTAGRAM_URL = "https://www.instagram.com/innovasalud_colombia/"

EXPIRED_EMAIL_SUBJECT = (
    "¡Tu certificado ha vencido! Renueva con INNOVASALUD COLOMBIA SAS "
    "y recibe beneficios exclusivos"
)

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "emails"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

_MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def format_date_es(value: datetime | None) -> str | None:
    """Formatea una fecha como '5 de octubre de 2026' sin depender del locale."""
    if value is None:
        return None
    return f"{value.day} de {_MONTHS_ES[value.month - 1]} de {value.year}"


def credentials_body(app_name: str, email_to: str, password: str, login_url: str) -> str:
    return f"""<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2>Bienvenido a {app_name}</h2>
    <p>Tu cuenta ha sido creada exitosamente. Estas son tus credenciales de acceso:</p>
    <p><strong>Correo:</strong> {email_to}</p>
    <p><strong>Contraseña:</strong> {password}</p>
    <p>Puedes acceder en el siguiente enlace:</p>
    <p><a href="{login_url}">{login_url}</a></p>
</body>
</html>"""


def issued_body(
    app_name: str,
    student_name: str,
    verify_link: str,
    certificate_type_name: str | None = None,
) -> str:
    cert_line = (
        f'<p><strong>Certificado:</strong> {certificate_type_name}</p>'
        if certificate_type_name
        else ""
    )
    return f"""<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2>Certificado Emitido</h2>
    <p>Hola <strong>{student_name}</strong>,</p>
    <p>Te informamos que tu certificado ha sido emitido exitosamente.</p>
    {cert_line}
    <p>Puedes verificar y descargar tu certificado en el siguiente enlace:</p>
    <p><a href="{verify_link}">{verify_link}</a></p>
    <p>Si tienes alguna duda, por favor contacta al administrador.</p>
</body>
</html>"""


def contact_body(name: str, email: str, program: str, message: str) -> str:
    return f"""<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2>Nuevo contacto desde la web</h2>
    <table style="border-collapse: collapse; width: 100%;">
        <tr><td style="padding: 8px; font-weight: bold;">Nombre:</td><td style="padding: 8px;">{name}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Email:</td><td style="padding: 8px;">{email}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Programa de interés:</td><td style="padding: 8px;">{program}</td></tr>
    </table>
    <h3>Mensaje:</h3>
    <p style="background: #f5f5f5; padding: 16px; border-radius: 8px;">{message}</p>
</body>
</html>"""


def expired_body(
    student_name: str,
    certificate_type_name: str | None = None,
    expires_at: datetime | None = None,
) -> str:
    template = _env.get_template("certificate_expired.html")
    return template.render(
        student_name=student_name,
        certificate_type_name=certificate_type_name,
        expires_at=format_date_es(expires_at),
        logo_url=PUBLIC_LOGO_URL,
        whatsapp_url=PUBLIC_WHATSAPP_URL,
        website_url=PUBLIC_SITE_URL,
        facebook_url=PUBLIC_FACEBOOK_URL,
        instagram_url=PUBLIC_INSTAGRAM_URL,
    )


def backup_body(
    app_name: str,
    *,
    filename: str,
    size_bytes: int,
    uploaded: bool,
    extra: str | None = None,
) -> str:
    size_mb = size_bytes / (1024 * 1024)
    destino = "MinIO externo (backup)" if uploaded else "adjunto a este correo"
    status_html = "OK" if uploaded else "FALLIDO"
    color = "#198754" if uploaded else "#dc3545"
    extra_html = f"<p>{extra}</p>" if extra else ""
    return f"""<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2>Backup de base de datos — {app_name}</h2>
    <p style="color:{color}; font-weight: bold;">Estado: {status_html}</p>
    <p><strong>Archivo:</strong> {filename}</p>
    <p><strong>Tamaño:</strong> {size_mb:.2f} MB</p>
    <p><strong>Destino:</strong> {destino}</p>
    {extra_html}
</body>
</html>"""
