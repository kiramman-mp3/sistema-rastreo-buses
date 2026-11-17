# Database helpers shared by init-prod.sh, backup.sh, restore.sh and reset-prod.sh. Source it after .env.prod.
#
# Production runs on an external Postgres (Supabase): DB_HOST is its host. With DB_HOST empty or "db" the
# local "db" container (profile local-db) is used instead, for development and labs.
#
# External databases are reached from a throwaway client container ($POSTGRES_IMAGE), always with TLS. Use
# Supabase's session pooler (port 5432) or the direct connection, never the transaction pooler (6543): Odoo keeps
# long connections and uses LISTEN/NOTIFY. pg_dump must be the same major version as the server or newer, so set
# POSTGRES_IMAGE to the server's version.

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-odoo}"
TRACCAR_DB_USER="${TRACCAR_DB_USER:-traccar}"
PG_CLIENT_IMAGE="${POSTGRES_IMAGE:-postgres:15}"

is_external_db() { [ "$DB_HOST" != "db" ]; }

# Runs a Postgres client tool (psql, pg_dump, pg_restore) against the server, with stdin passed through.
pg_tool() {
  local tool="$1"; shift
  if is_external_db; then
    docker run --rm -i -e PGPASSWORD="$DB_PASSWORD" -e PGSSLMODE=require "$PG_CLIENT_IMAGE" \
      "$tool" -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$@"
  else
    $DC exec -T db "$tool" -U odoo "$@"
  fi
}

psql_admin() { pg_tool psql -d postgres -v ON_ERROR_STOP=1 "$@"; }

db_exists() { [ -n "$(psql_admin -tAc "SELECT 1 FROM pg_database WHERE datname='$1'")" ]; }

# An empty database owned by the Odoo user (local) or by the account's user (external).
create_db() {
  if is_external_db; then psql_admin -c "CREATE DATABASE \"$1\""
  else psql_admin -c "CREATE DATABASE \"$1\" OWNER ${2:-odoo}"
  fi
}

# Starts the local container when it is the one in use, and waits for it.
wait_for_db() {
  if is_external_db; then
    local tries=0
    until psql_admin -tAc "SELECT 1" >/dev/null 2>&1; do
      tries=$((tries + 1))
      if [ "$tries" -ge 12 ]; then
        echo "Cannot reach the database at $DB_HOST:$DB_PORT as $DB_USER: check DB_HOST, DB_PORT, DB_USER and DB_PASSWORD."
        return 1
      fi
      sleep 5
    done
  else
    $DC up -d db
    until $DC exec -T db pg_isready -U odoo -d postgres >/dev/null 2>&1; do sleep 2; done
  fi
}
