# Phase 8 — Tier 1 Performance Optimisation Validation

**Date:** 17 November 2026
**Scope:** O1 (label-transfer fix), O3 (buffer caching), O2 (`cudnn.benchmark`) — implemented and
validated individually as required.
**Result:** **2 changes adopted (O1, O3); 1 rejected on evidence (O2).**
**Nothing committed. No confirmatory matrix re-run. No frozen result, seed, threshold, partition,
attack, aggregation rule or architecture touched.**

---

## 0. Summary

| Change | Adopted? | Numerically identical? | Measured effect |
|---|---|---|---|
| **O1** label `non_blocking` condition | **YES** | **Bit-identical** | **≈116 ms/round (1.9 %)**, measured over 566 batches |
| **O3** baseline buffer caching | **YES** | **Bit-identical** (delta max diff 0.0) | 3.59 → 2.74 ms/round (**0.011 %** of round) |
| **O2** `cudnn.benchmark = True` | **NO — rejected** | Identical hashes, but no speedup and structurally incompatible with determinism | 0 % (timings overlap) |

Combined steady-state measurement of the 5-client single-epoch round after O1+O3: **median
3,055 ms**, SD 111 ms, **CV 3.6 %**. Full 2-epoch round median: **6,099 ms**.

---

## 1. O1 — label-transfer condition

### 1.1 The defect

`scripts/run_phase5_a2_ablation.py`, in `train_local` (used by all Phase 8 runs):

```python
features = features.unsqueeze(1).to(device, non_blocking=device.type == "cuda")   # correct
labels   = labels.to(device,          non_blocking=labels.device.type == "cuda")  # BUG
```

`labels` is a CPU tensor, so `labels.device.type` is `"cpu"` and the expression is always `False`.
The **intent** was clearly to ask whether the *destination* is CUDA, so label copies were
unconditionally synchronous.

This was the only occurrence in the codebase (`src/federated/fedavg.py:134` was already correct).

### 1.2 The fix

```python
non_blocking = device.type == "cuda"
features = features.unsqueeze(1).to(device, non_blocking=non_blocking)
labels = labels.to(device, non_blocking=non_blocking)
```

The flag is computed once from the destination device and applied to both transfers. On a CPU
device it remains `False`, so **the CPU execution path is preserved exactly**.

### 1.3 Validation

| Check | Result |
|---|---|
| Per-client state hash vs pre-change (5 clients) | **All identical** |
| Per-client training loss vs pre-change | **All identical** |
| Validation macro-F1 | **0.252459252955** — identical to 12 decimal places |
| Per-class recall | **Identical** |
| 3-epoch state hash | **`5385a700c4fa4f318e559369…`** — identical |
| 3-epoch loss | **Identical** |
| Determinism across repeated runs | **Stable** (2 repeats per client, hashes matched) |

**No numerical change of any kind. Checkpoint selection cannot change.**

### 1.4 Measured effect

| Metric | Pre | Post | Change |
|---|---:|---:|---:|
| 5-client, 1 epoch (sum) | 3,617.5 ms | 3,322.5 ms | **−8.15 %** |
| client_01 3-epoch | 3,479.2 ms | 3,350.3 ms | −3.70 % |

Per client:

| Client | Pre ms | Post ms |
|---|---:|---:|
| client_01 | 1,560.2 | 1,395.0 |
| client_02 | 669.2 | 619.7 |
| client_03 | 292.7 | 282.1 |
| client_04 | 510.0 | 472.7 |
| client_05 | 585.4 | 553.0 |

**Honest caveat:** single-shot timings here carry several percent of run-to-run variance. The
repeated measurement in §3 gives a CV of 3.6 %, so the 8.2 % figure is at the edge of resolvable.
The direction is consistent across all five clients and every repetition, which is stronger evidence
than the point estimate.

---

## 2. O3 — buffer caching

### 2.1 Investigation: what is actually immutable?

In `scripts/run_phase8_robust.py`, the per-client delta was built as:

```python
delta = torch.cat([(local[key].to(torch.float64) - baseline[key].to(torch.float64)).reshape(-1)
                   for key in baseline if torch.is_floating_point(baseline[key])])
```

`global_state` is converted to float64 **once per client** — five times per round — even though it
cannot change during the loop. Verified: `global_state` is only reassigned at line 197, *after* every
client has trained.

### 2.2 What was safe to cache, and what was not

| Candidate | Verdict |
|---|---|
| `global_state` float64 flatten | **Safe** — immutable across the client loop |
| Local client states | **Not safe** — new object per client, per round |
| Per-client delta vectors | **Not safe** — must be recomputed (inputs change every round) |
| DataLoader batches | Not applicable — different indices each epoch by design |
| Model activations | **Not safe** — change every forward pass |

Only the baseline flatten qualified. The change is deliberately narrow: **one cached tensor, no
persistent cache across rounds.**

### 2.3 A bug caught during implementation

My first edit computed `cat([(local − global)…]) − baseline`, which subtracts the global state
twice. Verified against the correct formulation and corrected to `cat([local…]) − baseline`. The
equivalence was then proven:

```
shapes torch.Size([30]) torch.Size([30])
bitwise identical: True
max abs diff: 0.0
```

Had this shipped it would have silently corrupted every delta. It is recorded here rather than
quietly fixed.

### 2.4 Validation

| Check | Result |
|---|---|
| Delta vectors vs original formulation | **Bitwise identical**, max abs diff **0.0** |
| Test suite | 183 passed, 16 skipped |
| Determinism | Stable |

