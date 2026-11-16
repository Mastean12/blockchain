"""The frozen ``compact_cnn_v1`` 1D CNN shared by Phase 4 and Phase 5.

The architecture is fixed by ``configs/models/phase4_cnn_v1.yaml`` and validated by
``src.training.phase4.validate_config``:

- three convolution blocks (32/64/128 channels, kernels 7/5/3, same padding,
  max-pool 2 after blocks 1 and 2, no pooling after block 3);
- ReLU activations, BatchNorm1d after every convolution;
- adaptive average pooling to a single value per channel;
- dropout 0.3 and a linear classifier 128 -> 5.

For a 253-sample window the two max-pool layers and the final adaptive average pool
collapse the 128 feature maps to a single value per channel, giving a classifier of
128 * 5 + 5 = 645 parameters. The convolution and BatchNorm weights and biases add
35,712, so the total trainable count is 36,357. ``_model`` in
``src/training/phase4.py`` asserts this count at construction time, and
``trainable_parameter_count`` re-checks it in the tests.
"""

from __future__ import annotations

import torch
from torch import nn


class CompactECGCNN(nn.Module):
    """Compact 1D CNN for five-class AAMI-derived heartbeat classification."""

    def __init__(
        self,
        input_samples: int = 253,
        class_count: int = 5,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        if input_samples != 253:
            raise ValueError("compact_cnn_v1 expects 253-sample windows")
        if class_count != 5:
            raise ValueError("compact_cnn_v1 expects five classes")

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
            nn.AdaptiveAvgPool1d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=float(dropout)),
            nn.Linear(128, self.class_count),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        if inputs.ndim != 3 or inputs.shape[1] != 1 or inputs.shape[2] != self.input_samples:
            raise ValueError(
                "Expected input shape (batch, 1, "
                f"{self.input_samples}), got {tuple(inputs.shape)}"
            )
        return self.classifier(self.features(inputs))


def trainable_parameter_count(model: nn.Module) -> int:
    """Number of parameters with ``requires_grad=True``."""
    return int(sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad))
