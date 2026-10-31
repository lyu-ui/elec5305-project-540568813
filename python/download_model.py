"""Optional: fetch the exact released checkpoint; verifies bytes before use."""
from pathlib import Path
import urllib.request,hashlib
root=Path(__file__).resolve().parent
url='https://huggingface.co/bpiyush/sound-of-water-models/resolve/main/dsr9mf13_ep100_step12423_real_finetuned_with_cosupervision.pth'
expected='2fa3d8cec1488ee65bb5a6e30f1b79716d8243bbe4ddc4c0687ce2a02c84303c'
target=root/'checkpoint.pth'
if not target.exists():
    print('Downloading released model (about 378 MB)...',flush=True)
    urllib.request.urlretrieve(url,target)
actual=hashlib.sha256(target.read_bytes()).hexdigest()
if actual!=expected:raise RuntimeError('Checkpoint hash mismatch; do not run inference with this file.')
print('Checkpoint verified:',target)
