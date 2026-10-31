"""Validation payload: proves a shipped Python file ran on the GPU and returned bytes through the job log."""
import json, os, subprocess, time, hashlib
import numpy as np, torch
out = os.environ["COPS_OUT"]
info = {"torch": torch.__version__, "cuda": torch.version.cuda, "cuda_available": torch.cuda.is_available()}
if torch.cuda.is_available():
    info["device"] = torch.cuda.get_device_name(0)
    info["mem_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)
    x = torch.randn(8192, 8192, device="cuda", dtype=torch.bfloat16)
    torch.cuda.synchronize(); t = time.time()
    for _ in range(20): y = x @ x
    torch.cuda.synchronize(); dt = time.time() - t
    info["bf16_matmul_tflops"] = round(20 * 2 * 8192**3 / dt / 1e12, 1)
    info["checksum_of_deterministic_check"] = float((torch.arange(1000, device="cuda", dtype=torch.float64) ** 2).sum())  # 332833500.0
info["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                                    capture_output=True, text=True).stdout.strip()
rng = np.random.default_rng(7)
blob = rng.integers(0, 256, 150_000, dtype=np.uint8)           # incompressible payload: tests the return channel size
(open(os.path.join(out, "payload.bin"), "wb")).write(blob.tobytes())
info["payload_sha256"] = hashlib.sha256(blob.tobytes()).hexdigest()
json.dump(info, open(os.path.join(out, "probe.json"), "w"), indent=1)
print(json.dumps(info))
