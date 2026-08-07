# Privacy

Codex Handoff runs locally and does not operate a project-owned backend. When Google Drive is selected, the application synchronizes selected encrypted snapshots directly through the user's Google Drive and Google's API. Project maintainers do not receive or store user snapshots, OAuth tokens, analytics, or telemetry.

The default profile excludes authentication tokens, caches, locks, temporary files, sockets, and active SQLite journal files. Snapshot contents are encrypted locally with AES-256-GCM before upload. The recovery key remains on user devices and is never sent to Google Drive. Object names and limited metadata, including version identifiers and device names, remain visible to Google Drive.
