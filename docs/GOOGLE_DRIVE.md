# Google Drive Setup

Codex Handoff uses the user's own Google Drive and requests the narrow `drive.file` OAuth scope. It can access only files created or explicitly opened by this application, not the user's entire Drive.

## Create OAuth Credentials

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable **Google Drive API** under **APIs & Services > Library**.
4. Configure the OAuth consent screen. For personal testing, choose **External** and add your Google account as a test user.
5. Create **OAuth client ID** credentials with application type **Desktop app**.
6. Download the JSON file to the local computer.

Do not commit this JSON file or the generated token to Git. In the GUI, select **Google Drive** and choose the downloaded JSON file. A browser opens on first connection. After approval, Codex Handoff stores the refresh token in the operating system's per-user configuration directory with restricted file permissions where supported.

## Recovery Key

On the first device, choose **Create new** next to **Recovery key**. Store an offline copy and select a copy of that same key on the second device. The key encrypts snapshots with AES-256-GCM before upload and is never sent to Google Drive. Losing it makes cloud snapshots unrecoverable; generating a different key on the second device will not work.

## Use Two Devices

Use OAuth credentials from the same Google Cloud project and sign in to the same Google account on both devices. The first device creates the app-owned `Codex Handoff` folder and protected baseline. The second device discovers the same folder through the same OAuth application identity.

## Publishing This Project

Repository maintainers should not publish a private OAuth client secret in source control. A desktop OAuth client identifier is distributed with many desktop applications, but public distribution still requires a deliberate Google consent-screen and verification strategy. Until that is configured, users can supply their own downloaded Desktop app JSON.

## Revocation

Access can be revoked at any time in the user's Google Account security settings. Removing the local token file forces a new OAuth flow. Revoking access does not delete snapshots already stored in Google Drive.
