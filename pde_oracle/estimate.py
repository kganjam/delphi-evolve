"""Turn MEASURED pde_bench.json rates into wall-time estimates for a stated workload.

  python -m pde_oracle.estimate --cpu cpu.json [--gpu gpu.json] --integrations 384000 --N 128 --steps 20000 \
      --cpu-threads 24 --gpus 1
Every input is explicit; nothing is defaulted from memory. Uses the median measured cell-steps/s over models for the
requested precision, at the measured configuration closest in (N, B). Perfect linear CPU scaling and perfect GPU
batching are ASSUMED (flagged in output) unless a scaling measurement is passed; both are optimistic.
"""
import argparse, json, statistics


def rate(doc, device, prec, N, threads=None):
    rs = [r for r in doc["runs"] if r["device"] == device and r["prec"] == prec and r["N"] == N and r["B"] >= 16
          and (threads is None or r.get("threads") == threads)]
    if not rs:
        rs = [r for r in doc["runs"] if r["device"] == device and r["prec"] == prec and (threads is None or r.get("threads") == threads)]
    return statistics.median(r["cell_steps_per_s"] for r in rs), len(rs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpu", required=True); ap.add_argument("--gpu")
    ap.add_argument("--integrations", type=int, required=True); ap.add_argument("--N", type=int, required=True)
    ap.add_argument("--steps", type=int, required=True); ap.add_argument("--prec", default="f64")
    ap.add_argument("--cpu-threads", type=int, required=True); ap.add_argument("--gpus", type=int, default=1)
    a = ap.parse_args()
    work = a.integrations * a.N ** 2 * a.steps
    out = {"workload_cell_steps": work, "assumptions": ["linear CPU scaling to --cpu-threads (optimistic)", "GPU rate from batch >=16 measured config"]}
    c, n = rate(json.load(open(a.cpu)), "cpu", a.prec, a.N, 1)
    out["cpu_rate_per_thread"] = c; out["cpu_hours_at_threads"] = round(work / (c * a.cpu_threads) / 3600, 2)
    if a.gpu:
        g, n = rate(json.load(open(a.gpu)), "cuda", a.prec, a.N)
        out["gpu_rate_per_gpu"] = g; out["gpu_hours"] = round(work / (g * a.gpus) / 3600, 3)
        out["gpu_over_one_cpu_thread"] = round(g / c, 1)
    print(json.dumps(out, indent=1))


main()
