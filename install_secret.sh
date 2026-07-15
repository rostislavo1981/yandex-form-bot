#!/bin/bash
# install_secret.sh — safely write one or more secrets into .env
#
# Usage:
#   ./install_secret.sh MAX_BOT_TOKEN
#   ./install_secret.sh MAX_BOT_TOKEN YANDEX_GPT_API_KEY YANDEX_GPT_FOLDER_ID
#
# The script:
#   1. Prompts for each var with hidden input (read -s, nothing echoes)
#   2. Validates non-empty
#   3. Replaces the line in .env (or appends if missing)
#   4. chmod 600 .env so only you can read it
#   5. Prints ONLY metadata (length + first 4 chars), never the value itself
#
# Safe to commit: this script never logs the secret value.

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f ".env.example" ]; then
        echo "📋 .env not found, copying from .env.example"
        cp .env.example "$ENV_FILE"
    else
        echo "❌ No .env or .env.example found. Create one first." >&2
        exit 1
    fi
fi

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 VAR_NAME [VAR_NAME ...]" >&2
    echo "Example: $0 MAX_BOT_TOKEN YANDEX_GPT_API_KEY" >&2
    exit 1
fi

# Verify we are NOT running under a process that could log stdin (e.g. tee, script)
# Best-effort check; the user can always run interactively in their own terminal.
if [ ! -t 0 ]; then
    echo "⚠️  stdin is not a TTY — input might be logged by your shell wrapper." >&2
    echo "    Run this script directly in your terminal, not piped." >&2
    read -r -p "    Continue anyway? [y/N] " ans
    case "$ans" in
        y|Y) ;;
        *)   exit 1 ;;
    esac
fi

updated=0
for var in "$@"; do
    # Skip invalid var names (defense in depth)
    if ! [[ "$var" =~ ^[A-Z_][A-Z0-9_]*$ ]]; then
        echo "❌ Invalid var name: $var (must match ^[A-Z_][A-Z0-9_]*$)" >&2
        continue
    fi

    # Prompt with hidden input
    prompt="$var: "
    read -r -s -p "$prompt" value
    echo    # newline after hidden input

    if [ -z "$value" ]; then
        echo "   ⏭  empty, skipped"
        continue
    fi

    # Validate basic shapes
    case "$var" in
        *_URL)
            if ! [[ "$value" =~ ^https?:// ]]; then
                echo "   ⚠️  $var doesn't look like a URL (no http:// or https:// prefix)" >&2
                read -r -p "      Save anyway? [y/N] " ans
                case "$ans" in y|Y) ;; *) continue ;; esac
            fi
            ;;
        *BOT_TOKEN)
            # Telegram/MAX bot tokens: <bot_id>:<token>, length ~46
            if [ "${#value}" -lt 20 ]; then
                echo "   ⚠️  $var is only ${#value} chars; bot tokens are usually 40+" >&2
                read -r -p "      Save anyway? [y/N] " ans
                case "$ans" in y|Y) ;; *) continue ;; esac
            fi
            ;;
        *_API_KEY)
            if [ "${#value}" -lt 10 ]; then
                echo "   ⚠️  $var is only ${#value} chars; API keys are usually 20+" >&2
                read -r -p "      Save anyway? [y/N] " ans
                case "$ans" in y|Y) ;; *) continue ;; esac
            fi
            ;;
    esac

    # Remove existing line(s) for this var, then append the new one
    tmp="${ENV_FILE}.tmp.$$"
    grep -v "^${var}=" "$ENV_FILE" > "$tmp" 2>/dev/null || true
    printf '%s=%s\n' "$var" "$value" >> "$tmp"
    mv "$tmp" "$ENV_FILE"

    # Print metadata only — NEVER the value
    prefix="${value:0:4}"
    len=${#value}
    echo "   ✅ $var  prefix=$prefix  length=$len"
    updated=$((updated + 1))
done

# Tighten permissions — only owner can read
chmod 600 "$ENV_FILE"

echo ""
if [ "$updated" -gt 0 ]; then
    echo "🔒 $ENV_FILE updated ($updated var(s)), permissions set to 600"
    echo "   You can verify with:  ls -la $ENV_FILE"
else
    echo "ℹ️  No variables were written"
fi
