# Financial AI Bot

An automated, LLM-driven market‑dip scanner that posts daily commentary on Threads.

## 🚀 How It Works

- **Market Dip Detection:** Scans the S&P 500 for the biggest daily losers.
- **AI Commentary:** Uses Gemini to draft a concise, 2‑sentence post about the top dip.
- **Threads Publishing:** Publishes the post using Meta's Threads Graph API.

Runs automatically every day at 7:00 AM PST (14:00 UTC) **and** 1:30 PM PST (20:30 UTC) via GitHub Actions.

## 📦 Usage

All configuration is stored in your `.env` file. Copy `.env.example` to `.env` and fill in your keys:

```bash
# .env (add your values)
GEMINI_API_KEY="<your-gemini-key>"
THREADS_ACCESS_TOKEN="<threads-access-token>"
THREADS_USER_ID="<your-threads-user-id>"
```

## 🛠️ Setup (Manual Override)

The default schedule runs from the repo secrets `THREADS_ACCESS_TOKEN` and `THREADS_USER_ID`. You can override the user ID and toggle posting on/off via the GitHub Pages control panel (see **Web Control Panel** below) or manually trigger the workflow with different settings.

## ⚙️ GitHub Actions Overview

The main workflow lives at `.github/workflows/daily_post.yml`. It:

1. Triggers **on schedule** (`30 14 * * *` and `30 20 * * *`) **and** manually via `workflow_dispatch`.
2. Reads the on/off switch from `bot_config.json` (committed to the repo).
3. Overrides from `workflow_dispatch` inputs (`enabled` and `threads_user_id`) if provided.
4. Runs the `threads_poster.py` script to post to Threads.

## 🖥️ Web Control Panel

Visit the site at:

> https://edmundchan.github.io/financial-ai-bot

*(Once GitHub Pages is enabled for the `/docs` folder, the URL will reflect your actual username.)*

### What It Does

- **Toggle On/Off:** Switch posting on or off (saved to `bot_config.json`).
- **Threads User ID:** Provide a different numeric Threads user ID to post as (overrides the default secret).
- **Save & Run Now:** Persists the settings to the repository **and** immediately triggers a workflow run using the supplied values.
- **Check Last Run:** Fetches the status of the most recent workflow execution.

### How to Use

1. **GitHub Pages Setup** (one‑time):
   - In your repository Settings → Pages, select **Source** `GitHub Actions` → `gh-pages` branch (or `/docs` folder on `main`).
   - Wait a few minutes for the site to become accessible.

2. **GitHub Personal Access Token**:
   - Create a **Fine‑grained** token at: https://github.com/settings/tokens
   - Permissions needed: `Actions (read/write)` and `Contents (read/write)`
   - The token is **never** sent to a server; it is stored only in your browser’s localStorage.

3. **Control the Bot**:
   - Paste the token when prompted.
   - Flip the toggle to disable posting.
   - Enter a Threads user ID if you want the bot to post as a different account.
   - Click **Save & Run Now** – the settings are committed to the repo and a workflow is dispatched immediately.
   - Use **Check Last Run** to see the latest workflow status.

## 🔐 Secrets Configuration

In GitHub → Repository settings → Secrets and variables → Actions, add the following secrets:

- `GEMINI_API_KEY` – your Google Gemini API key
- `THREADS_ACCESS_TOKEN` – a Threads access token (see Meta docs for how to obtain)
- `THREADS_USER_ID` – the numeric Threads user ID that the bot will post as (default for scheduled runs)

## 📂 Files

- `.env` – environment variables (keep this out of version control via `.gitignore`)
- `.env.example` – template for required environment variables
- `config.py` – Pydantic settings manager that reads `.env`
- `trend_generator.py` – scans for top dips and uses Gemini to draft the post
- `threads_poster.py` – publishes a formatted post to Threads using the Meta Graph API
- `.github/workflows/daily_post.yml` – GitHub Actions schedule + manual workflow
- `bot_config.json` – committed on/off toggle and Threads user ID override (written by the web panel)
- `docs/` – GitHub Pages folder containing the control panel (`index.html`, `style.css`, `script.js`)
- `README.md` – this file
- `.gitignore` – standard Python/Node exclusions

## 📈 What the Bot Publishes

The bot picks the single best dip from the previous day’s market close and writes a post that includes:

- **ELI5 explanation** of why the dip looks attractive (valuation focus).
- **An open‑ended question** to spark discussion.
- **Total length ≤ 275 characters**.

Example output format:

```json
{
  "selected_ticker": "NVDA",
  "post_content": "NVDA is down 12% after earnings; trailing P/E ~45x vs 30x avg; does this create a buying opportunity for long‑term investors?"
}
```

## 🔧 Troubleshooting

- **Missing `.env` or invalid keys:** The app will log an error on first run and exit.
- **Threads API errors:** Ensure `THREADS_ACCESS_TOKEN` and `THREADS_USER_ID` are valid and the token has the necessary permissions.
- **GitHub Actions timeouts:** The workflow installs dependencies fresh each run; if network issues arise, you can manually retry the run from the GitHub UI.
- **Web Panel Can’t Save:** Check that your GitHub token has **Contents: Write** permission.

## 🏆 Contributing

Feel free to improve the code, add new data sources, or enhance the AI prompt. Open a pull request and let’s make this bot even smarter!
