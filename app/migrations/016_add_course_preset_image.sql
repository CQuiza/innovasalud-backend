-- ============================================================
-- Migración 016: Agregar preset_image a courses
-- Permite seleccionar imágenes predeterminadas sin pasar por MinIO
-- ============================================================

BEGIN;

ALTER TABLE courses
    ADD COLUMN IF NOT EXISTS preset_image VARCHAR(50) NULL;

COMMIT;
