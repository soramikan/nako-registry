#!/usr/bin/env node
// ID-07: node-semver 7.7.4 の API を一度の実行で照合する。
// 依存の導入・起動・版の不一致は exit 2、判定結果の不一致は exit 1。
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

let semver;
let version;
try {
  semver = require("semver");
  version = require("semver/package.json").version;
} catch (error) {
  console.error(`FAIL ID-07 dependency: ${error.message}`);
  process.exit(2);
}

if (version !== "7.7.4") {
  console.error(`FAIL ID-07 dependency: semver ${String(version)} is not 7.7.4`);
  process.exit(2);
}

let first;
let second;
try {
  // fixture/v1/conformance.md ID-07 と同じ範囲と版。loose と includePrerelease は既定どおり無効。
  first = semver.satisfies("1.9.0", "^1.2.3", {
    loose: false,
    includePrerelease: false,
  });
  second = semver.satisfies("2.0.0-alpha.2", "^1.2.3 >=2.0.0-alpha.1", {
    loose: false,
    includePrerelease: false,
  });
} catch (error) {
  console.error(`FAIL ID-07 evaluation: ${error.message}`);
  process.exit(2);
}

console.log(`ID-07 semver=${version} first=${String(first)} second=${String(second)}`);
if (first !== true || second !== false) {
  console.error("FAIL ID-07 result: expected first=true and second=false");
  process.exit(1);
}
console.log("PASS ID-07 1.9.0 satisfies ^1.2.3");
console.log("PASS ID-07 2.0.0-alpha.2 rejected by ^1.2.3 >=2.0.0-alpha.1 (caret upper bound)");
