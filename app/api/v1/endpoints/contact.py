"""Formulario de contacto público."""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi_mail import FastMail, MessageSchema

from app.schemas.contact import ContactForm
from app.utils.email import _get_mail_config
from app.utils.email_templates import contact_body

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", status_code=status.HTTP_200_OK)
async def submit_contact_form(data: ContactForm) -> dict:
    conf = _get_mail_config()
    if conf is None:
        logger.warning("SMTP no configurado. No se envió el mensaje de contacto.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El servicio de correo no está configurado.",
        )

    message = MessageSchema(
        subject=f"Nuevo contacto: {data.name} — {data.program}",
        recipients=[conf.MAIL_FROM],
        body=contact_body(data.name, data.email, data.program, data.message),
        subtype="html",
        reply_to=[data.email],
    )
    fm = FastMail(conf)
    await fm.send_message(message)
    logger.info("Mensaje de contacto recibido de %s (%s)", data.name, data.email)
    return {"detail": "Mensaje enviado correctamente"}
