"""One-time setup: log into Garmin (handling MFA) and print a base64 token.

Run locally:  python ingest/save_token.py

Enter your MFA code if prompted, then copy the printed value into:
  - ingest/.env  ->  GARMIN_TOKENSTORE_B64=...   (for local runs)
  - GitHub repo secret GARMIN_TOKENSTORE_B64      (for the scheduled workflow)

The token is valid for roughly a year; re-run this when it expires.

Note: Garmin rate-limits login attempts by IP (HTTP 429). If you hit that, wait
15-60 minutes before trying again rather than re-running repeatedly.
"""
from __future__ import annotations

import base64
import getpass

from garminconnect import Garmin


def prompt_mfa() -> str:
    return input("MFA code (from your authenticator/email): ").strip()


def main() -> None:
    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")

    # prompt_mfa is only invoked if the account has MFA enabled.
    garmin = Garmin(email=email, password=password, prompt_mfa=prompt_mfa)
    garmin.login()

    token_json = garmin.client.dumps()
    token_b64 = base64.b64encode(token_json.encode()).decode()

    print("\n=== GARMIN_TOKENSTORE_B64 — copy the single line below ===\n")
    print(token_b64)
    print("\n=== end ===")


if __name__ == "__main__":
    main()
