# Privacy

Codex Handoff runs locally and does not operate a project-owned backend. When Google Drive is selected, the application synchronizes selected encrypted snapshots directly through the user's Google Drive and Google's API. Project maintainers do not receive or store user snapshots, OAuth tokens, analytics, or telemetry.

The default profile excludes authentication tokens, caches, locks, temporary files, sockets, and active SQLite journal files. Snapshot contents are encrypted locally with AES-256-GCM before upload. The recovery key remains on user devices and is never sent to Google Drive. Object names and limited metadata, including version identifiers and device names, remain visible to Google Drive.

When background monitoring is enabled, Codex Handoff runs in the current user's tray or menu bar and normally reads only the small remote `head.json` record every 60 seconds. Network failures use a 2, 5, and 15-minute retry schedule. The application does not run a project-owned service, collect analytics, or send telemetry to the maintainers.
