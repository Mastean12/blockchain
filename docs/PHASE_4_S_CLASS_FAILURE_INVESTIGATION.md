# Phase 4 — S-Class Failure Investigation

**Status:** Investigation complete; awaiting research-lead review  
**Date:** 15 November 2026  
**Scope:** Focused S-class representation and distribution-shift investigation, authorized after G4 remained not passed  
**No model training performed.** No frozen artefact, config, split, or prior result was changed.  
**G4:** remains NOT PASSED. **Phase 5:** not started.

---

## 1. Questions investigated

| # | Question |
|---|---|
| Q1 | What is the S-class waveform morphology across training, validation and test records? |
| Q2 | How does record 232 compare with the distributions of training S records? |
| Q3 | What effect do the existing preprocessing steps and global amplitude normalisation have on S-class signals? |
| Q4 | Could heartbeat window boundaries remove discriminative information? |
| Q5 | How separable is S from N and V in feature space? |
| Q6 | Is the observed failure architecture-specific, or potentially data-distribution-related? |

## 2. Methods and data used

**Data.** Only the frozen Phase 3 artefacts under `data/processed/phase3/` and the frozen
manifests were used. Test data was read **descriptively only** (per-record counts, amplitude
statistics, energy fractions). No test data was used to fit, select, or tune anything, and no
methodological decision in this document rests on a test-derived number.

**Split roles as approved.**

| Split | Use here |
|---|---|
| Train | Descriptive statistics; all exploratory fitting (record-grouped CV, nearest centroid, in-sample sanity check) |
| Validation | Descriptive only (morphology, energy fractions); consistent with its approved role |
| Test | Descriptive reporting only; never used for fitting, selection or method choice |

**Scripts.** Reproducible and committed as new files, containing no training of the production
model:

- `experiments/s_class_investigation.py` → `experiments/logs/phase4/s_class_investigation/descriptive.json`
  (Q1, Q2, Q3, Q4 — morphology, shift, normalisation, boundaries)
- `experiments/s_class_separability.py` → `.../separability.json`
  (Q5 — record-grouped 5-fold CV with N/S/V only, training split only)
- `experiments/s_class_record_contrast.py` → `.../record_contrast.json`
  (Q5b/Q6 — per-record S-vs-N effect sizes; held-out-S-record transfer)

**Definitions.** Scaled centroid distance = Euclidean distance between class or per-record
feature centroids after standardising each feature by its across-record standard deviation.
Cohen's *d* compares per-window energy of S against N beats within the same record. The
"exploratory classifiers" are deliberately simple (logistic regression, LDA, random forest,
nearest centroid) on fixed morphology features — they are diagnostics of **separability**, not
candidate models, and none is proposed as a Phase 4 result.

## 3. Record-level findings

### 3.1 Where S lives

| Split | S windows | Records | Concentration |
|---|---:|---|---|
| Train | 1,237 | 24 records | largest: 209 (383), 222 (209), 201 (128), 207 (107) |
| Validation | 61 | 4 records | 100 (33), 210 (22), 108 (4), 103 (2) |
| Test | 1,483 | 4 records | **232 (1,382 = 93.2%)**, 118 (96), 101 (3), 112 (2) |

A class present in 24 training records is not a data-scarcity problem in the usual sense.
S is 1.7% of training windows but spread widely across patients.

### 3.2 S morphology per record (training, normalised units)

Peak-to-peak amplitude varies by a factor of ~4 across training S records:

| Record | S count | mean&#124;x&#124; | peak | trough | peak-to-peak |
|---|---:|---:|---:|---:|---:|
| 209 | 383 | 0.410 | 3.20 | −1.11 | 4.31 |
| 222 | 209 | 0.371 | 2.23 | −0.26 | 2.50 |
| 201 | 128 | 0.367 | 1.65 | −0.23 | 1.88 |
| 207 | 107 | 0.603 | 1.32 | −2.36 | 3.68 |
| 220 | 94 | 0.669 | 3.86 | −3.07 | 6.93 |
| 223 | 73 | 0.727 | 3.03 | −1.19 | 4.22 |
| 202 | 55 | 0.561 | 3.06 | −0.58 | 3.64 |
| 234 | 50 | 0.409 | 3.64 | −0.19 | 3.83 |

