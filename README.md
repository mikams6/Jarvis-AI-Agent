# Jarvis AI Agent

## Google Calendar credentials

Keep the Google OAuth client JSON outside this repository. Save it as:

`%LOCALAPPDATA%\Jarvis\google_calendar_client.json`

Jarvis stores the OAuth token and other local app data in the same private
`%LOCALAPPDATA%\Jarvis` directory. Do not commit OAuth client files, tokens,
or other credentials to GitHub.

If an older copy of `google_calendar_client.json` is in the project folder,
Jarvis moves it to the private app-data directory the next time Google
Calendar is used.
