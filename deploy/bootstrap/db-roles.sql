-- Least-privilege database roles. Run once (idempotent) as the bootstrap superuser, before the first
-- migration, with passwords passed through the environment (never on the command line):
--   KIEN_MIGRATOR_PASSWORD=... KIEN_APP_PASSWORD=... KIEN_BACKUP_PASSWORD=... \
--     psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f db-roles.sql
-- deploy/bootstrap/db-roles.sh does exactly this inside the postgres container.
--   kien_migrator  owns the schema; used only by the one-shot migrate service (DDL).
--   kien_app       DML only (SELECT/INSERT/UPDATE/DELETE); used by api and worker. No CREATE/DROP.
--   kien_backup    read-only; for pg_dump.
\set ON_ERROR_STOP on
\getenv migrator_pw KIEN_MIGRATOR_PASSWORD
\getenv app_pw KIEN_APP_PASSWORD
\getenv backup_pw KIEN_BACKUP_PASSWORD

SELECT format('CREATE ROLE %I LOGIN', r) FROM unnest(ARRAY['kien_migrator','kien_app','kien_backup']) r
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) \gexec

ALTER ROLE kien_migrator WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'migrator_pw';
ALTER ROLE kien_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_pw';
ALTER ROLE kien_backup WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'backup_pw';

SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database()) \gexec
SELECT format('GRANT CONNECT, TEMPORARY ON DATABASE %I TO kien_migrator, kien_app, kien_backup', current_database()) \gexec

-- Only the migrator may create objects in public.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO kien_migrator;
GRANT USAGE ON SCHEMA public TO kien_app, kien_backup;

-- Existing objects (re-runs after migrations) and every future object the migrator creates.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO kien_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO kien_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO kien_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO kien_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE kien_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kien_app;
ALTER DEFAULT PRIVILEGES FOR ROLE kien_migrator IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO kien_app;
ALTER DEFAULT PRIVILEGES FOR ROLE kien_migrator IN SCHEMA public GRANT SELECT ON TABLES TO kien_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE kien_migrator IN SCHEMA public GRANT SELECT ON SEQUENCES TO kien_backup;
