# Phase 8 — GPU Utilisation and Performance Audit

**Type:** measurement-only audit. No methodology, threshold, seed, partition, architecture or
aggregation mathematics was changed. No full matrix was launched. No dependency installed.
**Date:** 17 November 2026
**Scope:** the Phase 8 execution path (`scripts/run_phase8_robust.py` → `train_local` →
`evaluate_model` → aggregation rules).

---

## 0. Headline findings

| # | Finding | Impact |
|---|---|---|
| **1** | GPU utilisation is **already good**: duty cycle **85–98 %**. The pipeline is GPU-bound, not data-bound. | Worker tuning would gain nothing |
| **2** | **95.8 % of round time is client training.** Aggregation is 2 ms (0.03 %), evaluation 4.1 %. | Optimising aggregation is pointless |
| **3** | Local training is **7.2× faster on GPU** (1.49 s vs 10.8 s per epoch) and is correctly device-placed. | GPU is being used properly |
| **4** | **A real defect exists:** label transfers use `non_blocking=False` because the condition tests the *CPU* tensor's device. | ~41 µs/batch wasted, ~4 ms/epoch — real but small |
| **5** | **No VRAM constraint.** Peak 104–153 MB of 4096 MB (2.5–3.7 %). Batch 4096 still fits. | 4 GB is not a limitation |
| **6** | **No AMP and no TF32 for matmul.** | Largest available speedup, ~1.5–2× |
| **7** | Privacy/attack/defence ops are CPU-side **by design** and cost **< 1 ms** each. | Not a bottleneck |

**Conclusion:** the implementation is not badly optimised. The one genuine defect is narrow, and the
main performance headroom is mixed-precision, which would change numerics and therefore cannot be
adopted without approval.

---

## 1. Environment verification

| Item | Measured |
|---|---|
| torch | 2.14.1+cu126 |
| CUDA available | **True** |
| Device | NVIDIA GeForce GTX 1650 |
| VRAM | **4.00 GB** |
| Compute capability | 7.5 (Turing) |
| SMs | 14 |
| cuDNN enabled | True |
| `cudnn.benchmark` | **False** |
| `cudnn.allow_tf32` | True |
| `matmul.allow_tf32` | **False** |
| `float32_matmul_precision` | `highest` |
| AMP usage in Phase 8 | **None** |

---

## 2. The eight audit questions

### 2.1 Is the model explicitly placed on CUDA? — **YES**

`_model(config, device)` calls `.to(device)` (`src/training/phase4.py:229`). Probe result:

```
model first param device: cuda:0
all params on cuda: True
```

Every client model is constructed with the device argument and every `load_state_dict` transfers
with `{k: v.to(device) ...}`. Correct throughout.

### 2.2 Are inputs, targets and tensors on the same device? — **YES, with one defect**

The DataLoader correctly yields CPU tensors (expected, since `pin_memory=True`), and the training
loop moves them:

```python
features = features.unsqueeze(1).to(device, non_blocking=device.type == "cuda")   # correct
labels   = labels.to(device,          non_blocking=labels.device.type == "cuda")  # DEFECT
```

The second line tests **`labels.device.type`**, which is `"cpu"`, so it evaluates to `False` and the
label transfer is **synchronous**. Measured:

```
labels.device.type == 'cuda' evaluates to: False
=> non_blocking=False: label transfers are SYNCHRONOUS
feature H2D (non_blocking=True):  280.5 us/batch
label  H2D (non_blocking=False):   40.8 us/batch
```

**Impact:** labels are only 8 bytes/sample (208 KB/epoch), so the total cost is small — roughly
105 batches × 41 µs ≈ **4.3 ms per epoch**, or ~0.3 % of an epoch. It is a genuine bug (the intent
was clearly `device.type == "cuda"`) but not a significant bottleneck. It is also inherited from the
frozen Phase 5 code, so fixing it changes nothing about Phase 1–7 results.

### 2.3 Does local client training execute on CUDA? — **YES, and it dominates**

Measured, client_01 (26,685 windows), 1 epoch:

