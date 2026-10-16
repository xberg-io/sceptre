"""Verify published native archives through real MCP OCR without rebuilding them."""

import argparse
import asyncio
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from smoke_release import receive, send, unpack_binary

PLATFORMS = {
    "x86_64-unknown-linux-gnu": ("Linux", {"x86_64", "amd64"}),
    "aarch64-unknown-linux-gnu": ("Linux", {"aarch64", "arm64"}),
    "aarch64-apple-darwin": ("Darwin", {"aarch64", "arm64"}),
    "x86_64-pc-windows-msvc": ("Windows", {"x86_64", "amd64"}),
}
MODELS = (
    (
        "craft_mlt_25k",
        "5569f7c684f6a0718aaad1c3d994ab8585b50df9",
        "159f5ffecde90d567f54da3e449fb0eba54a1da791c429c3509984dcfd7f684e",
    ),
    (
        "english_g2",
        "11f8e6857741ac8e7151a327c5a4b0030edafa84",
        "29ef336a7ad835d3e16eb70f23973d0fefd7a81fe6070845850954fe1cece0db",
    ),
)
FIXTURE_SHA256 = "385b4cd54423a2d61c44d266d5c6e206c96a34b9f4281fe47f247f6b07012c4c"


def sha256(path: Path) -> str:
    """Hash bytes without retaining large model files in memory."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def release_asset(version: str, triple: str) -> str:
    """Reject path injection and unsupported platform names before downloading."""
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-rc\.\d+)?", version) or triple not in PLATFORMS:
        raise ValueError("Expected a release version and a supported target triple")
    extension = "zip" if triple.endswith("windows-msvc") else "tar.gz"
    return f"sceptre-{triple}.{extension}"


def download(url: str, destination: Path, limit: int = 200_000_000) -> None:
    """Download bounded public bytes with socket timeouts and atomic replacement."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "sceptre-release-verification"})
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > limit:
                        raise ValueError(f"Download exceeded {limit} bytes")
                    temporary.write(chunk)
            temporary.close()
            temporary_path.replace(destination)
        finally:
            temporary.close()
            temporary_path.unlink(missing_ok=True)


def verify_checksum(archive: Path, checksums: str) -> str:
    """Require exactly one checksum for this archive and check its actual bytes."""
    rows = [line.split() for line in checksums.splitlines() if line.strip()]
    matches = [row[0] for row in rows if len(row) == 2 and row[1].removeprefix("*") == archive.name]
    if len(matches) != 1 or not re.fullmatch(r"[0-9a-f]{64}", matches[0]):
        raise ValueError("Expected exactly one valid archive checksum")
    actual = sha256(archive)
    if actual != matches[0]:
        raise ValueError(f"Archive sha256 mismatch: {archive.name}")
    return actual


def cached_download(url: str, target: Path, expected: str) -> None:
    """Rehash cache hits and fail closed on corruption rather than infer freshness."""
    if not target.exists():
        download(url, target)
    if sha256(target) != expected:
        raise ValueError(f"Model sha256 mismatch: {target.name}")


def prepare_models(cache: Path) -> list[dict]:
    """Seed the immutable snapshot layout consumed by the released library."""
    rows = []
    for name, revision, digest in MODELS:
        relative = Path(f"models--xberg-io--sceptre-{name}") / "snapshots" / revision / f"{name}.onnx"
        target = cache / relative
        cached_download(
            f"https://huggingface.co/xberg-io/sceptre-{name}/resolve/{revision}/{name}.onnx", target, digest
        )
        rows.append({"name": name, "revision": revision, "sha256": digest, "bytes": target.stat().st_size})
    return rows


def validate_ocr(result: dict) -> int:
    """Require agreement between structured/text content and four exact OCR facts."""
    if result.get("isError"):
        raise ValueError("readtext returned an error")
    structured = result.get("structuredContent", {})
    lines = structured.get("lines", [])
    if not lines:
        raise ValueError("readtext returned no structured OCR lines")
    text = " ".join(line.get("text", "") for line in lines)
    content = result.get("content", [])
    decoded = [json.loads(item["text"]) for item in content if item.get("type") == "text"]
    if decoded != [structured]:
        raise ValueError("Text and structured OCR results disagree")
    facts = ["Cedar", "supplied", "17", "widgets"]
    actual = sum(fact in re.findall(r"\w+", text) for fact in facts)
    if text != "Cedar supplied 17 widgets." or actual != 4:
        raise ValueError(f"Expected 4 OCR facts, got {actual}: {text!r}")
    return actual


