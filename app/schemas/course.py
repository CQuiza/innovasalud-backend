"""Curso."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CourseStatus


class CourseCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    certificate_type_id: int | None = None
    teacher_id: int | None = None
    status: CourseStatus = CourseStatus.draft
    preset_image: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    certificate_type_id: int | None = None
    teacher_id: int | None = None
    status: CourseStatus | None = None
    preset_image: str | None = None

    model_config = ConfigDict(extra="forbid")


class CourseRead(BaseModel):
    id: int
    title: str
    description: str | None
    certificate_type_id: int | None
    teacher_id: int | None
    preset_image: str | None = None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime
    status: CourseStatus

    model_config = ConfigDict(from_attributes=True)


class CoursePublicRead(BaseModel):
    """Listado público (catálogo)."""

    id: int
    title: str
    description: str | None
    preset_image: str | None = None
    image_url: str | None = None
    status: CourseStatus

    model_config = ConfigDict(from_attributes=True)
