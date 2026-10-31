// usage: node sign.mjs <unsigned.trig> <private-key.pem> <out.trig> [display-name]
// Signs LOCALLY (trusty URI + RSA signature). There is deliberately no publish call in this file.
import { Nanopub, NpProfile } from "@nanopub/sign";
import fs from "node:fs";
const [, , inp, keyPath, out, name] = process.argv;
const rdf = fs.readFileSync(inp, "utf8");
const pem = fs.readFileSync(keyPath, "utf8");
const profile = new NpProfile(pem, undefined, name || "local-throwaway", undefined);
const np = new Nanopub(rdf).sign(profile);
fs.writeFileSync(out, np.rdf());
const info = np.info();
console.log(JSON.stringify({ trusty_uri: info.uri.value, algorithm: info.algo, signed_out: out }));