| Device | Wall | Throughput | Speedup |
|---|---:|---:|---:|
| GPU | **1,489 ms** | 17,926 samples/s | **7.23×** |
| CPU | 10,759 ms | 2,480 samples/s | 1× |

Per-client epoch distribution:

| Client | Windows | Epoch ms | ms/1k windows |
|---|---:|---:|---:|
| client_01 | 26,685 | 1,376 | 51.6 |
| client_02 | 14,780 | 624 | 42.2 |
| client_03 | 6,260 | 272 | 43.5 |
| client_04 | 11,149 | 469 | 42.1 |
| client_05 | 13,053 | 548 | 42.0 |
| **Total** | **71,927** | **3,289** | |

client_01 is 49 % slower per window than the others (51.6 vs ~42 ms/1k), consistent with cache
pressure at the largest size rather than a device problem.

### 2.4 Does aggregation unnecessarily transfer CPU↔GPU? — **NO, and it costs nothing**

Aggregation operates on CPU float64 vectors by design; there is no GPU round-trip. Measured on
36,357-element updates with 5 clients:

| Rule | Cost |
|---|---:|
| FedAvg | 1.55 ms |
| Coordinate median | 2.79 ms |
| Trimmed mean | 2.61 ms |
| Krum | 4.37 ms |
| Multi-Krum | 4.59 ms |

Delta construction (`local − global` flattened to float64): **0.35 ms**. `_cpu_state_dict`
(device→CPU clone): **0.75 ms**; ×5 clients = 3.8 ms/round.

**Total non-training round overhead: ~7 ms against ~6,360 ms of round time — 0.1 %.**

For completeness, GPU alternatives were measured (not adopted): coordinate median on GPU
**0.87 ms**, L2 norm on GPU **0.48 ms** — but moving 5×36k floats to GPU each round would cost more
than the 2.8 ms saved.

### 2.5 Is evaluation a bottleneck? — **NO**

| Split | Windows | Time | Throughput |
|---|---:|---:|---:|
| Validation | 13,722 | 415 ms | 33,036 windows/s |
| Test | 15,045 | 236 ms | 63,733 windows/s |

Validation runs once per round and accounts for **4.1 %** of round time. It runs on GPU (same
`device` argument). Cost is dominated by the `.cpu().numpy()` transfer of probabilities for sklearn
metrics, not by the forward pass — but at 415 ms it is not worth optimising.

### 2.6 Do DataLoader, preprocessing, checkpoint or init dominate? — **NO**

| Item | Cost | Share of round |
|---|---:|---:|
| `load_phase4_data` (one-off) | 213.9 ms | — |
| `_model` construction + state load | **1.5 ms** | 0.02 % |
| DataLoader iteration (105 batches) | ~110 ms unpinned | see 2.6.1 |
| Checkpoint save | **4.11 ms** (151 KB) | 0.07 % |
| Validation | 415 ms | 4.1 % |
| **Client training** | **6,095 ms** | **95.8 %** |

No repeated preprocessing: arrays are loaded once into float32 tensors and reused. No checkpoint
loading inside the round loop.

#### 2.6.1 The `num_workers=0` question — measured, and it does not matter

`_local_loader` pins `num_workers=0, pin_memory=torch.cuda.is_available()`. Testing worker scaling on
the real training loop (frozen config otherwise unchanged):

| workers | pin_memory | epoch ms | samples/s | **GPU duty cycle** |
|---:|---|---:|---:|---:|
| 0 | False | 1,275 | 20,929 | 90.2 % |
| **0** | **True (frozen)** | **1,049** | **25,434** | **86.0 %** |
| 2 | False | 1,008 | 26,480 | 92.9 % |
| 2 | True | 1,121 | 23,815 | 98.0 % |
| 4 | False | 1,098 | 24,300 | 96.3 % |
| 4 | True | 1,064 | 25,080 | 97.7 % |

**All configurations land within 1.01–1.28 s and 86–98 % duty cycle.** Additional workers give no
reliable improvement. Detailed duty-cycle measurement at the frozen configuration:

```
batches: 105, wall 1060 ms, GPU compute 904 ms
GPU duty cycle: 85.2%
GPU idle (data prep / H2D / Python): 157 ms
```

