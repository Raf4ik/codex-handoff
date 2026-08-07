# Codex Handoff Protocol

## Versioned State

The storage provider contains immutable version artifacts and a small mutable `head.json`. A version manifest records its parent version, source device, profile, and every synchronized file's size and SHA-256 digest. A version is uploaded and verified before `head.json` is updated to make it discoverable by other devices.

`head.json` only points to the latest published version. Clients never infer ownership from filesystem modification time.

## Device State

Each of the two paired devices keeps its own state outside the synced profile:

```json
{"device_id":"macbook","last_applied_version":"v...","baseline_id":"b..."}
```

Before pushing, the client compares the remote head with its `last_applied_version`. A newly configured device has no state file and cannot push. It must first apply the current head or restore the protected baseline. If the other paired device published a version since this device last pulled it, push stops with a stale-device error. The user must apply the current cloud update before publishing the next synchronization snapshot.

## Immutable Baseline

The first baseline is written once under `baseline/<baseline_id>/`. Creating a baseline when one already exists is an error. The encrypted baseline is cached in the application data directory on both paired devices after creation or first synchronization. Restore, pruning, and normal sync do not delete or alter baseline files. Re-baselining is a separate explicit operation that creates a new baseline ID and archives the old one.

## Apply and Restore

An apply operation first creates a local backup snapshot, writes files through a staging directory, verifies all digests, and only then updates the device state. A failed apply leaves the target untouched where possible and always leaves the pre-apply backup available.

## Portable Profiles

Profiles are allowlists, not a copy of the entire `.codex` directory. They may include sessions, skills, plugins, and rules. Authentication, cache, lock, socket, temporary, and active database journal files are excluded by default. Platform-specific paths are represented relative to the state root.

## Cloud Providers

The core depends on a narrow provider interface. The local filesystem provider is the reference implementation and test oracle. The Google Drive provider implements the same operations using OAuth and resumable uploads; no provider is allowed to weaken version immutability or stale-device checks.
