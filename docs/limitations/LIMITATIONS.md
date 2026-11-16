# Limitations

Known limits of the study. Each must be carried into the thesis; none may be silently dropped.

---

## Dataset and task

1. **MIT-BIH is a research benchmark, not a population sample.** 48 recordings from 47 subjects,
   collected 1975–1979. Class proportions are not clinical prevalence.
2. **Record-independent is not patient-independent.** Only records 201/202 have a documented shared
   subject; other identities are unknown.
3. **Four paced records excluded** (102, 104, 107, 217) under the de Chazal 44-record protocol.
4. **Q support is 15 annotations across 5 records**; it is absent from validation and sparse in test.
5. **F is absent from the test set** (0 windows). Test F metrics are not estimable and no five-class
   test macro-F1 is claimed.
6. **S support is concentrated**: 93.2 % of test S windows come from record 232, which is absent
   from training. Test S recall is not evidence of generalisable performance.
7. **Beat classification only.** Windows use expert reference annotations; this is not end-to-end
   QRS detection.
8. **EC57 was not accessed in full.** No clause-level compliance claim is made.

## Baselines and federated learning

9. **S recall is 0.000 in every Phase 4 and Phase 5 condition**, including both diagnostics and all
   20 federated runs. Root cause is a validation-population plus pooling-capacity problem, not
   leakage or a metric bug. Evidence: `PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md`.
10. **G4 passed on 16 November 2026 with the S-class defect documented as an accepted limitation**
    (`PHASE_4_G4_RESOLUTION.md`). Two pre-registered ablations were attempted: the selection-rule
    hypothesis was refuted by direct checkpoint scoring (no epoch has S signal to select), and a
    max+mean pooling variant reached at most 4 of 61 validation S windows, failing its ≥3/5-seed
    criterion. Phase 6 therefore proceeded on a baseline whose S defect is characterised and
    reproduced, not on an unexamined one.
11. **Checkpoint selection is fragile** at validation macro-F1 ≈0.28: round-to-round differences are
    smaller than seed variation, so the selected round — and the headline test number — is partly
    arbitrary within rounds 1–5.
12. **F3 scoring highest is split-specific**, not evidence that non-IID data helps. Ablation A2
    quantified it: 54 % of the advantage is aggregation weight dispersion (one client at 37.1 % of
    the model), 46 % partition composition. Five clients and one aggregation alternative only.
13. **FedProx at μ=0.01 gave no benefit** at matched rounds; F5 was not run by the pre-declared rule.
14. **Five simulated clients from one public dataset** are not independent hospitals.
15. **One partition family** (F3) was used for Phase 6; utility effects may not transfer.

## Differential privacy

16. **The privacy unit is the client slot, not a record, patient or beat.** No record-, patient- or
    beat-level guarantee exists and none may be claimed.
17. **Replace-one adjacency with equal cardinality and a fixed, published client set** hides content,
    not the existence of a client.
18. **No secure aggregation.** The server observes each noised client update, so per-client
    sensitivity `2C` (view B) — not the smaller aggregate view — is the honest accounting.
19. **The client is trusted to add its own noise.** Without secure aggregation, a cheating client
    voids its own contribution's guarantee.
20. **Five privacy units is a very coarse universe**; ε at n = 5 is a weak practical guarantee.
21. **BatchNorm buffers (448 floats) are neither DP-protected nor encrypted** — a disclosed leak of
    activation-distribution statistics.
22. **`n_k` (client sizes) is public** by manifest publication, and inferable from `num_batches_tracked`.
23. **Seeded research PRNG, not a CSPRNG.** Results demonstrate the method; they do not establish
    production security.
24. **No defensible DP operating point was found** for whole-model client-level DP at `d = 36,357`
    with five clients. The DP arm is a documented negative result.
25. **σ = 0.5 and σ = 4.0 of the approved grid were not executed** (approved omission).
26. **The DP finding is mechanism-specific.** Per-layer DP, central DP and DP-SGD were not
    implemented; they target the `√d` term differently and may behave differently.
27. **ε is computed, not measured**, and holds only under the stated assumptions.
28. **The final model is released**; inference from the model itself is out of scope.

## Homomorphic encryption

29. **CKKS does not hide the aggregate from the secret-key holder.** The decryptor sees the plaintext
    aggregate every round.
30. **CKKS provides no integrity or authenticity**; a server can drop or replay ciphertexts.
31. **Approximation error (≈1.4e-07) is empirical**, measured on the tensors used, not a formal bound.
32. **20.5× communication expansion** (145 KB → 2.98 MB per client) is the dominant HE cost.
33. **HE is not a privacy guarantee.** It provides confidentiality against the key-blind server only.

## Benchmarks against related work

34. **Direct comparison with published ECG-FL papers is unsafe** where their splits use beat-level
   random splitting after duplication-based balancing (e.g. Manwal et al. 2026). Their high accuracy
   does not establish independent-patient generalisation.
35. **No clinical claim.** This is an offline research prototype, not a validated diagnostic device.

## Governance

36. **G5 is undecided**; G6 passed with the scope limits recorded in `PHASE_6_RESULTS_AND_ANALYSIS.md` §8.1.
37. **Phases 7–10 have no results.** Blockchain audit, robust aggregation, integration and the
   defence package are not started.