**The pipeline is GPU-bound.** Raising `num_workers` would add process overhead and Windows spawn
complexity for no gain — and would risk changing RNG consumption order, which is exactly what the
frozen protocol forbids.

A separate observation: unpinned iteration is faster *in isolation* (936 vs 512 batches/s), but
pinned H2D transfer recovers the difference in the real loop (1,049 ms pinned vs 1,275 ms unpinned).
`pin_memory=True` is therefore the correct setting and is already in place.

### 2.7 Does 4 GB VRAM constrain anything? — **NO**

| Batch size | Peak allocated | Reserved | Fits? |
|---:|---:|---:|:---:|
| **256 (frozen)** | **104 MB** | 122 MB | Yes |
| 512 | 193 MB | 230 MB | Yes |
| 1,024 | 369 MB | 182 MB | Yes |
| 2,048 | 722 MB | 342 MB | Yes |
| 4,096 | 1,407 MB | 818 MB | Yes |

Full training epoch peak: **153 MB of 4,096 MB (3.7 %)**. Five models resident simultaneously:
**90 MB**.

**VRAM headroom is ~3.9 GB.** The 4 GB constraint is not binding at any point. (OOM warnings appeared
only during a deliberate 8,192+ stress test, which is far beyond any legitimate need.)

### 2.8 Are privacy, attack or robust-aggregation ops CPU-bound? — **YES, BY DESIGN, AND CHEAP**

All Phase 6 and Phase 8 tensor operations act on **serialised model state on CPU**, never on GPU
activations. That is correct: the DP mechanism clips a model *update vector*, not activations.

| Operation | Device | Cost |
|---|---|---:|
| `clip_update` (36,357 float64) | CPU | **0.80 ms** |
| `add_gaussian_noise` (36,357) | CPU | **0.66 ms** |
| `adversarial_updates` (1 client) | CPU | **0.24 ms** |
| `apply_rejection_policy` (5 clients) | CPU | **0.66 ms** |

All are sub-millisecond and together are under 0.05 % of a round. Moving them to GPU would add
transfer cost for no benefit. `per_client_sensitivity` is pure Python arithmetic.

**These operations are not a bottleneck and should stay on CPU.**

### 2.9 Do multiple model copies or conversions reduce performance? — **NO**

Per round the code creates one model per client (5 total, sequentially, each released after use),
plus one delta vector per client. Measured overhead:

| Item | Per round |
|---|---:|
| 5 × `_cpu_state_dict` (device→CPU clone) | 3.8 ms |
| 5 × delta flatten to float64 | ~2.0 ms |
| `apply_update` (float64 → float32) | 0.9 ms |
| state load/store to device | 3.0 ms |
| **Total conversion overhead** | **~10 ms (0.16 %)** |

Models are **not** held resident concurrently during training, so there is no VRAM or memory-copy
penalty. float64 upcasting in delta construction is deliberate (numerical fidelity for aggregation)
and costs ~2 ms — correct to keep.

---

## 3. End-to-end round attribution

One complete round, measured with `torch.cuda.synchronize()` around every stage:

| Stage | ms | % of round |
|---|---:|---:|
| `train[client_01]` | 2,293.4 | 36.0 % |
| `train[client_02]` | 1,236.9 | 19.4 % |
| `train[client_05]` | 1,099.5 | 17.3 % |
| `train[client_04]` | 927.8 | 14.6 % |
| `train[client_03]` | 537.4 | 8.4 % |
| `validate` | 258.2 | 4.1 % |
| `aggregate` | 2.0 | 0.03 % |
| `load_global` / `store_global` | 3.0 | 0.05 % |
| `apply_update` | 0.9 | 0.01 % |
| 5 × `delta[...]` | 4.4 | 0.07 % |
| **TOTAL** | **6,363.8** | 100 % |

**Client training 95.8 % · validation 4.1 % · everything else 0.1 %.**

This matches the historical Phase 8 runs: the 145 confirmatory runs report **mean 6.46 s/round,
median 6.48 s, min 6.16 s, max 6.66 s** — the implementation is behaving consistently and near its
measured optimum.

