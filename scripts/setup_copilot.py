"""Generate persistent worker/encryption secrets without displaying them."""
import base64
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / '.runtime' / 'copilot.env'
target.parent.mkdir(exist_ok=True)
if target.exists():
    print('Existing copilot secrets preserved.')
else:
    with target.open('x', encoding='utf-8') as handle:
        handle.write('COPILOT_WORKER_KEY=' + secrets.token_urlsafe(48) + '\n')
        handle.write('AI_SECRET_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode() + '\n')
    target.chmod(0o600)
    print('Copilot secrets created. Restrict Windows file permissions to your account and back up securely.')

security_file = root / '.runtime' / 'api-security.env'
if not security_file.exists():
    existing = ''
    local_env = root / '.env.local'
    if local_env.exists():
        for line in local_env.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('JWT_SECRET='):
                existing = line.split('=',1)[1].strip().strip('\"\'')
    signing_key = existing if len(existing) >= 32 else secrets.token_urlsafe(48)
    with security_file.open('x', encoding='utf-8') as handle:
        handle.write('JWT_SECRET=' + signing_key + '\n')
    security_file.chmod(0o600)
    print('Strong API signing key configured; sessions signed with a previous weak key require sign-in again.')
