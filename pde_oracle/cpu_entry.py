"""CPU-job entry: install CPU torch, then run P concurrent single-thread bench processes to measure CPU scaling.
Env: CPU_PROCS (comma list, e.g. 1,8,31), plus PDE_* passed through. Output: $COPS_OUT/cpu_scaling.json"""
import json, os, subprocess, sys, time
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "torch", "--index-url", "https://download.pytorch.org/whl/cpu"], check=True)
out = {"nproc": os.cpu_count(), "scaling": {}}
env0 = dict(os.environ, PDE_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PDE_CONFIGS="128:16:f64", PDE_MODELS="schnakenberg,gray_scott")
for P in [int(x) for x in os.environ.get("CPU_PROCS", "1,8").split(",")]:
    d = f"{os.environ['COPS_OUT']}/p{P}"; os.makedirs(d, exist_ok=True)
    t = time.perf_counter()
    ps = [subprocess.Popen([sys.executable, "pde_oracle/bench.py"], env=dict(env0, COPS_OUT=d, PDE_OUTNAME=f"b{i}.json"), stdout=subprocess.DEVNULL) for i in range(P)]
    rc = [p.wait() for p in ps]
    runs = [json.load(open(f"{d}/b{i}.json")) for i in range(P)]
    agg = {}
    for m in ("schnakenberg", "gray_scott"):
        agg[m] = {"sum_cell_steps_per_s": sum(r["cell_steps_per_s"] for run in runs for r in run["runs"] if r["model"] == m),
                  "per_proc_mean": sum(r["cell_steps_per_s"] for run in runs for r in run["runs"] if r["model"] == m) / P}
    out["scaling"][str(P)] = {"wall_s": round(time.perf_counter() - t, 1), "rc": rc, **agg}
    print("scaling", P, json.dumps(out["scaling"][str(P)]), flush=True)
json.dump(out, open(f"{os.environ['COPS_OUT']}/cpu_scaling.json", "w"), indent=1)