> **Correction to an earlier misreading.** While reviewing the development analysis I previously
> described per-run durations as "median 38.4 s". That figure was **seconds per run**, not per round.
> The correct per-round figure is 6.46 s. No result in the confirmatory report depends on the
> incorrect reading, but the record should be accurate.

---

## 4. Where the remaining time actually goes

With 95.8 % in training and a 85–98 % GPU duty cycle, the only meaningful lever is **making the GPU
arithmetic faster**, not feeding it better.

| Lever | Expected gain | Cost / risk |
|---|---|---|
| **Automatic mixed precision (AMP, fp16)** | **~1.4–2.0×** on a Turing GTX 1650 (has fp16 tensor cores) | Changes numerics → changes results. **Not permitted** under the frozen protocol |
| TF32 for matmul | small (conv-heavy net, Turing has no TF32) | Effectively zero on this GPU |
| `cudnn.benchmark = True` | 5–15 % on fixed shapes | Safe but alters kernel selection; should be validated for reproducibility first |
| Larger batch size | ~7 % (256 → 512) | **Forbidden** — batch size is frozen |
| `num_workers > 0` | **0 %** measured | Adds risk, changes RNG order |
| torch.compile | uncertain on Windows | Not installed; not permitted |

### 4.1 The honest arithmetic on AMP

AMP would take a round from 6.46 s to roughly 3.5–4.5 s, and a 51-round run from 5.5 min to
~3–4 min. Across 145 confirmatory runs (~15.6 h total) that would have saved ~7–9 h.

**But it would change every result.** fp16 accumulation shifts the loss surface, the validation
macro-F1 ordering, and therefore the selected checkpoint. Under §12 and the frozen protocol, that is
a methodology change, not an optimisation. **It must not be adopted for Phase 8.**

---

## 5. Proposed optimisation plan

Ordered by ratio of value to risk. **None implemented; all require research-lead approval.**

### Tier 1 — safe, no methodological impact

| # | Change | Expected gain | Justification |
|---|---|---|---|
| **O1** | Fix `non_blocking=labels.device.type == "cuda"` → `device.type == "cuda"` | ~4 ms/epoch (~0.3 %) | Clear bug; intent is unambiguous. Must be verified to produce bit-identical metrics before adoption |
| **O2** | Enable `torch.backends.cudnn.benchmark = True` | 5–15 % | Pure kernel selection. Requires a reproducibility check: one seed run twice, metrics must match |
| **O3** | Cache the per-client delta flatten buffer | ~2 ms/round | Minor; only worth doing alongside other work |

Tier 1 total realistic gain: **~10–18 %**. Combined with the fact that the pipeline is already
85–98 % GPU-efficient, further tuning has limited headroom.

### Tier 2 — changes results, requires protocol re-approval

| # | Change | Gain | Why blocked |
|---|---|---|---|
| **O4** | AMP / fp16 autocast | 1.4–2.0× | Alters numerics; would invalidate Phase 4–8 results |
| **O5** | Larger batch size | ~7 % | Batch size frozen |
| **O6** | `num_workers > 0` | **0 %** measured | No benefit; adds Windows spawn risk and RNG-order risk |

**O4 is the only change that would materially help, and it is the one change that must not be made
within this study's frozen protocol.** If a future phase wants AMP, it must be a new, separately
approved configuration with its own results — not a retrofit.

### 6. What should *not* be optimised

| Item | Why not |
|---|---|
| Aggregation rules (2 ms) | GPU version saves < 2 ms but costs ~1 ms of transfer; net ~0 |
| Privacy/attack/defence ops (0.2–0.8 ms) | Correctly CPU-side; GPU would add transfer overhead |
| DataLoader workers | Measured 0 % gain |
| VRAM/batch sizing | Only 3.7 % of VRAM used |
| Evaluation (4.1 %) | 415 ms of a 6,460 ms round |

---

## 7. Limitations of this audit

1. **Single machine, single run each.** Timings have run-to-run variance of a few percent; the
   worker-scaling table shows up to ±20 % spread between repeats, so small differences should not be
   over-interpreted.