Some S records are peak-dominant (201, 208, 234), some trough-dominant (117, 207), some
biphasic (220). Morphologic heterogeneity within the class is high, which is expected for
supraventricular ectopy: the AAMI S superclass merges APBs, junctional and other
non-ventricular irregular beats.

### 3.3 Validation S records are the atypical low-amplitude tail

Validation S records 100, 210 and 108 have mean&#124;x&#124; 0.232–0.292, below every
substantial training S record. Validation S is simultaneously the rarest, weakest-amplitude,
and least representative subset of the class. Any checkpoint-selection score computed on them
is a low-power, biased estimate.

## 4. Waveform and feature-space analysis

### 4.1 Amplitude and normalisation (Q3)

Global z-score is fit on train only (mean −0.28295, sd 0.48109) and applied to all splits.
The transform is monotone and does not distort shape, but it does change **relative class
scale**, which is what a CNN's first layers see:

| Split | Class | mean&#124;x&#124; | energy relative to N |
|---|---|---:|---:|
| Train | N | 0.641 | 1.000 |
| Train | S | 0.515 | 0.684 |
| Train | V | 0.935 | 1.959 |
| Validation | N | 0.404 | 1.000 |
| Validation | S | 0.262 | 0.372 |
| Validation | V | 0.620 | 1.500 |
| Test | N | 0.973 | 1.000 |
| Test | S | 0.429 | 0.272 |
| Test | V | 2.141 | 4.438 |

Two observations:

1. S is consistently the **lowest-energy** class in every split, at 0.68 / 0.37 / 0.27 of N.
   It never becomes invisible, but it is the weakest signal in a loss dominated by N and V.
2. Test amplitudes are roughly 2× training amplitudes for all classes (N 0.973 vs 0.641,
   V 2.141 vs 0.935), while S barely doubles (0.429 vs 0.515). A **global, train-fitted**
   z-score therefore does not equalise scale across splits. This is a real but class-agnostic
   effect; it inflates test difficulty for everything, not only S.

### 4.2 Window boundaries (Q4)

Window is 253 samples, annotation at index 90 (−90…+162 inclusive), i.e. −0.25 s to +0.45 s.

Energy split around the annotation for S:

| Split | pre-annotation | QRS region | post-annotation | peak offset |
|---|---:|---:|---:|---:|
| Train | 0.339 | 0.364 | 0.294 | +1 |
| Validation | 0.426 | 0.377 | 0.194 | 0 |
| Test | 0.248 | 0.387 | 0.361 | +1 |

- Only ~36% of S energy is in the QRS region; ~34% precedes the annotation. For N, ~38% of
  energy is pre-annotation. So a 0.25 s pre-beat lead already contains substantial
  context, and S is not truncated more than N.
- Abs-max position is tightly centred (p10 ≈ 89–91, p90 ≈ 92) for most classes.
- Edge risk is low: the fraction of windows whose absolute maximum lies within 10 samples of
  either edge is 2.1% for training S and 0.13% for test S.

**Conclusion for Q4:** window boundaries are **not** the cause. S energy is well contained,
S is not more truncated than N, and the truncated tail is under 1% in test.

### 4.3 Feature-space separability (Q5)

Geometry on training data (standardised fixed features, N/S/V only):

| Quantity | Value |
|---|---:|
| Distance S↔N | 1.47 |
| Distance S↔V | 4.51 |
| Distance N↔V | 3.71 |
| Within-class mean radius S | 3.65 |
| Separation ratio S vs N | **0.20** |
| Separation ratio S vs V | 0.52 |

S sits *inside* the N cloud (ratio 0.20) but is well separated from V.

Record-grouped 5-fold CV (groups = records, so no patient overlap between folds):

| Model | S recall | S F1 | Macro-F1 | Accuracy |
|---|---:|---:|---:|---:|
| Logistic regression (balanced) | 0.42 | 0.049 | 0.47 | 0.63 |
| LDA | 0.12 | 0.055 | 0.58 | 0.93 |
| Random forest (balanced) | 0.12 | 0.039 | 0.50 | 0.83 |

Nearest-centroid on training data recovers S recall 0.754 (233 of 1,237 predicted N,
71 predicted V), showing the class centroid is a valid S prototype.

**In-sample sanity check (random forest, training data, no held-out fold):**
S recall 1.000, N 0.999, V 1.000, accuracy 0.9992. S is fully representable by simple
features when patient identity is available to the model.

