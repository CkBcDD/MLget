import shutil
import subprocess
import sys

sys.path.insert(0, "src")

from mlget import resolver


def test_detect_cuda_from_nvidia_smi(monkeypatch):
    # simulate nvidia-smi present and returning a line with CUDA Version
    monkeypatch.setattr(shutil, "which", lambda name: "C:/nvidia-smi")

    fake_output = "| NVIDIA-SMI 535.86.10    Driver Version: 535.86.10    CUDA Version: 12.1     |\n"

    def fake_check_output(args, stderr=None, text=None):
        return fake_output

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    cuda = resolver._detect_nvidia_cuda()
    assert cuda is not None
    assert cuda.startswith("12")
    tag = resolver._cuda_to_tag(cuda)
    assert tag == "cu121"


def test_detect_cuda_from_env_var(monkeypatch):
    # ensure nvidia-smi missing
    monkeypatch.setattr(shutil, "which", lambda name: None)
    # set CUDA_VERSION env
    monkeypatch.setenv("CUDA_VERSION", "11.8")
    cuda = resolver._detect_nvidia_cuda()
    assert cuda == "11.8"
    tag = resolver._cuda_to_tag(cuda)
    assert tag == "cu118"


def test_cuda_mapping_unknown(monkeypatch):
    # unknown or malformed -> None tag (fall back to CPU)
    assert resolver._cuda_to_tag(None) is None
    assert resolver._cuda_to_tag("") is None
    assert resolver._cuda_to_tag("not-a-version") is None
