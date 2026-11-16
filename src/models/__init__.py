"""Model definitions for the approved ECG baselines."""

from src.models.cnn1d import CompactECGCNN, trainable_parameter_count

__all__ = ["CompactECGCNN", "trainable_parameter_count"]
