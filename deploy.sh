#!/usr/bin/env bash
#
# deploy.sh — resilient static-site deploy for audiolibri.org
#
# The nginx docroot (/var/www/audiolibri.org) is a plain git checkout, so a
# deploy is just "pull the latest commit". This script does it *safely*:
#
#   - single-instance lock        (no overlapping runs)
#   - fast-forward only            (never rewrites history on the server)
#   - refuses to clobber local edits unless you ask (FORCE_RESET=1)
#   - validates app.js + JSON before declaring success
#   - automatic rollback to the previous commit if validation fails
#   - runs git as the docroot owner (www-data) to keep permissions correct
#
# Run on origin-01 as root (or as www-data).
#
#   ./deploy.sh                          # deploy origin/main
#   BRANCH=redesign/netflix-seo ./deploy.sh
#   FORCE_RESET=1 ./deploy.sh            # one-time: hard-reset a DIVERGED
#                                        # checkout to origin/BRANCH
#   RELOAD_NGINX=1 ./deploy.sh           # also reload nginx (only if config changed)
#
set -euo pipefail

# ---- config (override via environment) --------------------------------------
DIR="${DIR:-/var/www/audiolibri.org}"
BRANCH="${BRANCH:-main}"
REMOTE="${REMOTE:-origin}"
OWNER="${OWNER:-www-data}"
LOG="${LOG:-/var/log/audiolibri-deploy.log}"
LOCK="${LOCK:-/run/audiolibri-deploy.lock}"
RELOAD_NGINX="${RELOAD_NGINX:-0}"
FORCE_RESET="${FORCE_RESET:-0}"
# -----------------------------------------------------------------------------

log()  { printf '%s  %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "$LOG" >&2; }
die()  { log "ERROR: $*"; exit 1; }

# Run git as the docroot owner so file ownership never drifts and we avoid
# git's "dubious ownership" guard. If we're already that user, skip sudo.
git_as() {
    if [ "$(id -un)" = "$OWNER" ]; then
        git -C "$DIR" "$@"
    else
        sudo -u "$OWNER" git -C "$DIR" "$@"
    fi
}

# --- single instance ---------------------------------------------------------
exec 9>"$LOCK" || die "cannot open lock file $LOCK"
flock -n 9     || die "another deploy is already running (lock: $LOCK)"

[ -d "$DIR/.git" ] || die "$DIR is not a git checkout"

# trust the docroot for the owner (idempotent)
git_as config --global --get-all safe.directory 2>/dev/null | grep -qxF "$DIR" \
    || git_as config --global --add safe.directory "$DIR" || true

OLD="$(git_as rev-parse HEAD)"
log "current: ${OLD:0:8} on $(git_as rev-parse --abbrev-ref HEAD)"

log "fetching $REMOTE ..."
git_as fetch --prune --quiet "$REMOTE" || die "git fetch failed"

TARGET="$(git_as rev-parse "$REMOTE/$BRANCH" 2>/dev/null)" || die "unknown ref $REMOTE/$BRANCH"

if [ "$OLD" = "$TARGET" ]; then
    log "already up to date ($BRANCH @ ${TARGET:0:8}) — nothing to do."
    exit 0
fi

# --- refuse to silently discard local edits ----------------------------------
if [ -n "$(git_as status --porcelain)" ] && [ "$FORCE_RESET" != "1" ]; then
    die "working tree has local changes — commit them, or rerun with FORCE_RESET=1 to discard."
fi

# --- update ------------------------------------------------------------------
if [ "$FORCE_RESET" = "1" ]; then
    log "FORCE_RESET: hard-resetting to $REMOTE/$BRANCH (local changes discarded)"
    git_as reset --hard "$REMOTE/$BRANCH" || die "reset failed"
elif ! git_as merge --ff-only "$REMOTE/$BRANCH"; then
    die "cannot fast-forward $BRANCH (history diverged). One-time reconcile: FORCE_RESET=1 ./deploy.sh"
fi

NEW="$(git_as rev-parse HEAD)"
log "updated: ${OLD:0:8} -> ${NEW:0:8}"

# --- validate, rollback on failure -------------------------------------------
rollback() { log "VALIDATION FAILED: $*"; log "rolling back to ${OLD:0:8}"; git_as reset --hard "$OLD"; exit 1; }

for f in index.html app.js; do
    [ -s "$DIR/$f" ] || rollback "$f is missing or empty"
done
[ -s "$DIR/app.css" ] || [ -s "$DIR/styles.css" ] || rollback "no stylesheet found (app.css or styles.css)"

# JS syntax — authoritative when node is available (install it for a real gate)
if command -v node >/dev/null 2>&1; then
    node --check "$DIR/app.js" 2>>"$LOG" || rollback "app.js has a JavaScript syntax error"
    log "app.js syntax OK"
else
    log "WARNING: node not found — cannot syntax-check app.js (consider installing nodejs)"
fi

# JSON integrity (python3 ships with Debian/Ubuntu)
if command -v python3 >/dev/null 2>&1; then
    for j in augmented.json audiobooks.json; do
        [ -f "$DIR/$j" ] && { python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$DIR/$j" 2>>"$LOG" \
            || rollback "$j is not valid JSON"; }
    done
    log "JSON integrity OK"
fi

# --- finalize ----------------------------------------------------------------
[ "$(id -u)" = "0" ] && chown -R "$OWNER":"$OWNER" "$DIR" 2>/dev/null || true

if [ "$RELOAD_NGINX" = "1" ]; then
    if nginx -t 2>>"$LOG"; then systemctl reload nginx && log "nginx reloaded"; else log "WARNING: nginx -t failed — NOT reloaded"; fi
fi

log "✅ deploy OK — $BRANCH now at ${NEW:0:8}"
