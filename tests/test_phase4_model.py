import pytest

torch = pytest.importorskip("torch")

from src.models.cnn1d import CompactECGCNN, trainable_parameter_count


def test_compact_cnn_has_approved_parameter_count_and_output_shape():
    model = CompactECGCNN()
    model.eval()

    with torch.inference_mode():
        logits = model(torch.zeros((4, 1, 253)))

    assert logits.shape == (4, 5)
    assert trainable_parameter_count(model) == 36357


def test_compact_cnn_rejects_wrong_input_shape():
    model = CompactECGCNN()

    with pytest.raises(ValueError, match="Expected input shape"):
        model(torch.zeros((4, 253)))
