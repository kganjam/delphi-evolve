// usage: node check.mjs <signed.trig>   -> exit 0 with JSON if trusty hash + signature verify, else exit 1
import { Nanopub } from "@nanopub/sign";
import fs from "node:fs";
try {
  const np = new Nanopub(fs.readFileSync(process.argv[2], "utf8")).check();
  const i = np.info();
  console.log(JSON.stringify({ ok: true, trusty_uri: i.uri.value, algorithm: i.algo, signer_orcid: i.orcid || null }));
} catch (e) {
  console.log(JSON.stringify({ ok: false, error: String(e).slice(0, 300) }));
  process.exit(1);
}