async def exchange(process: asyncio.subprocess.Process, fixture: Path, responses: dict, timeout: float) -> dict:
    """Exercise discovery and exactly one public OCR request over the real wire."""
    await send(
        process,
        {
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "sceptre-published-verifier", "version": "1"},
            },
        },
    )
    initialized = await receive(process, 1, timeout)
    responses["initialize"] = initialized
    if not initialized.get("protocolVersion") or "tools" not in initialized.get("capabilities", {}):
        raise ValueError("MCP initialization did not advertise tools")
    await send(process, {"method": "notifications/initialized"})
    await send(process, {"id": 3, "method": "tools/list", "params": {}})
    listed = await receive(process, 3, timeout)
    names = [tool.get("name") for tool in listed.get("tools", [])]
    if names != ["readtext"]:
        raise ValueError(f"Expected exactly one readtext tool, got {names}")
    schema = listed["tools"][0].get("inputSchema", {})
    if (
        "image_path" not in schema.get("required", [])
        or schema.get("properties", {}).get("image_path", {}).get("type") != "string"
    ):
        raise ValueError("readtext requires a string image_path")
    responses["tools/list"] = listed
    await send(
        process,
        {"id": 4, "method": "tools/call", "params": {"name": "readtext", "arguments": {"image_path": str(fixture)}}},
    )
    result = await receive(process, 4, timeout)
    responses["tools/call"] = result
    actual = validate_ocr(result)
    return {"expected_facts": 4, "actual_facts": actual, "tool_names": names, "actual_native_ocr_calls": 1}


async def check_mcp(command: list[str], fixture: Path, output: Path, env: dict, timeout: float = 120) -> dict:
    """Bound protocol waits and always stop/reap the native subprocess."""
    output.mkdir(parents=True, exist_ok=True)
    responses = {}
    with (output / "native-stderr.log").open("wb") as stderr:
        process = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=stderr, env=env or None
        )
        try:
            proof = await exchange(process, fixture, responses, timeout)
            return {**proof, "responses": responses}
        finally:
            try:
                (output / "protocol.json").write_text(json.dumps(responses, indent=2), encoding="utf-8")
            finally:
                if process.returncode is None:
                    process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except TimeoutError:
                    process.kill()
                    await process.wait()


def validate_version(stdout: str, expected: str) -> None:
    """Reject an archive that reports a different package version."""
    if stdout.strip() != f"sceptre {expected}":
        raise ValueError(f"Unexpected packaged version: {stdout!r}")


def verify(arguments: argparse.Namespace) -> dict:
    """Check downloaded release bytes on their matching native host."""
    asset = release_asset(arguments.version, arguments.triple)
    system, architectures = PLATFORMS[arguments.triple]
    if platform.system() != system or platform.machine().lower() not in architectures:
        raise ValueError(f"Native host does not match {arguments.triple}")
    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = f"https://github.com/xberg-io/sceptre/releases/download/v{arguments.version}"
    archive = output / asset
    checksums = output / f"sceptre_{arguments.version}_checksums.txt"
    download(f"{base}/{asset}", archive)
    download(f"{base}/{checksums.name}", checksums, 100_000)
    digest = verify_checksum(archive, checksums.read_text(encoding="utf-8"))
    fixture = Path(__file__).parent / "fixtures/release-ocr.png"
    if sha256(fixture) != FIXTURE_SHA256:
        raise ValueError("Synthetic OCR fixture sha256 mismatch")
    models = prepare_models(arguments.cache.resolve())
    binary = unpack_binary(archive, output / "native")
    version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, check=True, timeout=30)
    validate_version(version.stdout, arguments.version)
    env = os.environ.copy()
    env.update(HF_HUB_CACHE=str(arguments.cache.resolve()), HF_HUB_OFFLINE="1")
    env.update(dict.fromkeys(("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"), "http://127.0.0.1:1"))
    protocol = asyncio.run(check_mcp([str(binary), "mcp", "--lang", "english", "--threads", "2"], fixture, output, env))
    return {
        **protocol,
        "version": version.stdout.strip(),
        "triple": arguments.triple,
        "archive_sha256": digest,
        "binary_sha256": sha256(binary),
        "fixture_sha256": FIXTURE_SHA256,
        "models": models,
        "native_host": {"system": platform.system(), "machine": platform.machine()},
        "verification_source_sha": os.environ.get("GITHUB_SHA"),
        "offline_native_inference": True,
    }


def main() -> None:
    """Download, verify, exercise and record the exact published native artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        default=os.environ.get("VERIFY_RELEASE_VERSION"),
        required="VERIFY_RELEASE_VERSION" not in os.environ,
    )
    parser.add_argument(
        "--triple", default=os.environ.get("VERIFY_RELEASE_TRIPLE"), required="VERIFY_RELEASE_TRIPLE" not in os.environ
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("VERIFY_RELEASE_OUTPUT"),
        required="VERIFY_RELEASE_OUTPUT" not in os.environ,
        type=Path,
    )
    parser.add_argument(
        "--cache",
        default=os.environ.get("VERIFY_RELEASE_MODEL_CACHE"),
        required="VERIFY_RELEASE_MODEL_CACHE" not in os.environ,
        type=Path,
    )
    arguments = parser.parse_args()
    proof = verify(arguments)
    (arguments.output / "proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    sys.stdout.write(f"Verified {arguments.triple}: {proof['actual_native_ocr_calls']} native OCR call; 4/4 facts\n")


if __name__ == "__main__":
    main()
