#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
  echo "Open .env and add your LLM + Outlook + Google Drive settings, then run this script again."
  exit 0
fi

echo "=== Pyrithion AI setup ==="
echo "1. LLM_API_KEY (for OpenRouter/Gemini)"
read -r -p "   Paste key (or press Enter to skip): " llm_key
if [ -n "$llm_key" ]; then
  if grep -q '^LLM_API_KEY=' .env; then
    sed -i.bak "s|^LLM_API_KEY=.*|LLM_API_KEY=${llm_key}|" .env
  else
    echo "LLM_API_KEY=${llm_key}" >> .env
  fi
fi

echo "2. Outbound email (Outlook agent account — separate from Google Drive)"
read -r -p "   SMTP email [agent@example.com]: " smtp_user
smtp_user=${smtp_user:-agent@example.com}
read -r -s -p "   SMTP password: " smtp_pass
echo
if [ -n "$smtp_user" ]; then
  sed -i.bak "s|^SMTP_HOST=.*|SMTP_HOST=smtp-mail.outlook.com|" .env
  sed -i.bak "s|^SMTP_PORT=.*|SMTP_PORT=587|" .env
  sed -i.bak "s|^SMTP_USERNAME=.*|SMTP_USERNAME=${smtp_user}|" .env
  sed -i.bak "s|^SMTP_PASSWORD=.*|SMTP_PASSWORD=${smtp_pass}|" .env
  sed -i.bak "s|^SMTP_FROM_EMAIL=.*|SMTP_FROM_EMAIL=${smtp_user}|" .env
  sed -i.bak 's|^SMTP_FROM_NAME=.*|SMTP_FROM_NAME=Pyrithion AI|' .env
fi

echo "3. Google Drive folder (service account — keep your existing Google setup)"
read -r -p "   Folder ID (optional): " drive_folder
if [ -n "$drive_folder" ]; then
  sed -i.bak "s|^GOOGLE_DRIVE_FOLDER_ID=.*|GOOGLE_DRIVE_FOLDER_ID=${drive_folder}|" .env
  read -r -p "   Path to service account JSON: " sa_file
  if [ -n "$sa_file" ]; then
    sed -i.bak "s|^GOOGLE_SERVICE_ACCOUNT_FILE=.*|GOOGLE_SERVICE_ACCOUNT_FILE=${sa_file}|" .env
  fi
fi

echo "4. Inbound email is disabled by default (IMAP_ENABLED=false)."
read -r -p "   Enable email-in now? (y/N): " enable_imap
if [ "$enable_imap" = "y" ] || [ "$enable_imap" = "Y" ]; then
  sed -i.bak 's|^IMAP_ENABLED=.*|IMAP_ENABLED=true|' .env
  read -r -p "   IMAP email (leave empty to configure later): " imap_user
  if [ -n "$imap_user" ]; then
    read -r -s -p "   IMAP password: " imap_pass
    echo
    sed -i.bak "s|^IMAP_USERNAME=.*|IMAP_USERNAME=${imap_user}|" .env
    sed -i.bak "s|^IMAP_PASSWORD=.*|IMAP_PASSWORD=${imap_pass}|" .env
  fi
else
  sed -i.bak 's|^IMAP_ENABLED=.*|IMAP_ENABLED=false|' .env
fi

rm -f .env.bak
echo
echo "Setup saved to .env"
echo "Run: ./start.sh"
