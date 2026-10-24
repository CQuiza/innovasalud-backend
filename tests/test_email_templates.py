from datetime import datetime, timezone
from html import escape

from app.utils.email_templates import (
    EXPIRED_EMAIL_SUBJECT,
    PUBLIC_FACEBOOK_URL,
    PUBLIC_INSTAGRAM_URL,
    PUBLIC_LOGO_URL,
    PUBLIC_SITE_URL,
    PUBLIC_WHATSAPP_URL,
    expired_body,
    format_date_es,
)


def test_format_date_es():
    assert format_date_es(datetime(2026, 10, 5, tzinfo=timezone.utc)) == "5 de octubre de 2026"
    assert format_date_es(None) is None


def test_expired_email_subject():
    assert EXPIRED_EMAIL_SUBJECT == (
        "¡Tu certificado ha vencido! Renueva con INNOVASALUD COLOMBIA SAS "
        "y recibe beneficios exclusivos"
    )


def test_expired_body_personalizes_data_and_links():
    html = expired_body(
        "JUAN PÉREZ & CIA",
        "CURSO BÁSICO DE PRIMEROS AUXILIOS",
        datetime(2026, 10, 19, tzinfo=timezone.utc),
    )

    assert "JUAN PÉREZ &amp; CIA" in html
    assert "CURSO BÁSICO DE PRIMEROS AUXILIOS" in html
    assert "19 de octubre de 2026" in html
    assert PUBLIC_LOGO_URL in html
    assert PUBLIC_WHATSAPP_URL in html
    assert PUBLIC_SITE_URL in html
    assert escape(PUBLIC_FACEBOOK_URL) in html
    assert PUBLIC_INSTAGRAM_URL in html
    assert "{{" not in html
    assert "{%" not in html


def test_expired_body_without_optional_data():
    html = expired_body("ESTUDIANTE")

    assert "según su vigencia" in html
    assert "{{" not in html
    assert "{%" not in html
