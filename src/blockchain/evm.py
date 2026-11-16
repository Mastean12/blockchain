"""Level 2 Ganache adapter: deploy and exercise the AuditLog contract.

**Level 2 means a single-node local EVM.** It tests contract logic and measures gas and latency in a
simulated environment. It is not a distributed blockchain, and no result from it may be presented as
a public-network cost (``docs/threat_model/SECURITY_THREAT_MODEL.md`` §6.1, §6.4).

The adapter deliberately stores only hashes and integers on-chain. Strings (run ids, accountant ids)
are hashed before submission, so no free text reaches the ledger.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BUILD_PATH = Path(__file__).resolve().parents[2] / "build" / "AuditLog.json"


class GanacheError(RuntimeError):
    """Raised when the contract layer cannot be used."""


def _keccak_bytes32(value: str) -> bytes:
    """Hash an identifier to raw 32 bytes for a bytes32 argument."""
    from web3 import Web3

    return Web3.keccak(text=value)


@dataclass
class TxMeasurement:
    """One measured transaction."""

    event_type: str
    gas_used: int
    latency_ms: float
    block_number: int
    success: bool
    revert_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "gas_used": self.gas_used,
            "latency_ms": self.latency_ms,
            "block_number": self.block_number,
            "success": self.success,
            "revert_reason": self.revert_reason,
        }


@dataclass
class AuditContract:
    """Thin wrapper over the deployed AuditLog contract.

    The contract is intentionally used with **one authorised account** (the aggregator) and one
    unauthorised account, which is only used to prove that authorisation is enforced.
    """

    web3: Any
    contract: Any
    authorised: Any
    unauthorised: Any
    measurements: list[TxMeasurement] = field(default_factory=list)
    deployment: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ deploy
    @classmethod
    def deploy(cls, rpc_url: str = "http://127.0.0.1:8545", timeout_s: float = 30.0) -> "AuditContract":
        from web3 import Web3

        if not BUILD_PATH.is_file():
            raise GanacheError(
                f"Compiled contract not found at {BUILD_PATH}. Run tools/blockchain/compile.js first."
            )
        build = json.loads(BUILD_PATH.read_text(encoding="utf-8"))
        web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": timeout_s}))
        if not web3.is_connected():
            raise GanacheError(f"Cannot reach Ganache at {rpc_url}")

        accounts = web3.eth.accounts
        if len(accounts) < 2:
            raise GanacheError("Ganache must expose at least two accounts")
        authorised, unauthorised = accounts[0], accounts[1]

        factory = web3.eth.contract(abi=build["abi"], bytecode=build["bytecode"])
        started = time.perf_counter()
        tx_hash = factory.constructor().transact({"from": authorised})
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        deploy_ms = (time.perf_counter() - started) * 1000.0

        contract = web3.eth.contract(address=receipt.contractAddress, abi=build["abi"])
        instance = cls(
            web3=web3,
            contract=contract,
            authorised=authorised,
            unauthorised=unauthorised,
        )
        instance.deployment = {
            "address": receipt.contractAddress,
            "gas_used": int(receipt.gasUsed),
            "latency_ms": deploy_ms,
            "abi_sha256": __import__("hashlib").sha256(
                json.dumps(build["abi"], sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "solc_version": build["solcVersion"],
            "source_sha256": build["sourceSha256"],
            "bytecode_bytes": (len(build["bytecode"]) - 2) // 2,
        }
        return instance

    # ------------------------------------------------------------- submission
    def _send(self, event_type: str, fn_call: Any, sender: str) -> TxMeasurement:
        started = time.perf_counter()
        try:
            tx_hash = fn_call.transact({"from": sender})
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            latency = (time.perf_counter() - started) * 1000.0
            measurement = TxMeasurement(
                event_type=event_type,
                gas_used=int(receipt.gasUsed),
                latency_ms=latency,
                block_number=int(receipt.blockNumber),
                success=int(receipt.status) == 1,
            )
            self.measurements.append(measurement)
            return measurement
        except Exception as error:  # noqa: BLE001 - revert reasons are part of the measurement
            latency = (time.perf_counter() - started) * 1000.0
            reason = self._extract_reason(error)
            measurement = TxMeasurement(
                event_type=event_type,
                gas_used=0,
                latency_ms=latency,
                block_number=-1,
                success=False,
                revert_reason=reason,
            )
            self.measurements.append(measurement)
            return measurement

    def _extract_reason(self, error: Exception) -> str:
        text = str(error)
        if "AuditLog:" in text:
            start = text.find("AuditLog:")
            return text[start:start + 80].split("'")[0].strip()
        if "revert" in text.lower():
            return "reverted (reason not exposed by node)"
        return type(error).__name__

    # ---------------------------------------------------------------- events
    def register_run(self, run_id: str, config_hash: str, split_hash: str,
                     client_manifest_hash: str, *, sender: str | None = None) -> TxMeasurement:
        call = self.contract.functions.registerRun(
            _keccak_bytes32(run_id),
            bytes.fromhex(config_hash),
            bytes.fromhex(split_hash),
            bytes.fromhex(client_manifest_hash),
        )
        return self._send("RunRegistered", call, sender or self.authorised)

    def open_round(self, run_id: str, round_index: int, participant_set_hash: str,
                   *, sender: str | None = None) -> TxMeasurement:
        call = self.contract.functions.openRound(
            _keccak_bytes32(run_id), int(round_index), bytes.fromhex(participant_set_hash)
        )
        return self._send("RoundOpened", call, sender or self.authorised)

    def commit_update(self, run_id: str, round_index: int, client_id: str,
                      update_hash: str, update_bytes: int,
                      *, sender: str | None = None) -> TxMeasurement:
        call = self.contract.functions.commitUpdate(
            _keccak_bytes32(run_id),
            int(round_index),
            _keccak_bytes32(client_id),
            bytes.fromhex(update_hash),
            int(update_bytes),
        )
        return self._send("UpdateCommitted", call, sender or self.authorised)

    def close_round(self, run_id: str, round_index: int, global_model_hash: str,
                    aggregation_rule_id: str, *, sender: str | None = None) -> TxMeasurement:
        call = self.contract.functions.closeRound(
            _keccak_bytes32(run_id),
            int(round_index),
            bytes.fromhex(global_model_hash),
            _keccak_bytes32(aggregation_rule_id),
        )
        return self._send("RoundClosed", call, sender or self.authorised)

    def report_missing(self, run_id: str, round_index: int, expected_set_hash: str,
                       *, sender: str | None = None) -> TxMeasurement:
        call = self.contract.functions.reportMissingCommitment(
            _keccak_bytes32(run_id), int(round_index), bytes.fromhex(expected_set_hash)
        )
        return self._send("MissingCommitment", call, sender or self.authorised)

    def seal_checkpoint(self, run_id: str, selected_round: int, checkpoint_hash: str,
                        *, sender: str | None = None) -> TxMeasurement:
        call = self.contract.functions.sealCheckpoint(
            _keccak_bytes32(run_id), int(selected_round), bytes.fromhex(checkpoint_hash)
        )
        return self._send("CheckpointSealed", call, sender or self.authorised)

    def attest_privacy(self, run_id: str, epsilon_scaled: int, delta_scaled: int,
                       sigma_scaled: int, clip_scaled: int, accountant_id: str,
                       *, sender: str | None = None) -> TxMeasurement:
        call = self.contract.functions.attestPrivacy(
            _keccak_bytes32(run_id),
            int(epsilon_scaled),
            int(delta_scaled),
            int(sigma_scaled),
            int(clip_scaled),
            _keccak_bytes32(accountant_id),
        )
        return self._send("PrivacyAttested", call, sender or self.authorised)

    # ----------------------------------------------------------------- reads
    @staticmethod
    def run_key(run_id: str) -> bytes:
        """The contract's round key for a run id, exposed for read-path tests."""
        return _keccak_bytes32(run_id)

    def read_round_count(self, run_id: str, round_index: int) -> int:
        return int(
            self.contract.functions.roundCommitCount(
                self.contract.functions.roundKey(_keccak_bytes32(run_id), int(round_index)).call()
            ).call()
        )

    def read_run(self, run_id: str) -> dict[str, Any]:
        result = self.contract.functions.verifyRun(_keccak_bytes32(run_id)).call()
        return {
            "registered": bool(result[0]),
            "config_hash": result[1].hex(),
            "split_hash": result[2].hex(),
            "client_manifest_hash": result[3].hex(),
            "checkpoint_hash": result[4].hex(),
            "selected_round": int(result[5]),
            "privacy_attested": bool(result[6]),
        }

    def measurement_table(self) -> list[dict[str, Any]]:
        return [m.as_dict() for m in self.measurements]
