"""One-time: get the Google refresh token the scheduled run uses to read the sheets and write to Drive
as you (amitray@lawsikho.in). Run it on your own computer, never in CI.

1. Google Cloud console > APIs & Services: enable "Google Drive API" and "Google Sheets API".
2. Credentials > Create credentials > OAuth client ID > Desktop app. Download the JSON.
3. pip install google-auth-oauthlib
   python scripts/google_refresh_token.py path/to/client_secret.json
4. Sign in with amitray@lawsikho.in and allow access. Copy the three printed values into the
   repository's GitHub secrets (Settings > Secrets and variables > Actions).
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

if len(sys.argv) != 2:
    sys.exit(__doc__)
flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
cfg = json.load(open(sys.argv[1]))["installed"]
print("\nAdd these as GitHub secrets:\n")
print("GOOGLE_OAUTH_CLIENT_ID     =", cfg["client_id"])
print("GOOGLE_OAUTH_CLIENT_SECRET =", cfg["client_secret"])
print("GOOGLE_OAUTH_REFRESH_TOKEN =", creds.refresh_token)
