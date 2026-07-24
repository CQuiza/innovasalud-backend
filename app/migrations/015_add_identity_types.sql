-- ============================================================
-- Migración 015: Ampliar tipos de identidad
-- Agrega CE, PPT, PASSPORT al CHECK constraint de identity_type
-- ============================================================

BEGIN;

ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_identity_type;

ALTER TABLE users ADD CONSTRAINT ck_users_identity_type
    CHECK (identity_type IN ('CC', 'TI', 'CE', 'PPT', 'PASSPORT', 'OTHER'));

COMMIT;