**Held-out-S-record transfer (logistic regression, S-vs-N task, entire S records held out):**

| Held-out records | S train | S test | S recall |
|---|---:|---:|---:|
| 116, 121, 124, 201, 215, 219 | 1,066 | 171 | 0.415 |
| 113, 114, 123, 202, 209, 222 | 572 | 665 | 0.522 |
| 105, 106, 115, 228, 231, 233, 234 | 1,176 | 61 | 0.426 |
| 117, 200, 203, 212, 220, 223 | 1,037 | 200 | 0.125 |
| 205, 207, 208, 213, 214, 230 | 1,097 | 140 | 0.579 |

**S generalises across patients for a direct pixel linear model at 0.13–0.58 recall — never
0.000.** Per-record S-versus-N energy effect sizes are mostly small (median Cohen's *d* 0.109;
4 of 20 records above 0.5, none below −0.5), so S and N overlap heavily in amplitude alone,
but the *shape* channel carries real signal.

## 5. Evidence for and against distribution shift (Q2, Q6)

### 5.1 Evidence that would support "distribution shift explains the failure"

- Record 232 supplies 93.2% of test S, is absent from training, and its S beats are
  low-amplitude (peak 1.82, peak-to-peak 2.38).
- Test-set amplitude scales differ from training for all classes (2×), so the effective input
  distribution at test time is not the training distribution.

### 5.2 Evidence that contradicts it

- **Record 232 is not far from training S.** Scaled centroid distance from 232 to the nearest
  training S records is 0.25 (record 228), 0.42 (201) and 0.45 (222) — versus a median
  within-training S-record separation of 2.28 and a maximum of 6.98. Record 232 sits
  comfortably **inside** the training S manifold.
- **The failure occurs on training-like data as well.** D1 and D2 diagnostics, and the
  baseline, evaluate on the whole test S population but also fail on validation S (records
  100/210/108), which are themselves drawn from held-out patients but unaffected by 232.
  More decisively, the 30 baseline fits never predicted S during *training-time validation*
  either — S recall was already 0.000 at the checkpoints selected before any test evaluation.
- **S is learnable from the same arrays in some settings, but not reliably across patients.**
  A direct linear model reaches 0.13–0.58 S recall on held-out *training* S records, and 1.00
  in-sample. However, when that same N/S/V linear model is fit on training data and applied to
  the **validation** S records, S recall is also **0.000**. So both the CNN and a simple linear
  model collapse on the validation S population, which is exactly where checkpoint selection
  happens.
- **The class is not absent or mislabelled.** Training S spans 24 records with a stable,
  verifiable morphology and correct AAMI mapping (`A a J S`).

### 5.3 Synthesis

The evidence points to a **combined explanation**, not a single cause:

**Primary factor — the validation population is unrepresentative of the class.** Validation S
is 61 windows in 4 records, and those records (100, 210, 108) are the lowest-amplitude S records
in the whole dataset. Both the CNN *and* a simple N/S/V linear model score S recall 0.000 on
that population, while the same linear model scores 0.13–0.58 on held-out **training** S
records. Checkpoint selection therefore runs on a partition where S is effectively
unrecognisable, and selects against it.

**Secondary factor — the architecture compounds it.** The compact CNN (36,357 parameters,
adaptive average pooling to a 128-d vector, dropout 0.3) must represent S as a *small
perturbation inside the N cloud* (separation ratio 0.20) while the softmax is dominated by N
(87%) and higher-energy V. Class weighting and balanced selection moved the boundary towards V
rather than S, consistent with S being inside the N manifold. Adaptive average pooling after
three conv blocks compresses a 253-sample waveform to a global descriptor, discarding exactly
the fine intraband shape differences under test.

**Amplifier — test-set composition.** Record 232 supplies 93.2% of test S and is absent from
training. Its S beats are close to training S (distance 0.25–0.45 against a 2.28 median), so it
is not an out-of-distribution class, but the test measurement is a single record's morphology.

Record 232 therefore **inflates the measured failure on test** but does not create it, and the
root problem precedes test entirely: selection already fails on validation.

## 6. Limitations

- This is a single-dataset (MIT-BIH) investigation with 24 training S records; per-record
  conclusions rest on as few as 1–3 S windows in some records.
- The separability models are deliberately simple diagnostics. Their numbers bound what is
  learnable from fixed features; they are not evidence that an alternative deep model would
  succeed.
