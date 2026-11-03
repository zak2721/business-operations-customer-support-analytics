-- =============================================================================
-- 01_create_database.sql
-- Creates the analytics database. Run as a superuser / owner, e.g.:
--   psql -h localhost -U postgres -f sql/01_database_setup/01_create_database.sql
-- (Run once. Everything else is created inside the `support` schema.)
-- =============================================================================
SELECT 'CREATE DATABASE support_analytics'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'support_analytics')\gexec
