---
name: subtrack-railway-deploy
description: "Deploy, redeploy, or debug the SubTrack Telegram bot project `serejaris/vibecoding_11` on Railway. Use when the user asks to make the bot work 24/7, fix Railway deploy errors, set Railway variables, diagnose `BOT_TOKEN не найден`, resolve Telegram `Conflict: terminated by other getUpdates request`, or verify the live `@ris_subtrack_bot` runtime."
---

# SubTrack Railway Deploy

## Scope

Operate the SubTrack Telegram bot deployment.

- Local repo: `/Users/ris/Documents/vibecoding_11`
- GitHub repo: `https://github.com/serejaris/vibecoding_11`
- Railway project: `brilliant-motivation`
- Railway environment: `production`
- Railway service: `vibecoding_11`
- Telegram bot: `@ris_subtrack_bot`
- Start command: `python main.py`
- Runtime mode: long polling, exactly one active process per token

Do not print, paste, commit, or summarize real token values.

## First Response

State the current surface: local repo, GitHub, Railway, or Telegram runtime. If the user reports a crash, inspect the logs first. If the screenshot or logs show `BOT_TOKEN не найден`, fix Railway variables before changing code.

## Quick Check

Run the bundled script for a safe read-only snapshot:

```bash
/Users/ris/.codex/skills/subtrack-railway-deploy/scripts/check_subtrack_deploy.sh
```

The script checks local repo status, required files, local env presence without printing secrets, Railway link/status, recent deployments, recent logs, Telegram `getMe`, webhook state, and local process conflicts.

## Deploy Or Repair Workflow

1. Work from `/Users/ris/Documents/vibecoding_11`.
2. Check local status and avoid touching unrelated dirty files.
3. Verify tests when code changed:

```bash
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

4. Ensure Railway CLI is installed and linked:

```bash
railway link -p brilliant-motivation -e production -s vibecoding_11
railway status
```

5. If Railway lacks variables, copy from local `.env` without printing values:

```bash
set -a
. ./.env
set +a
railway variables --set "BOT_TOKEN=$BOT_TOKEN" --set "REMIND_DAYS_BEFORE=${REMIND_DAYS_BEFORE:-3}" --skip-deploys
```

6. Redeploy:

```bash
railway redeploy -s vibecoding_11 --yes
railway deployment list -s vibecoding_11 -e production
```

7. Inspect logs. A healthy startup contains:

```text
Start polling
Run polling for bot @ris_subtrack_bot
```

8. If logs contain Telegram conflict, stop the other process using the same token. Check local first:

```bash
ps aux | rg -i 'vibecoding_11|main.py|aiogram' | rg -v rg
```

Kill only the SubTrack local process after confirming it is the duplicate. Do not stop unrelated Python bots.

9. Verify Telegram token identity without exposing it:

```bash
set -a
. ./.env
set +a
python3 - <<'PY'
import os, json, urllib.request
url = f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/getMe"
with urllib.request.urlopen(url, timeout=10) as r:
    data = json.load(r)
print({"ok": data.get("ok"), "username": data.get("result", {}).get("username"), "id": data.get("result", {}).get("id")})
PY
```

## Common Failures

- `RuntimeError: BOT_TOKEN не найден`: Railway env var is missing. Add `BOT_TOKEN` in Railway variables, then redeploy.
- `TelegramConflictError: Conflict: terminated by other getUpdates request`: the same token is running in another polling process. Stop local `python main.py` or the older cloud deployment.
- Empty `railway logs --lines`: use `railway deployment list` to get the latest deployment id, then call `railway logs <deployment-id> --deployment --lines 120`.
- Local tests fail with `No module named pytest`: this repo uses `unittest`; run `.venv/bin/python -m unittest discover -s tests -v`.

## Safety Rules

- Do not commit `.env`, `data/*.db`, logs, or token values.
- Do not rotate the Telegram token unless the user explicitly asks.
- Do not claim production is fixed until Railway logs show polling or Telegram runtime is otherwise verified.
- Keep SQLite unless the user asks for production storage changes.
