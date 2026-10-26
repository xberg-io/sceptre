"""Fail-closed comparability controls for release benchmark measurements."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from sceptre_rs_tools import release_benchmark as paired


def sample_pair() -> tuple[dict, dict]:
    environment = {
        "os": "Linux",
        "arch": "x86_64",
        "runner_label": "ubuntu-latest",
        "cpu_count": 4,
        "platform": "Linux-test",
        "backend": "ort",
        "accelerator": "cpu",
        "onnxruntime": {"version": "1.24.2", "providers": ["CPUExecutionProvider"]},
        "models": [{"name": "craft", "sha256": "a" * 64}],
        "corpus": {"resolved": True, "images": {"sample": "b" * 64}},
        "reference": {"easyocr_version": "1.7.2"},
    }
    report = {
        "metadata": {"environment": environment, "threads": 2, "repeats": 2, "group": "all", "corpus_total": 1},
        "records": [{"stem": "sample", "group": "labeled", "skipped": None, "sceptre_token_f1": 1.0}],
    }
    baseline, candidate = copy.deepcopy(report), copy.deepcopy(report)
    baseline["metadata"]["environment"]["sceptre_version"] = "0.8.1"
    candidate["metadata"]["environment"]["sceptre_version"] = "0.8.2"
    return baseline, candidate


def test_pair_preserves_independently_observed_versions() -> None:
    baseline, candidate = sample_pair()
    paired.validate_pair(baseline, candidate, {"sample": "b" * 64}, "0.8.1", "0.8.2")
    assert baseline["metadata"]["environment"]["sceptre_version"] == "0.8.1"


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("version", "version"),
        ("host", "host"),
        ("threads", "threads"),
        ("model", "models"),
        ("runtime", "onnxruntime"),
        ("provider", "onnxruntime"),
        ("config", "group"),
        ("corpus", "corpus"),
        ("missing-row", "records"),
        ("duplicate-row", "records"),
        ("empty-rows", "records"),
        ("missing-model", "models"),
        ("missing-runtime", "onnxruntime"),
    ],
)
def test_pair_rejects_noncomparable_inputs(change: str, reason: str) -> None:
    baseline, candidate = sample_pair()
    changes = {
        "version": (("metadata", "environment", "sceptre_version"), "0.8.1"),
        "host": (("metadata", "environment", "runner_label"), "other"),
        "threads": (("metadata", "threads"), 4),
        "model": (("metadata", "environment", "models", 0, "sha256"), "c" * 64),
        "runtime": (("metadata", "environment", "onnxruntime", "version"), "1.25.0"),
        "provider": (("metadata", "environment", "onnxruntime", "providers"), ["CUDAExecutionProvider"]),
        "config": (("metadata", "group"), "labeled"),
        "corpus": (("metadata", "environment", "corpus", "images", "sample"), "c" * 64),
        "duplicate-row": (("records",), candidate["records"] * 2),
        "missing-model": (("metadata", "environment", "models"), []),
        "missing-runtime": (("metadata", "environment", "onnxruntime"), None),
        "missing-row": (("records",), []),
        "empty-rows": (("records",), []),
    }
    path, value = changes[change]
    target = candidate
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError, match=reason):
        paired.validate_pair(baseline, candidate, {"sample": "b" * 64}, "0.8.1", "0.8.2")


def test_binary_checksum_rejects_wrong_expected_digest(tmp_path: Path) -> None:
    binary = tmp_path / "sceptre"
    binary.write_bytes(b"genuine fixture bytes")
    with pytest.raises(ValueError, match="SHA256"):
        paired.verify_binary(binary, "0" * 64)


def test_identical_binaries_are_rejected() -> None:
    with pytest.raises(ValueError, match="same binary"):
        paired.require_distinct("a" * 64, "a" * 64)


def scored_pair() -> tuple[dict, dict]:
    baseline, candidate = sample_pair()
    for report in (baseline, candidate):
        report["metadata"].update(
            {
                "sceptre_batch": {"english": {"total_seconds": 1.0, "image_count": 1, "rss_mb": 100.0}},
                "easyocr_batch": {"english": {"total_seconds": 2.0, "image_count": 1}},
                "labeled_scored": 1,
                "breadth_scored": 0,
            }
        )
        report["records"][0].update(
            {"languages": ["english"], "sceptre_rss_mb": 100.0, "easyocr_rss_mb": 200.0, "sceptre_cold_seconds": 1.0}
        )
        report["aggregates"] = {"labeled": {}, "all": {}}
    return baseline, candidate


def test_unchanged_real_thresholds_accept_equal_measurements() -> None:
    baseline, candidate = scored_pair()
    assert paired._gate(baseline, candidate) == []


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("slow", "throughput"),
        ("rss", "RSS"),
        ("no-rss", "RSS"),
        ("no-speed", "throughput"),
        ("quality", "token-F1"),
        ("no-contract", "contracts"),
    ],
)
def test_unchanged_thresholds_reject_measurement_failures(change: str, reason: str) -> None:
    baseline, candidate = scored_pair()
    if change == "slow":
        candidate["metadata"]["sceptre_batch"]["english"]["total_seconds"] = 2.0
    elif change == "rss":
        candidate["metadata"]["sceptre_batch"]["english"]["rss_mb"] = 111.0
    elif change == "no-rss":
        candidate["metadata"]["sceptre_batch"]["english"].pop("rss_mb")
    elif change == "no-speed":
        candidate["metadata"]["sceptre_batch"] = {}
    elif change == "quality":
        candidate["records"][0]["sceptre_token_f1"] = 0.89
    elif change == "no-contract":
        baseline["records"][0].pop("sceptre_token_f1")
    assert any(reason.lower() in problem.lower() for problem in paired._gate(baseline, candidate))


def test_selectors_preserve_existing_cli_defaults() -> None:
    from sceptre_rs_tools import benchmark

    default = benchmark.parse_args([])
    assert default.binary is None
    assert default.published_baseline is None
    selected = benchmark.parse_args(["--binary", "/tmp/old", "--published-baseline", "/tmp/real.json"])
    assert str(selected.binary) == "/tmp/old"
    assert str(selected.published_baseline) == "/tmp/real.json"


def test_baseline_payload_retains_observed_old_version() -> None:
    from sceptre_rs_tools.publish import published_payload

    baseline, _ = scored_pair()
    assert published_payload(baseline)["environment"]["sceptre_version"] == "0.8.1"


@pytest.mark.parametrize(
    ("name", "kind", "mode", "size", "reason"),
    [
        ("../sceptre", "file", 0o755, 3, "path"),
        ("/tmp/sceptre", "file", 0o755, 3, "path"),
        ("sceptre", "symlink", 0o755, 0, "link"),
        ("sceptre", "file", 0o4755, 3, "privileged"),
        ("sceptre", "file", 0o755, 300 * 1024 * 1024, "oversized"),
    ],
)
def test_archive_member_selection_rejects_unsafe_inputs(
    name: str, kind: str, mode: int, size: int, reason: str
) -> None:
    import tarfile

    member = tarfile.TarInfo(name)
    member.mode, member.size = mode, size
    if kind == "symlink":
        member.type = tarfile.SYMTYPE
    with pytest.raises(ValueError, match=reason):
        paired._binary_member([member])


def test_archive_member_selection_rejects_duplicate_binary() -> None:
    import tarfile

    with pytest.raises(ValueError, match="exactly one"):
        paired._binary_member([tarfile.TarInfo("sceptre"), tarfile.TarInfo("duplicate/sceptre")])


def test_archive_member_selection_accepts_only_known_regular_binary() -> None:
    import tarfile

    member = tarfile.TarInfo("./sceptre")
    member.mode, member.size = 0o755, 3
    assert paired._binary_member([member]) is member


@pytest.mark.parametrize("fail_quality", [False, True])
def test_serial_measurement_preserves_both_reports_and_failure_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_quality: bool
) -> None:
    import argparse
    import json

    from sceptre_rs_tools import benchmark

    baseline, candidate = scored_pair()
    if fail_quality:
        candidate["records"][0]["sceptre_token_f1"] = 0.8
    old_binary, new_binary = tmp_path / "old", tmp_path / "new"
    old_binary.write_bytes(b"unit-test old executable identity")
    new_binary.write_bytes(b"unit-test new executable identity")
    args = argparse.Namespace(
        output=tmp_path / "result",
        baseline_binary=old_binary,
        candidate_binary=new_binary,
        baseline_sha256=paired.digest(old_binary),
        candidate_sha256=paired.digest(new_binary),
        baseline_archive=tmp_path / "archive-fixture",
        candidate_revision="revision-fixture",
        candidate_version="0.8.2",
        threads=2,
        repeats=2,
    )
    monkeypatch.setattr(benchmark, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(paired, "verify_release_archive", lambda *_: {"source_revision": "baseline-fixture"})
    monkeypatch.setattr(paired, "configuration_manifest", lambda *_: {"config": "same-fixture-bytes"})
    monkeypatch.setattr(paired.subprocess, "check_output", lambda *_, **__: "revision-fixture\n")
    inputs = {"sample": {"image_sha256": "b" * 64, "group": "labeled", "languages": ["english"]}}
    monkeypatch.setattr(paired, "input_manifest", lambda *_: inputs)
    monkeypatch.setattr(benchmark, "build_corpus", lambda *_, **__: [])
    monkeypatch.setattr(
        benchmark,
        "_sceptre_environment",
        lambda binary, *_: (
            baseline["metadata"]["environment"] if binary == old_binary else candidate["metadata"]["environment"]
        ),
    )
    monkeypatch.setattr(paired, "model_manifest", lambda *_: {"model": "same-fixture-bytes"})
    order = []

    def measure(binary: Path, output: Path, *_: object) -> dict:
        order.append(binary)
        output.mkdir()
        report = baseline if binary == old_binary else candidate
        (output / "comparison.json").write_text(json.dumps(report))
        return report

    monkeypatch.setattr(paired, "_measure", measure)
    assert paired.compare(args) == int(fail_quality)
    assert order == [old_binary, new_binary]
    assert json.loads((args.output / "gate.json").read_text())["passed"] is not fail_quality
    assert (
        json.loads((args.output / "baseline-published.json").read_text())["environment"]["sceptre_version"] == "0.8.1"
    )
    hashes = json.loads((args.output / "artifact-sha256.json").read_text())
    assert {"baseline/comparison.json", "candidate/comparison.json", "manifest.json", "gate.json"} <= set(hashes)
    assert all(paired.digest(args.output / name) == checksum for name, checksum in hashes.items())