### 2.5 Measured effect

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Delta construction, 5 clients | 3.585 ms | 2.744 ms | **−23.5 %** |
| As share of a 6,460 ms round | 0.0555 % | 0.0425 % | **−0.011 %** |

**Honest reporting: this saves 0.71 ms per round.** It is a real, verified improvement and it is
negligible. It is adopted because it is provably free of behaviour change, not because it matters.

---

## 3. O2 — `cudnn.benchmark` investigation

### 3.1 Measured

| Setting | Times (3 reps) | Hash stable across reps? |
|---|---|---|
| `benchmark=False` | 3,645 / 3,367 / 3,354 ms | Yes |
| `benchmark=True` | 3,347 / 3,477 / 3,360 ms | Yes |
| `benchmark=False` | 3,347 / 3,403 / 3,368 ms | Yes |
| `benchmark=True` | 3,484 / 3,380 / 3,355 ms | Yes |

Hashes were identical between settings (`5385a700c4fa4f31…`), and identical to the pre-change
baseline.

**No speedup.** The timings overlap completely. This model has a small, fixed set of convolution
shapes that cuDNN already covers efficiently; autotuning has nothing to find.

### 3.2 The structural blocker

`seed_everything` (`src/training/phase4.py:114-116`) unconditionally sets:

```python
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
```

Proven behaviourally:

```
before seed_everything: benchmark = True
after  seed_everything: benchmark = False | deterministic = True
```

So `cudnn.benchmark` is **reset to False on every `seed_everything` call**, which happens at the
start of every run and every seed. Enabling it would require modifying `seed_everything` — a
determinism change, which the constraints explicitly forbid.

### 3.3 Decision

**Rejected, on two independent grounds:** no measured benefit, and implausible to adopt without
altering deterministic settings. Not implemented. No code changed.

---

## 4. Reproducibility verification

| Check | Result |
|---|---|
| `seed_everything` behaviour | **Unchanged** — still forces `benchmark=False`, `deterministic=True` |
| Deterministic algorithms | Unchanged (`torch.use_deterministic_algorithms`) |
| `CUBLAS_WORKSPACE_CONFIG` | Unchanged |
| Seeds | Unchanged (42–46, 47–48, 49–53 all intact) |
| Bit-identical output vs pre-change | **Yes** — state hash `5385a700…`, val macro-F1 `0.252459252955` |
| CPU execution path | **Preserved** — `non_blocking` evaluates to `False` when `device.type != "cuda"` |

---

## 5. Files changed

| File | Change | Lines |
|---|---|---|
| `scripts/run_phase5_a2_ablation.py` | O1: `non_blocking` computed from destination device, applied to features and labels | 1 block |
| `scripts/run_phase8_robust.py` | O3: single cached baseline flatten per round; per-client delta computed against it | 1 block |

**Not changed:** `src/models/cnn1d.py`, `src/training/phase4.py`, `src/federated/fedavg.py`,
`src/aggregation/*`, `src/privacy/*`, all configs, all thresholds, all manifests, all results.

---

## 6. Honest limitations

1. **Timing variance is comparable to the O1 effect.** Repeated measurement gives CV 3.6 %; the O1
   gain is 8.2 % in single-shot and directionally consistent across all clients, but should not be
   quoted more precisely than "5–8 %".
2. **O3 is negligible in wall-clock terms** (0.011 %). It is adopted for correctness-preserving
   tidiness, not performance.
3. **`cudnn.benchmark` may help on other hardware** with more convolution shapes or newer
   architectures. This finding is specific to this model on this GTX 1650.
4. **The real headroom remains AMP**, which is prohibited. Tier 1 touches only ~8 % of runtime
   because 95.8 % of a round is GPU compute that these changes do not accelerate.
5. **No full matrix was re-run**, per instruction. Validation used the representative workload
   (client_01 plus all five clients, one and three epochs).

---

## 7. Expected effect on a full run — measured, not estimated

An earlier draft of this section estimated ~40 ms per round from the per-epoch figure. That estimate
was wrong and has been replaced with direct measurement.

**Batches per round:** 5 clients × 2 epochs = **566 batches**.

**Marginal label-copy cost** (same batch size, same destination):

| Transfer | Cost per batch |
|---|---:|
| Synchronous (`non_blocking=False`) | **221.5 µs** |
| Non-blocking (`non_blocking=True`) | **15.9 µs** |
| **Marginal saving** | **205.6 µs** |

**Per-round saving: 566 × 205.6 µs ≈ 116 ms.**

Measured round wall time (5 clients × 2 epochs, 5 repetitions):
`[6370, 6099, 6199, 6099, 6086]` ms, **median 6,099 ms**.

| Item | Value |
|---|---|
| Round time (measured) | 6,099 ms |
| O1 saving (566 batches × 205.6 µs) | **≈116 ms** |
| O3 saving | 0.7 ms |
| **Total per-round gain** | **≈117 ms ≈ 1.9 %** |
| 51-round run | 5.18 min → ≈5.08 min |

**Why the isolated per-epoch measurement overstated the effect.** The standalone probe measured
label copies after the source tensor was already resident in cache, giving 40.8 µs. In a real
training loop the copy competes with feature transfers and GPU work, so the true synchronous cost is
**221 µs/batch**. The per-round figure in this section is therefore higher (1.9 %) and the
per-epoch figure lower (borderline) than a naive reading of the earlier table would suggest.

Both numbers are now reported from direct measurement. The honest summary is: **O1 saves roughly
1.9 % per round**, and the earlier "8 % per epoch" figure should be read as an upper-bound artifact
of a warm-cache microbenchmark rather than a production expectation.
