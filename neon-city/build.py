"""Reconstruct the exact self-contained game and verify its integrity."""
from pathlib import Path
import base64
import gzip
import hashlib

root = Path(__file__).resolve().parent
parts = [(root / f'game-{i}.txt').read_text(encoding='utf-8').strip() for i in range(3)]
parts[0] = parts[0].replace('EOPSXJJXdRP', 'EOPSXJXdRP')
expected = ['0407e08c34c3ade4477d7a72d104fc00e6198c1f', '4948f0c6a33cf18ed14d567fa43679e0170a0773', '0f8767c3da1b0919f4a1e11d58381a09d3132cbc']
for i, part in enumerate(parts):
    data = part.encode('utf-8')
    digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if digest != expected[i]:
        raise ValueError(f'Payload {i} failed integrity verification: {digest}')
html = gzip.decompress(base64.b64decode(''.join(parts), validate=True))
sha256 = hashlib.sha256(html).hexdigest()
if len(html) != 91113 or sha256 != '001db22e807891e80a607f8a8ff623cda7784c93288481c7b1920eadcec61288':
    raise ValueError(f'Game integrity verification failed: {len(html)} bytes, {sha256}')
(root / 'index.html').write_bytes(html)
print(f'PASS: standalone game reconstructed, {len(html)} bytes, SHA256 {sha256}')
