# Security Policy

Please report vulnerabilities privately through GitHub Security Advisories for this repository. Do not include Codex state, OAuth tokens, snapshot contents, or other user data in a public issue.

Codex Handoff deliberately excludes authentication files and active database journals from its default profile. Snapshots may still contain sensitive conversations and project paths. Users should protect their Google account, local workspace, and exported archives accordingly.

Application updates are discovered through the public GitHub Releases API. The selected platform package must match the SHA-256 value published in the same release before installation can be offered. Download and installation each require explicit user confirmation. Checksums protect against download corruption; unsigned beta installers still rely on GitHub repository and release security until platform code signing is introduced.
