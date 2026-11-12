-- Read-only database role for the AI service's ownership check. Run once by an operator as the
-- Postgres owner. Set the password interactively (psql: \password kien_ai_ro); never put it in git.
-- The service only runs: SELECT 1 FROM documents JOIN engagements ... (ids only, no document text).
CREATE ROLE kien_ai_ro LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM kien_ai_ro;
GRANT CONNECT ON DATABASE kien TO kien_ai_ro;  -- replace "kien" with the real database name
GRANT USAGE ON SCHEMA public TO kien_ai_ro;
GRANT SELECT (id, firm_id, engagement_id) ON documents TO kien_ai_ro;
GRANT SELECT (id, firm_id) ON engagements TO kien_ai_ro;
