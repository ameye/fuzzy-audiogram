#!/usr/bin/env python3
"""Send manuscript PDF with figures as email attachment."""

import base64, json, os, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

HERMES_HOME = os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))
TOKEN_PATH = Path(HERMES_HOME) / 'google_token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

MANUSCRIPT_PDF = Path('/opt/data/fuzzy-audiogram/manuscript.pdf')
MANUSCRIPT_QMD = Path('/opt/data/fuzzy-audiogram/manuscript.qmd')
FIGS_DIR = Path('/opt/data/fuzzy-audiogram/figures')
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
msg['Subject'] = 'Fuzzy Audiogram Manuscript — With Figures (PDF)'

body = MIMEText("""Hi Sanyaolu,

Here is the updated manuscript PDF with all 7 figures embedded, plus the source files.

Attached:
1. manuscript.pdf — Full manuscript with figures (1.6 MB, 7 figures, 4 tables, 24 refs)
2. manuscript.qmd — Quarto source file for re-rendering
3. All 7 figures as high-resolution PNGs (300 DPI)

To re-render: quarto render manuscript.qmd --to pdf

Repository: https://github.com/ameye/fuzzy-audiogram

Best,
Hermes Agent
""")
msg.attach(body)

# Attach files
attachments = [
    (MANUSCRIPT_PDF, 'fuzzy_audiogram_manuscript_with_figures.pdf'),
    (MANUSCRIPT_QMD, 'fuzzy_audiogram_manuscript.qmd'),
]

# Also attach all 7 figures
for fig_path in sorted(FIGS_DIR.glob('*.png')):
    attachments.append((fig_path, f'figure_{fig_path.name}'))

for fpath, fname in attachments:
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
print(f"Files attached: {len(attachments)}")
