# MCGP Project Rules & Constraints

## Mandatory Git Upload Requirements

To maintain safety and protect user content:
1. **NO SCRAPED DATA UPLOAD**: Never stage, commit, or push any files under the `data/` folder (such as downloaded HTML files, full screenshots, PDF pages, parsed structured JSON files, SQLite `mcgp.db`, or progress status logs).
2. **NO CREDENTIAL UPLOAD**: Never upload any `.env` configuration files or any parameters carrying Vertex AI projects or Gemini API keys.
3. **PRESERVE ALL DATA DIRECTORY IGNORES**: The `data/` folder and `.env` credentials must remain permanently in `.gitignore` to prevent leaks.
