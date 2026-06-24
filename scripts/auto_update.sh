#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REMOTE="${AUTO_UPDATE_REMOTE:-origin}"
BRANCH="${AUTO_UPDATE_BRANCH:-main}"
SERVICE="${AUTO_UPDATE_SERVICE:-holo-rick}"
HEALTH_URL="${AUTO_UPDATE_HEALTH_URL:-http://127.0.0.1:8362/}"
HEALTH_ATTEMPTS="${AUTO_UPDATE_HEALTH_ATTEMPTS:-30}"
HEALTH_INTERVAL_SECONDS="${AUTO_UPDATE_HEALTH_INTERVAL_SECONDS:-2}"
ROLLBACK_HEALTH_ATTEMPTS="${AUTO_UPDATE_ROLLBACK_HEALTH_ATTEMPTS:-20}"
LOCK_FILE="${AUTO_UPDATE_LOCK_FILE:-$APP_DIR/instance/auto-update.lock}"
STABLE_FILE="${AUTO_UPDATE_STABLE_FILE:-$APP_DIR/instance/last-stable-commit}"
BACKUP_DIR="${AUTO_UPDATE_BACKUP_DIR:-$APP_DIR/instance/update-backups}"
LOG_FILE="${AUTO_UPDATE_LOG_FILE:-$APP_DIR/logs/auto-update.log}"
DB_FILE="${AUTO_UPDATE_DB_FILE:-$APP_DIR/instance/holo_rick.db}"

mkdir -p "$(dirname "$LOCK_FILE")" "$BACKUP_DIR" "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE") 2>&1

log() {
  printf '[%s] %s\n' "$(date -Is)" "$*"
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

health_check() {
  local attempts="${1:-$HEALTH_ATTEMPTS}"
  local i
  for i in $(seq 1 "$attempts"); do
    if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null; then
      return 0
    fi
    sleep "$HEALTH_INTERVAL_SECONDS"
  done
  return 1
}

integrity_check() {
  HOLO_RICK_INTEGRITY_MODE=block python3 scripts/security/check-integrity.py --mode block
}

rollback_to_commit() {
  local rollback_commit="$1"
  local db_backup="${2:-}"
  log "Rollback auf stabilen Commit $rollback_commit"
  git reset --hard "$rollback_commit"
  if [[ -n "$db_backup" && -f "$db_backup" ]]; then
    cp -p "$db_backup" "$DB_FILE"
    log "Datenbank-Backup wiederhergestellt"
  fi
  compose build "$SERVICE"
  compose up -d "$SERVICE"
  if health_check "$ROLLBACK_HEALTH_ATTEMPTS"; then
    printf '%s\n' "$rollback_commit" > "$STABLE_FILE"
    log "Rollback erfolgreich"
    return 0
  fi
  log "Rollback fehlgeschlagen: Healthcheck bleibt rot"
  return 1
}

main() {
  cd "$APP_DIR"
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    log "Update läuft bereits, überspringe diesen Lauf"
    return 0
  fi

  if [[ ! -d .git ]]; then
    log "Kein Git-Repository in $APP_DIR"
    return 2
  fi
  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    log "Arbeitsbaum hat lokale Änderungen. Auto-Update abgebrochen, damit nichts überschrieben wird."
    git status --short --untracked-files=no
    return 2
  fi

  local old_commit target_commit db_backup timestamp short_old
  old_commit="$(git rev-parse HEAD)"
  short_old="${old_commit:0:12}"
  timestamp="$(date +%Y%m%d-%H%M%S)"
  db_backup=""

  log "Prüfe $REMOTE/$BRANCH von $old_commit"
  git fetch --prune "$REMOTE" "$BRANCH"
  target_commit="$(git rev-parse "$REMOTE/$BRANCH")"

  if [[ "$old_commit" == "$target_commit" ]]; then
    log "Keine neuen Änderungen"
    if ! integrity_check; then
      log "Integritätsprüfung des aktuellen Standes fehlgeschlagen"
      return 2
    fi
    if health_check 3; then
      printf '%s\n' "$old_commit" > "$STABLE_FILE"
    fi
    return 0
  fi

  if [[ -f "$DB_FILE" ]]; then
    db_backup="$BACKUP_DIR/holo_rick_db_${timestamp}_${short_old}.sqlite"
    cp -p "$DB_FILE" "$db_backup"
    log "Datenbank-Backup erstellt: $db_backup"
  fi

  if ! git merge --ff-only "$REMOTE/$BRANCH"; then
    log "Fast-Forward nicht möglich. Update abgebrochen."
    return 3
  fi

  if ! integrity_check; then
    log "Integritätsprüfung nach Update fehlgeschlagen"
    rollback_to_commit "$old_commit" "$db_backup"
    return 1
  fi

  if ! compose build "$SERVICE"; then
    log "Build fehlgeschlagen"
    rollback_to_commit "$old_commit" "$db_backup"
    return 1
  fi

  if ! compose up -d "$SERVICE"; then
    log "Container-Start fehlgeschlagen"
    rollback_to_commit "$old_commit" "$db_backup"
    return 1
  fi

  if ! health_check "$HEALTH_ATTEMPTS"; then
    log "Healthcheck fehlgeschlagen"
    rollback_to_commit "$old_commit" "$db_backup"
    return 1
  fi

  printf '%s\n' "$target_commit" > "$STABLE_FILE"
  log "Update erfolgreich: $target_commit"
}

main "$@"
