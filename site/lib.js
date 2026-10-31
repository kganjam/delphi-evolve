/* Pure functions for the TrpB landscape view. No DOM access, so Node can test them.
 *
 * Everything here operates on the REAL replicate measurements packed by
 * `python -m evolve.evidence landscape` (site/data/landscape.js).
 *
 * Edge rule (the same dominance condition the Lean certificate is about):
 *   a step v -> w is ACCEPTED iff  L(w) >= U(v)
 * where, with assumed per-measurement error bound eps,
 *   readnoise mode: L = mean - e, U = mean + e with e = ceil(kappa*sd_bin/2*1e6)/1e6, sd_bin the
 *                   core worker's declared replicate-difference SD for the read-count bin;
 *                   the slider value is kappa (assumed sensitivity multiplier).
 *   envelope mode:  L = min(rep1, rep2) - eps,  U = max(rep1, rep2) + eps
 *   point mode:     L = mean - eps,             U = mean + eps
 * eps / kappa is an ASSUMPTION chosen by the viewer, not an estimated confidence level.
 * An edge touching an unmeasured genotype is UNKNOWN, never accepted or rejected.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.TrpbLib = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const AA = "ACDEFGHIKLMNPQRSTVWY";
  const N = 160000;
  const W = [8000, 400, 20, 1];
  const MISSING = -32768;
  const SCALE = 50000; // landscape.js stores score x 50000 in int16
  const SD = [0.014953, 0.009995, 0.005851, 0.002992]; // core's declared noise model (see landscape.meta.json)
  const SD_EDGES = [20, 50, 200];
  const sdBin = (c) => (c >= SD_EDGES[2] ? 3 : c >= SD_EDGES[1] ? 2 : c >= SD_EDGES[0] ? 1 : 0);

  function b64ToBytes(s) {
    if (typeof atob === "function") {
      const bin = atob(s);
      const out = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
      return out;
    }
    return new Uint8Array(Buffer.from(s, "base64"));
  }

  function decode(pack) {
    const r1raw = new Int16Array(b64ToBytes(pack.r1).buffer);
    const r2raw = new Int16Array(b64ToBytes(pack.r2).buffer);
    const cnt = new Uint16Array(b64ToBytes(pack.cnt).buffer);
    const act = b64ToBytes(pack.act);
    const measured = new Uint8Array(N);
    const mn = new Float32Array(N), mx = new Float32Array(N), mean = new Float32Array(N);
    const sd = new Float32Array(N), reads = new Uint16Array(N), active = new Uint8Array(N);
    for (let i = 0; i < N; i++) {
      if (r1raw[i] === MISSING || r2raw[i] === MISSING) {
        mn[i] = mx[i] = mean[i] = sd[i] = NaN;
        continue;
      }
      measured[i] = 1;
      const a = r1raw[i] / SCALE, b = r2raw[i] / SCALE;
      mn[i] = Math.min(a, b); mx[i] = Math.max(a, b); mean[i] = (a + b) / 2;
      reads[i] = cnt[i]; active[i] = act[i]; sd[i] = SD[sdBin(cnt[i])];
    }
    return { measured, mn, mx, mean, sd, reads, active, r1raw, r2raw, scale: SCALE, meta: pack.meta, unknown: pack.unknown };
  }

  const idxOf = (g) => {
    if (typeof g !== "string" || g.length !== 4) return -1;
    let i = 0;
    for (let p = 0; p < 4; p++) {
      const a = AA.indexOf(g[p].toUpperCase());
      if (a < 0) return -1;
      i += a * W[p];
    }
    return i;
  };
  const genoOf = (i) => {
    let s = "";
    for (let p = 0; p < 4; p++) s += AA[Math.floor(i / W[p]) % 20];
    return s;
  };
  const hamming = (a, b) => {
    let d = 0;
    for (let p = 0; p < 4; p++) if (Math.floor(a / W[p]) % 20 !== Math.floor(b / W[p]) % 20) d++;
    return d;
  };

  /* margin = L(w) - U(v) for parameter x (eps, or kappa in readnoise mode). Accepted iff >= 0. */
  const halfWidth = (D, i, x, mode) => (mode === "readnoise" ? Math.ceil((x * D.sd[i]) / 2 * 1e6) / 1e6 : x);
  function margin(D, v, w, x, mode) {
    if (!D.measured[v] || !D.measured[w]) return null;
    if (mode === "envelope") return D.mn[w] - x - (D.mx[v] + x);
    return D.mean[w] - halfWidth(D, w, x, mode) - (D.mean[v] + halfWidth(D, v, x, mode));
  }
  /* The largest parameter at which the edge is still accepted (widest-path capacity). */
  function edgeCap(D, v, w, mode) {
    if (!D.measured[v] || !D.measured[w]) return null;
    if (mode === "envelope") return (D.mn[w] - D.mx[v]) / 2;
    if (mode === "point") return (D.mean[w] - D.mean[v]) / 2;
    return (D.mean[w] - D.mean[v]) / ((D.sd[v] + D.sd[w]) / 2);
  }
  const edgeStatus = (D, v, w, eps, mode) => {
    const m = margin(D, v, w, eps, mode);
    return m === null ? "unknown" : m >= 0 ? "accepted" : "rejected";
  };

  /* BFS over single substitutions. Among shortest routes, prefer fewest unmeasured
   * genotypes, then the largest worst-step margin. allowUnknown=false is the
   * "measured-only" (pessimistic) graph; true adds every edge touching an unmeasured genotype. */
  function search(D, start, target, eps, mode, allowUnknown) {
    const dist = new Int16Array(N).fill(-1);
    const pred = new Int32Array(N).fill(-1);
    const bott = new Float32Array(N).fill(-Infinity);
    const unk = new Int16Array(N);
    const queue = new Int32Array(N);
    let qh = 0, qt = 0;
    dist[start] = 0; bott[start] = Infinity; unk[start] = D.measured[start] ? 0 : 1;
    queue[qt++] = start;
    while (qh < qt) {
      const v = queue[qh++];
      if (v === target) break;
      for (let p = 0; p < 4; p++) {
        const cur = Math.floor(v / W[p]) % 20;
        const baseIdx = v - cur * W[p];
        for (let a = 0; a < 20; a++) {
          if (a === cur) continue;
          const w = baseIdx + a * W[p];
          const m = margin(D, v, w, eps, mode);
          let ok, mm;
          if (m === null) { ok = allowUnknown; mm = Infinity; } else { ok = m >= 0; mm = m; }
          if (!ok) continue;
          const nu = unk[v] + (D.measured[w] ? 0 : 1);
          const nb = Math.min(bott[v], mm);
          if (dist[w] === -1) {
            dist[w] = dist[v] + 1; pred[w] = v; unk[w] = nu; bott[w] = nb; queue[qt++] = w;
          } else if (dist[w] === dist[v] + 1 && (nu < unk[w] || (nu === unk[w] && nb > bott[w]))) {
            pred[w] = v; unk[w] = nu; bott[w] = nb;
          }
        }
      }
    }
    const found = dist[target] !== -1;
    let route = null;
    if (found) {
      route = [];
      for (let v = target; v !== -1; v = pred[v]) route.push(v);
      route.reverse();
    }
    return { found, route, dist, reached: qt, queueOrder: queue.subarray(0, qt) };
  }

  /* Largest eps for which a measured-only route exists: max over routes of min over
   * steps of the per-edge capacity (widest path; exact up to read-count ceil rounding, independent of the slider). */
  function maxEps(D, start, target, mode) {
    if (!D.measured[start] || !D.measured[target]) return null;
    const width = new Float32Array(N).fill(-Infinity);
    const done = new Uint8Array(N);
    // binary max-heap of [width, node]
    const hw = [], hn = [];
    const push = (w, n) => {
      let i = hw.length; hw.push(w); hn.push(n);
      while (i > 0) {
        const p = (i - 1) >> 1;
        if (hw[p] >= hw[i]) break;
        [hw[p], hw[i]] = [hw[i], hw[p]]; [hn[p], hn[i]] = [hn[i], hn[p]]; i = p;
      }
    };
    const pop = () => {
      const w = hw[0], n = hn[0];
      const lw = hw.pop(), ln = hn.pop();
      if (hw.length) {
        hw[0] = lw; hn[0] = ln;
        let i = 0;
        for (;;) {
          let l = 2 * i + 1, r = l + 1, m = i;
          if (l < hw.length && hw[l] > hw[m]) m = l;
          if (r < hw.length && hw[r] > hw[m]) m = r;
          if (m === i) break;
          [hw[m], hw[i]] = [hw[i], hw[m]]; [hn[m], hn[i]] = [hn[i], hn[m]]; i = m;
        }
      }
      return [w, n];
    };
    width[start] = Infinity; push(Infinity, start);
    while (hw.length) {
      const [wd, v] = pop();
      if (done[v]) continue;
      done[v] = 1;
      if (v === target) return wd;
      for (let p = 0; p < 4; p++) {
        const cur = Math.floor(v / W[p]) % 20;
        const baseIdx = v - cur * W[p];
        for (let a = 0; a < 20; a++) {
          if (a === cur) continue;
          const w = baseIdx + a * W[p];
          if (done[w]) continue;
          const cap = edgeCap(D, v, w, mode);
          if (cap === null) continue;
          const nw = Math.min(wd, cap);
          if (nw > width[w]) { width[w] = nw; push(nw, w); }
        }
      }
    }
    return -Infinity; // unreachable in the measured graph at any eps
  }

  /* All orderings of the substitutions separating start and target (<=24). */
  function directOrderings(D, start, target, eps, mode) {
    const diff = [];
    for (let p = 0; p < 4; p++) {
      const a = Math.floor(start / W[p]) % 20, b = Math.floor(target / W[p]) % 20;
      if (a !== b) diff.push([p, b]);
    }
    const out = [];
    const perm = (rest, cur, path) => {
      if (!rest.length) { out.push(path); return; }
      rest.forEach((s, k) => {
        const next = cur + (s[1] - (Math.floor(cur / W[s[0]]) % 20)) * W[s[0]];
        perm(rest.filter((_, j) => j !== k), next, path.concat([next]));
      });
    };
    perm(diff, start, [start]);
    return out.map((nodes) => {
      let worst = Infinity, accepted = true, unknown = false;
      for (let i = 0; i + 1 < nodes.length; i++) {
        const m = margin(D, nodes[i], nodes[i + 1], eps, mode);
        if (m === null) { unknown = true; continue; }
        if (m < worst) worst = m;
        if (m < 0) accepted = false;
      }
      return { nodes, worst: worst === Infinity ? null : worst, accepted: accepted && !unknown, unknown };
    });
  }

  /* Decision for (start,target,eps,mode). */
  function decide(D, start, target, eps, mode) {
    const pess = search(D, start, target, eps, mode, false);
    if (pess.found) return { status: "open", route: pess.route, reached: pess.reached };
    const opt = search(D, start, target, eps, mode, true);
    if (opt.found) {
      const unknownNodes = opt.route.filter((v) => !D.measured[v]);
      return { status: "undetermined", route: opt.route, unknownNodes, reached: opt.reached,
               measuredReached: pess.reached };
    }
    // blocked: closed set R (optimistic reachability) with no admissible outgoing edge.
    const R = new Uint8Array(N);
    for (let i = 0; i < opt.reached; i++) R[opt.queueOrder[i]] = 1;
    let boundary = 0, nearest = null;
    for (let i = 0; i < opt.reached; i++) {
      const v = opt.queueOrder[i];
      for (let p = 0; p < 4; p++) {
        const cur = Math.floor(v / W[p]) % 20;
        const baseIdx = v - cur * W[p];
        for (let a = 0; a < 20; a++) {
          if (a === cur) continue;
          const w = baseIdx + a * W[p];
          if (R[w]) continue;
          boundary++;
          const m = margin(D, v, w, eps, mode);
          if (m !== null && (nearest === null || m > nearest.margin)) nearest = { from: v, to: w, margin: m };
        }
      }
    }
    return { status: "blocked", closedSetSize: opt.reached, boundaryEdges: boundary, nearest };
  }

  /* Unmeasured genotypes adjacent to the measured-reachable set, nearest the target first.
   * A heuristic ordering for "which assay next", NOT a computed value of information. */
  function assayCandidates(D, start, target, eps, mode, limit) {
    const s = search(D, start, -1, eps, mode, false); // target -1: explore the whole reachable set
    const seen = new Set(), out = [];
    for (let i = 0; i < s.reached; i++) {
      const v = s.queueOrder[i];
      for (let p = 0; p < 4; p++) {
        const cur = Math.floor(v / W[p]) % 20;
        const baseIdx = v - cur * W[p];
        for (let a = 0; a < 20; a++) {
          if (a === cur) continue;
          const w = baseIdx + a * W[p];
          if (!D.measured[w] && !seen.has(w)) { seen.add(w); out.push({ node: w, via: v, d: hamming(w, target) }); }
        }
      }
    }
    out.sort((x, y) => x.d - y.d || x.node - y.node);
    return { total: out.length, top: out.slice(0, limit || 5), reachableMeasured: s.reached };
  }

  return { AA, N, W, halfWidth, SD, SD_EDGES, decode, idxOf, genoOf, hamming, margin, edgeCap, edgeStatus, search, maxEps,
           directOrderings, decide, assayCandidates };
});
