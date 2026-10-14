"""Check the version and MCP protocol of the binary inside a release archive."""

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def unpack_binary(archive: Path, destination: Path) -> Path:
    """Extract regular root files while rejecting links and escaping archive paths."""
    destination.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as handle:
            for member in handle.infolist():
                name = archive_name(member.filename)
                if not member.is_dir():
                    (destination / name).write_bytes(handle.read(member))
        binary = destination / "sceptre.exe"
    else:
        with tarfile.open(archive, "r:gz") as handle:
            for member in handle.getmembers():
                name = archive_name(member.name)
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError(f"Unsafe archive member: {member.name}")
                source = handle.extractfile(member)
                if source is None:
                    raise ValueError(f"Unreadable archive member: {member.name}")
                with source, (destination / name).open("wb") as output:
                    shutil.copyfileobj(source, output)
                (destination / name).chmod(member.mode & 0o777)
        binary = destination / "sceptre"
    if not binary.is_file():
        raise ValueError(f"Release archive has no {binary.name} binary: {archive}")
    return binary.resolve()


def archive_name(name: str) -> str:
    """Allow only root-level files emitted by the release packager."""
    path = PurePosixPath(name)
    if path.is_absolute() or len(path.parts) > 1 or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe archive member: {name}")
    return path.name


async def receive(process: asyncio.subprocess.Process, request_id: int, timeout: float) -> dict:
    """Require a matching successful JSON-RPC response before the deadline."""
    assert process.stdout is not None
    line = await asyncio.wait_for(process.stdout.readline(), timeout=timeout)
    if not line:
        raise ValueError(f"MCP server closed stdout before response id {request_id}")
    try:
        response = json.loads(line)
    except json.JSONDecodeError as error:
        raise ValueError(f"MCP stdout is not JSON: {line!r}") from error
    if not isinstance(response, dict):
        raise TypeError(f"MCP response is not an object: {response}")
    if response.get("jsonrpc") != "2.0" or response.get("id") != request_id:
        raise ValueError(f"Unexpected JSON-RPC response id: {response}")
    if "error" in response:
        raise ValueError(f"MCP protocol error: {response['error']}")
    result = response.get("result")
    if not isinstance(result, dict):
        raise TypeError(f"MCP response has no result object: {response}")
    return result


async def send(process: asyncio.subprocess.Process, message: dict) -> None:
    """Flush one newline-delimited JSON-RPC message to the server."""
    assert process.stdin is not None
    process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}).encode() + b"\n")
    await process.stdin.drain()


async def discover(process: asyncio.subprocess.Process, timeout: float) -> int:
    """Initialize the MCP session and verify the public OCR tool schema."""
    await send(
        process,
        {
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "sceptre-release-smoke", "version": "1"},
            },
        },
    )
    initialized = await receive(process, 1, timeout)
    if not initialized.get("protocolVersion") or "tools" not in initialized.get("capabilities", {}):
        raise ValueError(f"MCP initialization did not advertise tools: {initialized}")
    await send(process, {"method": "notifications/initialized"})
    await send(process, {"id": 2, "method": "tools/list", "params": {}})
    result = await receive(process, 2, timeout)
    tools = result.get("tools", [])
    readtext = next((tool for tool in tools if tool.get("name") == "readtext"), None)
    if readtext is None:
        raise ValueError(f"MCP tools/list did not expose readtext: {result}")
    schema = readtext.get("inputSchema", {})
    if "image_path" not in schema.get("required", []):
        raise ValueError(f"readtext schema does not require image_path: {schema}")
    if schema.get("properties", {}).get("image_path", {}).get("type") != "string":
        raise ValueError(f"readtext image_path schema is not a string: {schema}")
    return len(tools)


async def smoke_mcp(command: list[str], timeout: float = 30) -> int:
    """Run protocol discovery with bounded waits and always reap the child process."""
    with tempfile.TemporaryFile() as stderr:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=stderr,
        )
        try:
            return await discover(process, timeout)
        except (ValueError, TypeError, TimeoutError, ConnectionError) as error:
            stderr.seek(0)
            diagnostic = stderr.read().decode(errors="replace")
            error.add_note(f"MCP stderr: {diagnostic}")
            raise
        finally:
            if process.returncode is None:
                process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()
                await process.wait()


def main() -> None:
    """Smoke-test the extracted executable rather than the build-tree original."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--version", required=True)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="sceptre-release-smoke-") as directory:
        binary = unpack_binary(arguments.archive, Path(directory))
        version = subprocess.run([str(binary), "--version"], check=True, text=True, capture_output=True, timeout=30)
        expected = f"sceptre {arguments.version}"
        if version.stdout.strip() != expected:
            raise ValueError(f"Packaged version mismatch: expected {expected!r}, got {version.stdout!r}")
        count = asyncio.run(smoke_mcp([str(binary), "mcp"]))
        sys.stdout.write(
            f"Verified {arguments.archive}: {expected}; MCP initialization and {count} tool(s), including readtext\n"
        )


if __name__ == "__main__":
    main()