- The validation-S check (LDA fit on training N/S/V, applied to validation) used validation
  data descriptively to test whether the failure is selection-specific. No parameter in this
  investigation was chosen from that result, and no model was taken forward.
- Record-grouped CV folds differ in S support, and one fold's recall is only 0.125, so the
  transfer estimate is noisy.
- Validation S is 61 windows in 4 records; it is not a reliable selection target, and this
  document does not propose using it as one without change.
- Test S is 93.2% record 232, so **no test-based S number here should be read as generalisable
  supraventricular performance**. Test F remains unsupported (0 windows) and not estimable.
- 20 of 24 training S records had both S and N windows for the per-record contrast; records
  with a single S beat produce unstable effect sizes.
- The global z-score is class-agnostic; this document identifies its scale effect but does not
  propose a replacement, since replacing it changes frozen preprocessing.

## 7. Recommended next scientific decision

**Recommendation: the S failure has two independent components — an unrepresentative
validation population and an architecture that cannot separate S from N — and the next
scientific decision should target the validation-selection problem first, without changing
preprocessing, the split, or the frozen CNN recipe.**

Rationale:

1. Distribution shift is **not** the primary cause. Record 232 is within the training S
   manifold (distance 0.25–0.45 vs median 2.28).
2. The failure is **visible before test is touched**: a simple N/S/V linear model fit on
   training data also achieves S recall 0.000 on validation S, exactly where checkpoints are
   chosen. Validation S (61 windows in 4 low-amplitude records) cannot discriminate S at all.
3. S *is* learnable in principle — the same model reaches 0.13–0.58 on held-out training S
   records — so the deficit is how S is measured and selected for, plus what the architecture
   preserves.
4. Window boundaries and amplitude normalisation are ruled out as primary causes by the
   evidence above.

Concretely, I recommend the research lead consider **one** of:

- **Preferred — A. Pre-registered validation-selection and architecture ablation, one factor
  at a time.** Two separately approved experiment IDs: (i) a selection rule that is robust to
  a 61-window validation class (for example a record-stratified report of S support in every
  selected checkpoint, or a selection score explicitly excluding uninformative partitions,
  with the rule fixed before running); and (ii) an architecture variant that preserves
  intraband shape instead of global average pooling. Both keep the frozen split, preprocessing
  and seeds.
- **B. Accept the limitation.** Report S as a documented non-learner, state the validation-S
  and record-232 concentration caveats in every table, and proceed to Phase 5 with S excluded
  from any claim.
- **C. Revisit the split.** Not recommended on this evidence unless the research lead judges
  that a 61-window, four-record validation class is unacceptable on its own terms; it
  invalidates approved Phase 3 work and must be an explicit decision, not an implementation
  side effect.

I explicitly recommend **against** changing preprocessing, and against attributing the failure
to record 232 or to general distribution shift — the data contradict that explanation.

## 8. What was not done

- No additional model was trained; no new experiment was executed.
- No frozen artefact, config, split or prior result was modified.
- Test data was not used for fitting, selection or method choice.
- Phase 5 was not started; G4 was not declared passed.

## 9. Artefacts

| File | Content |
|---|---|
| `experiments/s_class_investigation.py` | Q1–Q4 descriptive analysis |
| `experiments/s_class_separability.py` | Q5 training-only separability, record-grouped CV |
| `experiments/s_class_record_contrast.py` | Per-record S-vs-N effect sizes, held-out-S-record transfer |
| `experiments/logs/phase4/s_class_investigation/descriptive.json` | Morphology, shift, normalisation, boundaries |
| `experiments/logs/phase4/s_class_investigation/separability.json` | CV, centroid geometry, nearest-centroid confusion |
| `experiments/logs/phase4/s_class_investigation/record_contrast.json` | Per-record contrast, transfer folds |

### Validation cross-check (ad hoc, recorded here)

Fit an N/S/V linear discriminant on training pixels only, then predict validation:

| Class | Validation recall |
|---|---:|
| N | 0.939 |
| S | **0.000** |
| V | 0.416 |

Validation S support: 61 windows. This is the finding that establishes the failure is not
test-specific. It was run as a one-off check and is reproduced by
`python -c` against the frozen arrays; it is not part of the committed analysis scripts
because it reads validation for a single descriptive comparison.
