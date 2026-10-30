# Privacy

- **No network calls from the CLI.** `capradar` reads and writes local JSON/Markdown files only. A unit test fails if network modules appear in the package.
- **No telemetry.** Nothing is collected or sent anywhere by this package.
- **Discovery uses your assistant.** The Skill asks your AI assistant to search the public web. Those searches go through your assistant's own tools under its own terms. Search queries are built from your profile's jobs and stack, so keep `profile.md` free of anything you would not type into a search engine.
- **Your data stays in your workspace** (`./radar` by default): `profile.md`, `config.json`, `ledger.json`, `inbox/`, `reports/`. Add `radar/` to `.gitignore` if your profile is personal.
- **Never put secrets in the profile or ledger** (API keys, passwords, client names, private documents). The radar does not need them.
- **Nothing is installed or authorized.** The radar recommends; you decide. It never installs, enables, buys or connects anything.