2. **Warm caches.** The round profile warms CUDA before measuring, so it excludes first-call kernel
   compilation. Real runs include that once per process.
3. **The GTX 1650 has 14 SMs and no TF32.** Findings about duty cycle and AMP headroom do not
   transfer to larger or newer GPUs.
4. **Desktop GPU.** The card also drives the display; some VRAM (≈650 MB observed earlier in the
   project) is held by other processes. Peak figures are process-local.
5. **No profiling of kernel-level hotspots** (no Nsight/nsys available). All attribution is
   Python-level wall-clock with explicit `cuda.synchronize()`.
6. **AMP gain is estimated, not measured**, because implementing it would alter the frozen
   configuration. The 1.4–2.0× range is an expectation for Turing fp16 tensor cores, not a
   measurement.

---

## 8. Summary statement

The Phase 8 implementation is **not** suffering from a GPU-utilisation problem. The model is on
CUDA, training runs on CUDA with a 7.2× speedup over CPU, GPU duty cycle is 85–98 %, only 3.7 % of
VRAM is used, and every non-training stage together accounts for 0.1 % of a round.

The single genuine defect is a synchronous label transfer worth ~0.3 %. Fixing it is safe and
recommended, but it will not change the runtime picture.

Material speedup would require mixed precision, which changes numerical results and is therefore
prohibited within this frozen protocol. Any decision to pursue it belongs to a new approved
configuration, not to an optimisation of the existing one.

---

## 9. Tier 1 implementation results (17 November 2026)

This section records what was implemented and measured after the audit. Full validation in
`PHASE_8_TIER1_OPTIMISATION_VALIDATION.md`.

### 9.1 Adopted

| Change | Numerically identical? | Measured effect |
|---|---|---|
| **O1** label transfer `non_blocking` fixed | **Yes — bit-identical** | **~116 ms per round (1.9 %)**, computed as 566 batches x 205.6 us marginal saving |
| **O3** baseline flatten cached once per round | **Yes — delta max abs diff 0.0** | 3.59 -> 2.74 ms/round (0.011 %) |

Verification for both: validation macro-F1 **0.252459252955** and 3-epoch state hash
**5385a700c4fa4f318e559369** identical to the pre-change baseline; determinism stable across
repeats; CPU path preserved (`non_blocking` is `False` when the device is not CUDA).

### 9.2 Rejected on evidence

**O2 `cudnn.benchmark = True` — not enabled.**

- No speedup: timings overlapped completely (3,347-3,645 ms in both modes over 3 repetitions).
- Hashes identical, so no correctness objection — but no benefit either.
- **Structural blocker:** `seed_everything` (`src/training/phase4.py:114`) unconditionally sets
  `cudnn.benchmark = False` and `cudnn.deterministic = True`. Demonstrated:
  `before seed_everything: benchmark = True` -> `after: benchmark = False`. Enabling it would
  require editing the determinism setup, which the constraints forbid.

### 9.3 Correction to the audit's Section 2.2 estimate

The audit estimated the O1 defect at "~4 ms per epoch", derived from an isolated microbenchmark that
measured 40.8 us per label copy on a warm cache. In the real training loop the synchronous cost is
**221.5 us per batch**, because the copy competes with feature transfers and GPU work.

| Measurement context | Sync label copy | Per-round impact |
|---|---:|---:|
| Isolated microbenchmark (audit section 2.2) | 40.8 us | ~4 ms/epoch |
| **Real loop, 566 batches/round** | **221.5 us** | **~116 ms/round** |

The audit therefore **understated** this defect by roughly 5x per batch. Corrected figures are used
in all subsequent reporting. This is exactly why the validation phase measured in situ rather than
relying on the audit's estimate.

### 9.4 Net position

Combined gain is **~1.9 % per round** (~117 ms of 6,099 ms). Round time measured after the changes:
median **6,099 ms** over 5 repetitions, consistent with the historical untuned 6,460 ms mean after
accounting for warm-cache conditions.

The audit's central conclusion is unchanged and now confirmed empirically: **95.8 % of a round is GPU
compute that these optimisations cannot accelerate.** Material speedup still requires mixed
precision, which remains prohibited.
