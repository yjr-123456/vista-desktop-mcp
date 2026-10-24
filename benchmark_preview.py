"""Compare preview encodings on one live frame; no input or persistent screenshots."""
import io
import json
import statistics
import time
from server import WindowsDesktop

image = WindowsDesktop().capture()
image.thumbnail((1600, 1600))
results = {}
for fmt in ("PNG", "JPEG"):
    samples = []
    for _ in range(7):
        output = io.BytesIO()
        start = time.perf_counter()
        image.save(output, format=fmt, **({"quality": 90, "subsampling": 0} if fmt == "JPEG" else {}))
        samples.append((time.perf_counter() - start) * 1000)
    results[fmt] = {"median_encode_ms": round(statistics.median(samples), 2), "bytes": len(output.getvalue())}
print(json.dumps(results, indent=2))
