# Luma Registration Sync — User Guide

A Python script that pulls event registration data from Luma and writes it to Google Sheets.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
   - [Luma API Key](#31-luma-api-key)
   - [Google Sheets OAuth Setup](#32-google-sheets-oauth-setup)
   - [Environment Variables](#33-environment-variables)
4. [Usage](#4-usage)
   - [Interactive Mode](#41-interactive-mode)
   - [Batch Mode](#42-batch-mode)
   - [CLI Reference](#43-cli-reference)
5. [Spreadsheet Output](#5-spreadsheet-output)
   - [Fixed Columns](#51-fixed-columns)
   - [Dynamic Columns](#52-dynamic-columns)
   - [Write Modes](#53-write-modes)
6. [Examples](#6-examples)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prerequisites

- **Python 3.10+** (uses `X | None` type syntax)
- **Luma Plus subscription** — required to access the Luma API
- **Google Cloud project** — for Google Sheets OAuth credentials

## 2. Installation

```bash
cd ~/Documents/notes/Claude/Luma

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

The `requirements.txt` installs:

| Package                | Purpose                              |
|------------------------|--------------------------------------|
| `requests`             | HTTP client for the Luma API         |
| `gspread`              | Google Sheets Python client          |
| `google-auth-oauthlib` | Google OAuth 2.0 browser login flow  |
| `python-dotenv`        | Loads environment variables from `.env` |

## 3. Configuration

### 3.1 Luma API Key

Your Luma API key authenticates requests to the Luma API. Each Luma calendar has its own key.

**To find your key:**
1. Log into [lu.ma](https://lu.ma)
2. Go to your calendar's settings
3. Navigate to the API section
4. Copy the key (starts with `secret-`)

**To configure it**, choose one of:

| Method | How |
|--------|-----|
| `.env` file (recommended) | Add `LUMA_API_KEY=secret-YourKeyHere` to the `.env` file |
| Environment variable | `export LUMA_API_KEY=secret-YourKeyHere` |
| CLI flag | `--api-key secret-YourKeyHere` |

Priority order: `--api-key` flag > `LUMA_API_KEY` environment variable > `.env` file.

### 3.2 Google Sheets OAuth Setup

The script uses OAuth 2.0 to access Google Sheets on your behalf. This requires a one-time setup in Google Cloud Console.

**Step 1 — Create a Google Cloud project**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a Project** > **New Project**
3. Name it (e.g., "Luma Sync") and click **Create**

**Step 2 — Enable APIs**
1. Go to **APIs & Services** > **Library**
2. Search for and enable **Google Sheets API**
3. Search for and enable **Google Drive API**

**Step 3 — Configure OAuth consent screen**
1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** user type > **Create**
3. Fill in the required fields (app name, user support email, developer email)
4. On the **Scopes** page, add:
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/drive`
5. On **Test users**, add your own Google email address
6. Save and continue

**Step 4 — Create OAuth credentials**
1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Application type: **Desktop app**
4. Name it (e.g., "Luma Sync Desktop")
5. Click **Create**, then **Download JSON**

**Step 5 — Install the credentials file**
Save the downloaded JSON file as:
```
credentials/client_secret.json
```

The script also checks these alternate locations:
- `credentials/credentials.json`
- `client_secret.json` (project root)

**First run:** The script opens your browser for Google login. After you approve access, a token is saved to `credentials/token.json` and reused on future runs. You will not need to log in again unless the token expires or is deleted.

### 3.3 Environment Variables

Create a `.env` file in the project root (a `.env.example` template is provided):

```bash
# Required
LUMA_API_KEY=secret-YourKeyHere

# Optional — sets the default event ID for interactive mode
LUMA_DEFAULT_EVENT_ID=evt-E7CYitIvydBWi0x
```

The `.env` file is listed in `.gitignore` and will not be committed.

## 4. Usage

Always activate the virtual environment first:
```bash
source .venv/bin/activate
```

### 4.1 Interactive Mode

Run the script with no arguments:

```bash
python luma_sync.py
```

The script walks you through each step:

```
Event ID (evt-...) [evt-E7CYitIvydBWi0x]:
                                           ↑ press Enter to use the default

Fetching event evt-E7CYitIvydBWi0x...
  Event: Inference Starts Here: Open Inference. Real Impact. One day.
  Date:  2026-04-25T13:30:00.000Z

Proceed? [Y/n]: y

Filter by status (approved/pending_approval/invited/declined/waitlist) or Enter for all:

Write to (e)xisting sheet or (n)ew sheet? [n]: n

Mode — (r)eplace or (a)ppend? [r]: r

Fetching guests...
  Found 29 guest(s).
Wrote 29 rows (replace mode).

Done! Sheet: https://docs.google.com/spreadsheets/d/...
```

### 4.2 Batch Mode

Pass `--event-id` to skip prompts and run non-interactively:

```bash
# Full refresh — create a new sheet
python luma_sync.py --event-id evt-E7CYitIvydBWi0x

# Full refresh — overwrite an existing sheet
python luma_sync.py --event-id evt-E7CYitIvydBWi0x --sheet-id 1aBcDeFgHiJkLmNoPqRsTuVwXyZ

# Incremental update — only add new registrations
python luma_sync.py --event-id evt-E7CYitIvydBWi0x --sheet-id 1aBcDeFgHiJkLmNoPqRsTuVwXyZ --mode append

# Only approved guests
python luma_sync.py --event-id evt-E7CYitIvydBWi0x --status approved
```

Batch mode is suitable for cron jobs and automation. It exits with code 0 on success, 1 on error.

### 4.3 CLI Reference

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--event-id` | No* | — | Luma event ID (`evt-...`). If omitted, launches interactive mode. |
| `--api-key` | No | `LUMA_API_KEY` env | Luma API key. Falls back to `.env` / environment variable. |
| `--sheet-id` | No | — | Google Sheet ID of an existing spreadsheet. If omitted, a new sheet is created. |
| `--mode` | No | `replace` | `replace` clears the sheet and writes all data. `append` only adds guests not already present. |
| `--status` | No | all | Filter by guest approval status: `approved`, `pending_approval`, `invited`, `declined`, `waitlist`. |

*If `--event-id` is omitted, the script enters interactive mode and prompts for all inputs.

**Finding a Google Sheet ID:**
The Sheet ID is the long string in the spreadsheet URL between `/d/` and `/edit`:
```
https://docs.google.com/spreadsheets/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                       This is the Sheet ID
```

**Finding a Luma Event ID:**
The event ID appears in the Luma event URL, or you can find it in the Luma dashboard. It always starts with `evt-`.

## 5. Spreadsheet Output

The script writes to a tab named **"Luma Registrations"** within the target spreadsheet. If the tab does not exist, it is created automatically.

### 5.1 Fixed Columns

These columns are always present, regardless of the event's registration form:

| Column | Description |
|--------|-------------|
| **Name** | Guest's full name |
| **Email** | Guest's email address |
| **Status** | Approval status (`approved`, `pending_approval`, `invited`, `declined`, `waitlist`) |
| **Registered At** | ISO 8601 timestamp of when the guest registered |
| **Checked In At** | ISO 8601 timestamp of check-in (empty if not checked in) |
| **Ticket Type** | Name of the ticket type (e.g., "Standard", "VIP") |
| **Company** | Company name from the registration form |
| **Job Title** | Job title from the registration form |
| **LinkedIn** | LinkedIn profile path |
| **GitHub** | GitHub username |
| **Check-in QR** | URL for the guest's check-in QR code |

### 5.2 Dynamic Columns

Any custom questions on the event's registration form are automatically discovered and added as additional columns after the fixed ones. These are determined at runtime by scanning all guest registration answers.

For example, an event with custom questions might produce:

| ... | Which persona describes you best? | What Topics are you interested in? | What is your technical proficiency level? |
|-----|---|---|---|
| ... | Industry Professional | vLLM, LLM-d | Intermediate |
| ... | Student | RAG, LLM-d, vLLM, Vibe Coding | Intermediate |

Multi-select answers are joined with commas. Boolean values display as "Yes" / "No".

The dynamic columns will differ between events depending on each event's registration form.

### 5.3 Write Modes

**Replace mode** (`--mode replace`, the default):
- Clears the entire "Luma Registrations" tab
- Writes the header row and all guest data from scratch
- Use this for a clean, up-to-date snapshot

**Append mode** (`--mode append`):
- Reads existing rows from the sheet
- Compares emails to identify guests already in the sheet
- Only adds rows for new guests not already present
- Does not update or remove existing rows
- Use this for incremental updates between syncs

## 6. Examples

**Daily sync via cron (macOS launchd or crontab):**
```bash
# Run every day at 9am, replace all data
0 9 * * * cd ~/Documents/notes/Claude/Luma && .venv/bin/python luma_sync.py \
  --event-id evt-E7CYitIvydBWi0x \
  --sheet-id 1aBcDeFgHiJkLmNoPqRsTuVwXyZ \
  --mode replace
```

**Export only approved guests:**
```bash
python luma_sync.py --event-id evt-E7CYitIvydBWi0x --status approved
```

**Sync a different event:**
```bash
python luma_sync.py --event-id evt-AnotherEventId
```

**Override the API key for a different calendar:**
```bash
python luma_sync.py --event-id evt-XXX --api-key secret-DifferentKey
```

## 7. Troubleshooting

### Luma API errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Error: Luma API key required` | No API key provided | Set `LUMA_API_KEY` in `.env`, export it, or pass `--api-key` |
| `401 Unauthorized` | Invalid or expired API key | Verify the key in your Luma calendar settings. Ensure you have Luma Plus. |
| `403 Forbidden` | API key does not have access to this event | The event must belong to the calendar associated with your API key. |
| `404 Not Found` | Invalid event ID | Check the event ID format — it must start with `evt-`. Copy it from the Luma dashboard or event URL. |
| `429 Too Many Requests` | Rate limit exceeded | Wait a few minutes and retry. For automation, space runs at least 5 minutes apart. |

### Google Sheets errors

| Error | Cause | Fix |
|-------|-------|-----|
| `client_secret.json not found` | OAuth credentials file missing | Follow the [Google Sheets OAuth Setup](#32-google-sheets-oauth-setup) steps above. |
| `Access blocked: This app's request is invalid` | OAuth consent screen not configured | Complete the consent screen setup in Google Cloud Console. Make sure your email is added as a test user. |
| `RefreshError` or `Token has been expired or revoked` | Saved token is stale | Delete `credentials/token.json` and run the script again to re-authenticate. |
| `Insufficient Permission` | Token was created with narrower scopes | Delete `credentials/token.json` and re-authenticate. The script requests both Sheets and Drive scopes. |
| `Spreadsheet not found` | Wrong sheet ID or no access | Verify the `--sheet-id` value. Ensure the Google account used during OAuth has edit access to the sheet. |
| `APIError 429: Quota exceeded` | Google Sheets API rate limit | Wait 60 seconds and retry. Events with 1000+ guests may need throttling — open an issue if this occurs. |

### Python / environment errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'requests'` | Virtual environment not activated or deps not installed | Run `source .venv/bin/activate && pip install -r requirements.txt` |
| `externally-managed-environment` | Trying to pip install globally on macOS | Use the virtual environment: `source .venv/bin/activate` |
| `SyntaxError` on `str | None` | Python version too old | Requires Python 3.10+. Check with `python3 --version`. |

### Common questions

**Q: How do I sync multiple events?**
Run the script once per event with different `--event-id` values. Use different `--sheet-id` targets or omit it to create a separate sheet per event.

**Q: The sheet has too many columns / I don't need all the registration answers.**
The dynamic columns are auto-discovered from the event's form. To exclude specific columns, you can hide them in Google Sheets (right-click column header > Hide column). The script currently exports all available data.

**Q: Append mode says "0 new rows" but I know there are new registrations.**
Append mode deduplicates by email address. If the new guests registered with an email already in the sheet, they will be skipped. Check for duplicate emails.

**Q: The browser didn't open for Google login.**
The script calls `run_local_server(port=0)` which picks a random port. If running over SSH or headless, you'll need to copy the authorization URL from the terminal to a local browser, complete the login, and paste the redirect URL back.

**Q: Can I use a service account instead of OAuth?**
Not with the current script. To add service account support, replace `get_gspread_client()` with `gspread.service_account(filename='path/to/key.json')` and share the target sheet with the service account email.

### Resetting authentication

If you encounter persistent Google auth issues:
```bash
# Remove the cached token to force re-authentication
rm credentials/token.json

# Run the script — browser will open for login
python luma_sync.py
```

### File layout reference

```
Luma/
  luma_sync.py            # Main script
  requirements.txt        # Python dependencies
  .env                    # Your API key + defaults (git-ignored)
  .env.example            # Template for .env
  .gitignore              # Keeps secrets out of git
  credentials/
    client_secret.json    # Google OAuth credentials (git-ignored)
    token.json            # Cached auth token (git-ignored, auto-generated)
  .venv/                  # Python virtual environment
```
