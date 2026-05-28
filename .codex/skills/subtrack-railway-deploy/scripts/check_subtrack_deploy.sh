#!/usr/bin/env bash
set -euo pipefail

REPO="/Users/ris/Documents/vibecoding_11"
cd "$REPO"

echo "== SubTrack deploy snapshot =="
echo "repo: $REPO"

echo
echo "== Git =="
git remote -v | sed -n '1,2p'
git status --short
git log -1 --oneline

echo
echo "== Required files =="
for file in README.md PRD.md AGENTS.md main.py requirements.txt .env.example; do
  if [[ -f "$file" ]]; then
    echo "present: $file"
  else
    echo "missing: $file"
  fi
done

echo
echo "== Local env presence =="
if [[ -f .env ]]; then
  echo ".env: present"
  grep -q '^BOT_TOKEN=' .env && echo "BOT_TOKEN: present" || echo "BOT_TOKEN: missing"
  grep -q '^REMIND_DAYS_BEFORE=' .env && echo "REMIND_DAYS_BEFORE: present" || echo "REMIND_DAYS_BEFORE: missing"
  grep -q '^REMINDER_INTERVAL_SECONDS=' .env && echo "REMINDER_INTERVAL_SECONDS: present" || echo "REMINDER_INTERVAL_SECONDS: missing"
else
  echo ".env: missing"
fi

echo
echo "== Railway =="
if command -v railway >/dev/null 2>&1; then
  railway --version
  railway status || true
  railway deployment list -s vibecoding_11 -e production || true
else
  echo "railway CLI: missing"
fi

echo
echo "== Local polling conflicts =="
ps aux | rg -i '(/Users/ris/Documents/vibecoding_11/.+python main.py|/Users/ris/Documents/vibecoding_11|Python main.py|aiogram.dispatcher)' | rg -v 'rg -i' || true

echo
echo "== Telegram identity =="
if [[ -f .env ]] && grep -q '^BOT_TOKEN=' .env; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
  python3 - <<'PY'
import os, json, urllib.request
token = os.environ.get("BOT_TOKEN")
for method in ("getMe", "getWebhookInfo"):
    url = f"https://api.telegram.org/bot{token}/{method}"
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.load(r)
    result = data.get("result", {})
    if method == "getMe":
        print({"method": method, "ok": data.get("ok"), "username": result.get("username"), "id": result.get("id")})
    else:
        print({"method": method, "ok": data.get("ok"), "url_set": bool(result.get("url")), "pending_update_count": result.get("pending_update_count")})
PY
else
  echo "skipped: local BOT_TOKEN missing"
fi
