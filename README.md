# Luma2GSheetShuttle

Sync event registration data from [Luma](https://lu.ma) to Google Sheets with a single command.

Pull guest names, emails, approval status, ticket info, company, LinkedIn, GitHub, and all custom registration form answers into a structured spreadsheet -- automatically.

## Features

- **Interactive & batch modes** -- guided prompts or fully scriptable CLI
- **Replace or append** -- full refresh or incremental updates that deduplicate by email
- **Dynamic columns** -- custom registration questions are auto-discovered and added as columns
- **Google Sheets OAuth** -- browser-based login with cached tokens for unattended re-runs
- **Pagination** -- automatically fetches all guests, regardless of event size
- **Status filtering** -- export only approved, pending, waitlisted, or declined guests

## Quick Start

```bash
git clone https://github.com/holzerjm/Luma2GSheetShuttle.git
cd Luma2GSheetShuttle

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your Luma API key
```

Set up Google Sheets OAuth credentials (one-time): see [Google Sheets OAuth Setup](USER_GUIDE.md#32-google-sheets-oauth-setup) in the User Guide.

Then run:

```bash
# Interactive -- prompts for event, sheet target, and mode
python luma_sync.py

# Batch -- create a new sheet with all guests
python luma_sync.py --event-id evt-YourEventId

# Batch -- update an existing sheet, append new guests only
python luma_sync.py --event-id evt-YourEventId --sheet-id YOUR_SHEET_ID --mode append
```

## Requirements

- Python 3.10+
- [Luma Plus subscription](https://lu.ma) (required for API access)
- Google Cloud project with Sheets API + Drive API enabled

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--event-id` | -- | Luma event ID (`evt-...`). Omit to enter interactive mode. |
| `--api-key` | `LUMA_API_KEY` env | Luma API key. Falls back to `.env`. |
| `--sheet-id` | -- | Existing Google Sheet ID. Omit to create a new sheet. |
| `--mode` | `replace` | `replace` overwrites the sheet. `append` adds only new guests. |
| `--status` | all | Filter: `approved`, `pending_approval`, `invited`, `declined`, `waitlist`. |

## Spreadsheet Output

Data is written to a **"Luma Registrations"** tab (created automatically if missing).

**Fixed columns** (always present):

| Name | Email | Status | Registered At | Checked In At | Ticket Type | Company | Job Title | LinkedIn | GitHub | Check-in QR |
|------|-------|--------|---------------|---------------|-------------|---------|-----------|----------|--------|-------------|

**Dynamic columns** are appended for each custom question on the event's registration form (persona type, topics of interest, proficiency level, free-text responses, etc.). Multi-select answers are comma-separated.

## Configuration

| Setting | Source | Notes |
|---------|--------|-------|
| Luma API key | `.env`, env var, or `--api-key` | Starts with `secret-`. Found in your Luma calendar settings. |
| Default event ID | `LUMA_DEFAULT_EVENT_ID` in `.env` | Used as the default in interactive mode. |
| Google OAuth credentials | `credentials/client_secret.json` | Downloaded from Google Cloud Console. |

See [`.env.example`](.env.example) for the template.

## Project Structure

```
Luma2GSheetShuttle/
  luma_sync.py              # Main script
  requirements.txt          # Python dependencies
  .env.example              # Environment variable template
  .gitignore                # Protects secrets from being committed
  USER_GUIDE.md             # Full user guide with setup, usage, and troubleshooting
  credentials/
    client_secret.json      # Google OAuth credentials (git-ignored)
    token.json              # Cached auth token (git-ignored, auto-generated)
```

## Documentation

The full **[User Guide](USER_GUIDE.md)** covers:

- Step-by-step Google Cloud OAuth setup
- Interactive and batch mode walkthroughs
- Cron job / automation examples
- Troubleshooting tables for Luma API, Google Sheets, and Python environment errors
- FAQ

## License

MIT
