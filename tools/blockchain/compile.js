// Compile contracts/AuditLog.sol with the pinned solc and write ABI + bytecode.
const fs = require("fs");
const path = require("path");
const solc = require("solc");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "contracts", "AuditLog.sol");
const outDir = path.join(root, "build");
const source = fs.readFileSync(sourcePath, "utf8");

const input = {
  language: "Solidity",
  sources: { "AuditLog.sol": { content: source } },
  settings: {
    optimizer: { enabled: true, runs: 200 },
    outputSelection: { "*": { "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"] } },
  },
};

const output = JSON.parse(solc.compile(JSON.stringify(input)));
const errors = (output.errors || []).filter((e) => e.severity === "error");
if (errors.length) {
  for (const e of errors) console.error(e.formattedMessage);
  process.exit(1);
}
const warnings = (output.errors || []).filter((e) => e.severity === "warning");
for (const w of warnings) console.warn(w.formattedMessage);

const contract = output.contracts["AuditLog.sol"]["AuditLog"];
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(
  path.join(outDir, "AuditLog.json"),
  JSON.stringify(
    {
      contractName: "AuditLog",
      solcVersion: solc.version(),
      sourceSha256: require("crypto").createHash("sha256").update(source).digest("hex"),
      abi: contract.abi,
      bytecode: "0x" + contract.evm.bytecode.object,
      deployedBytecode: "0x" + contract.evm.deployedBytecode.object,
    },
    null,
    2
  )
);
console.log("compiled AuditLog.sol with solc", solc.version());
console.log("bytecode bytes:", contract.evm.bytecode.object.length / 2);
