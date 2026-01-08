# Configuration (Reference)

## `.env` loading

The `kalshi` CLI loads a `.env` file automatically on invocation (it searches upward from the current directory).

This is intended for local development and running authenticated commands without manual `export ...`.

## Public vs authenticated features

- **Public (no credentials):** data sync, snapshots, market lookup, scans, alerts, analysis (DB-backed).
- **Authenticated:** portfolio commands (`portfolio balance`, `portfolio sync`, etc.) and authenticated integration
  tests.

## Environment variables

### Required (authenticated)

- `KALSHI_KEY_ID` — your Kalshi key id
- `KALSHI_PRIVATE_KEY_PATH` — path to your private key file
  - OR `KALSHI_PRIVATE_KEY_B64` — base64-encoded private key

### Optional

- `KALSHI_ENVIRONMENT` — `demo` or `prod` (default: `prod`)
  - You can also pass `kalshi --env demo ...` / `kalshi -e demo ...` to override.

### Tests only

- `KALSHI_RUN_LIVE_API=1` — enables live API integration tests in `tests/integration/`.

## Example `.env`

```bash
# The CLI defaults to `prod` if this is unset. For safer experimentation, use `demo`.
KALSHI_ENVIRONMENT=demo
KALSHI_KEY_ID=your_key_id_here
KALSHI_PRIVATE_KEY_PATH=/absolute/path/to/kalshi-private-key.pem
# OR:
# KALSHI_PRIVATE_KEY_B64=base64_encoded_private_key_material
```
