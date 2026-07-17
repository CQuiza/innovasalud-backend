"""Cursos."""

import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from minio.error import S3Error
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, get_optional_user
from app.core.database import get_db
from app.core.settings import get_settings
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.course_repository import course_repository
from app.schemas.course import CourseCreate, CoursePublicRead, CourseRead, CourseUpdate
from app.services.access import is_super_or_admin, is_student, require_course_visible
from app.services.course_service import course_service
from app.utils.minio_client import get_minio_client

router = APIRouter(prefix="/courses", tags=["courses"])

ALLOWED_IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})
COURSE_IMAGE_MAX_SIZE = 5 * 1024 * 1024  # 5 MB

_EXT_MEDIA_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@router.get("")
async def list_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    optional_user: Annotated[User | None, Depends(get_optional_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list:
    rows = await course_service.list_for_actor(db, actor=optional_user, skip=skip, limit=limit)
    if optional_user and is_super_or_admin(optional_user):
        return [CourseRead.model_validate(r) for r in rows]
    return [CoursePublicRead.model_validate(r) for r in rows]


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    optional_user: Annotated[User | None, Depends(get_optional_user)],
) -> object:
    need_enrollment = optional_user is not None and is_student(optional_user)
    await require_course_visible(db, optional_user, course_id, need_content=need_enrollment)
    c = await course_repository.get_by_id(db, course_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    return c


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> object:
    if current.role not in (UserRole.superuser.value, UserRole.admin.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores")
    return await course_repository.create(
        db,
        title=body.title,
        description=body.description,
        certificate_type_id=body.certificate_type_id,
        teacher_id=body.teacher_id,
        status=body.status.value,
    )


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: int,
    body: CourseUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> object:
    if not is_super_or_admin(current):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores")
    c = await course_repository.get_by_id(db, course_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    payload = body.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"] is not None:
        payload["status"] = payload["status"].value
    return await course_repository.update(db, c, payload)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> None:
    if not is_super_or_admin(current):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores")
    c = await course_repository.get_by_id(db, course_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    await course_repository.delete(db, c)


@router.post("/{course_id}/image", response_model=CourseRead)
async def upload_course_image(
    course_id: int,
    file: UploadFile,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> object:
    if not is_super_or_admin(current):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores")
    c = await course_repository.get_by_id(db, course_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no válido. Use JPG, PNG, GIF o WebP.",
        )

    data = await file.read()
    if len(data) > COURSE_IMAGE_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen supera el límite de 5 MB",
        )

    settings = get_settings()
    object_name = f"{settings.minio_path_course_images}/{course_id}{ext}"

    client = get_minio_client(settings)
    client.ensure_bucket()
    try:
        await asyncio.to_thread(
            client.upload_bytes,
            object_name,
            data,
            content_type=file.content_type or "image/png",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al subir imagen: {e}",
        )

    if c.image_url and c.image_url != object_name:
        try:
            await asyncio.to_thread(client.remove_object, c.image_url)
        except Exception:
            pass

    return await course_repository.update(db, c, {"image_url": object_name})


@router.get("/{course_id}/image")
async def get_course_image(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    c = await course_repository.get_by_id(db, course_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")

    settings = get_settings()
    client = get_minio_client(settings)
    default_key = f"{settings.minio_path_course_images}/default.png"
    object_name = c.image_url or default_key

    try:
        data = await asyncio.to_thread(client.download_bytes, object_name)
    except S3Error as e:
        code = str(getattr(e, "code", "") or "").lower()
        if code in ("nosuchkey", "notfound"):
            try:
                data = await asyncio.to_thread(client.download_bytes, default_key)
            except S3Error:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Imagen no encontrada",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e),
            )

    media_type = _EXT_MEDIA_TYPE.get(Path(object_name).suffix.lower(), "application/octet-stream")
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.delete("/{course_id}/image", response_model=CourseRead)
async def delete_course_image(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
) -> object:
    if not is_super_or_admin(current):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores")
    c = await course_repository.get_by_id(db, course_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    if not c.image_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El curso no tiene imagen personalizada",
        )

    try:
        client = get_minio_client(get_settings())
        await asyncio.to_thread(client.remove_object, c.image_url)
    except Exception:
        pass

    return await course_repository.update(db, c, {"image_url": None})
