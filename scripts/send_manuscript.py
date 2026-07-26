#!/usr/bin/env python3
"""Send manuscript.qmd as an email attachment via Gmail API."""

import base64, json, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

# Add skill scripts to path
SKILL_SCRIPTS = str(Path.home() / '.hermes' / 'skills' / 'productivity' / 'google-workspace' / 'scripts')
sys.path.insert(0, SKILL_SCRIPTS)

# Use HERMES_HOME for token path
import os
HERMES_HOME = os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))
TOKEN_PATH = Path(HERMES_HOME) / 'google_token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
MANUSCRIPT_PATH = Path('/opt/data/fuzzy-audiogram/manuscript.qmd')
REFERENCES_PATH = Path('/opt/data/fuzzy-audiogram/references.bib')
RECIPIENT = 'sanyaameye@hotmail.com'

# Load credentials
creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    TOKEN_PATH.write_text(json.dumps(
        {"type": "authorized_user", **json.loads(creds.to_json())},
        indent=2
    ))

# Build MIME message
msg = MIMEMultipart('mixed')
msg['To'] = RECIPIENT
msg['Subject'] = 'Fuzzy Audiogram Manuscript + References'

# Body
body = MIMEText("""Hi Sanyaolu,

Here is the full manuscript for the Fuzzy Audiogram project as requested.

Attached:
1. manuscript.qmd — Full manuscript (~6,250 words, Quarto format)
2. references.bib — 24 real PubMed-indexed references (BibTeX)

To render to PDF: quarto render manuscript.qmd --to pdf
To render to DOCX: quarto render manuscript.qmd --to docx

Repository: https://github.com/ameye/fuzzy-audiogram

Best,
Hermes Agent
""")
msg.attach(body)

# Attach manuscript
for fpath, fname in [
    (MANUSCRIPT_PATH, 'fuzzy_audiogram_manuscript.qmd'),
    (REFERENCES_PATH, 'references.bib'),
]:
    if not fpath.exists():
        print(f"Warning: {fpath} not found, skipping")
        continue
    with open(fpath, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{fname}"')
        msg.attach(part)

# Send
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
service = build('gmail', 'v1', credentials=creds)
result = service.users().messages().send(userId='me', body={'raw': raw}).execute()

print(f"Sent! ID: {result['id']}, Thread: {result['threadId']}")
