"""One-time setup: log into Garmin (handling MFA) and print a base64 tokenstore.

Run locally:  python ingest/save_token.py

Paste your MFA code when prompted, then copy the printed value into:
  - ingest/.env  ->  GARMIN_TOKENSTORE_B64=...   (for local runs)
  - GitHub repo secret GARMIN_TOKENSTORE_B64      (for the scheduled workflow)

The token is valid for roughly a year; re-run this when it expires.
"""
from __future__ import annotations

import getpass

from garminconnect import Garmin


def main() -> None:
    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")

    garmin = Garmin(email=email, password=password, return_on_mfa=True)
    result1, result2 = garmin.login()
    if result1 == "needs_mfa":
        mfa_code = input("MFA code (from your authenticator/email): ").strip()
        garmin.resume_login(result2, mfa_code)

    token_b64 = garmin.garth.dumps()
    print("\n=== GARMIN_TOKENSTORE_B64 — copy the single line below ===\n")
    print(token_b64)
    print("\n=== end ===")


if __name__ == "__main__":
    main()
