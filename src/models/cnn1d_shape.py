"""Architecture ablation variant A1 for the G4 resolution attempt.

Authorised by the Phase 4 S-class investigation's preferred path: "an architecture variant that
preserves intraband shape instead of global average pooling".

The frozen ``compact_cnn_v1`` is NOT modified. This module adds a separate model with the same
convolution stack and a different pooling head, so the pooling hypothesis can be tested in
isolation.

**Design constraint — capacity must stay comparable.** A naive "flatten the 128x63 map and
project" head adds ~1.03 M parameters (28x the frozen model), which would confound the ablation:
any difference could be capacity rather than pooling. This variant instead concatenates global
*max* and global *mean* pooling (2 x 128 = 256 features) and feeds the existing 128-unit
classifier input through a small linear reduction. Parameter count is kept within ~2x of the
frozen model so the comparison is about *how* the feature map is reduced, not how much capacity
the head has.

Rationale for max+mean: global average pooling discards *where* within the 63-sample map a
feature occurs and attenuates short, high-amplitude transients. Max pooling retains the peak
response, which is the channel most likely to carry S-wave shape information. Combining both
gives the classifier access to peak-vs-average structure that a mean alone cannot express.
"""

from __future__ import annotations

import torch
from torch import nn

FEATURE_CHANNELS = 128
POOLED_FEATURES = FEATURE_CHANNELS * 2


class CompactECGCNNShapePreserving(nn.Module):
    """``compact_cnn_v1`` stack with max+mean pooling instead of global average pooling."""

    def __init__(
        self,
        input_samples: int = 253,
        class_count: int = 5,
        dropout: float = 0.3,
        hidden_units: int = 128,
    ) -> None:
        super().__init__()
        if input_samples != 253:
            raise ValueError("A1 expects 253-sample windows")
        if class_count != 5:
            raise ValueError("A1 expects five classes")

        self.input_samples = int(input_samples)
        self.class_count = int(class_count)
        self.features = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(kernel_size=2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(kernel_size=2),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
        )
        # 256 pooled features -> 128 classifier inputs, matching the frozen classifier width.
        self.reduce = nn.Sequential(
            nn.Linear(POOLED_FEATURES, int(hidden_units)),
            nn.ReLU(inplace=True),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(p=float(dropout)),
            nn.Linear(int(hidden_units), self.class_count),
        )

    def pool(self, feature_map: torch.Tensor) -> torch.Tensor:
        mean = torch.mean(feature_map, dim=2)
        peak = torch.amax(feature_map, dim=2)
        return torch.cat([mean, peak], dim=1)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        if inputs.ndim != 3 or inputs.shape[1] != 1 or inputs.shape[2] != self.input_samples:
            raise ValueError(
                "Expected input shape (batch, 1, "
                f"{self.input_samples}), got {tuple(inputs.shape)}"
            )
        feature_map = self.features(inputs)
        return self.classifier(self.reduce(self.pool(feature_map)))
