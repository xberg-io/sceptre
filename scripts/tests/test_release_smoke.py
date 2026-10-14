"""Prove the release gate checks protocol responses and extracted archive bytes."""

import asyncio
import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path


class ReleaseSmokeTests(unittest.TestCase):
    """Exercise the harness with child processes and real disposable archives."""

    def setUp(self) -> None:
        """Load the release gate and give each test its own filesystem."""
        root = Path(__file__).resolve().parents[2]
        spec = importlib.util.spec_from_file_location("release_smoke", root / "scripts/smoke_release.py")
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        directory = tempfile.TemporaryDirectory(prefix="release-smoke-test-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def server(self, mode: str) -> list[str]:
        """Run a protocol fixture in a separate process to test wire failures."""
        path = self.root / "server.py"
        path.write_text(
            "import json, sys, time\n"
            f"mode = {mode!r}\n"
            "for line in sys.stdin:\n"
            "    request = json.loads(line)\n"
            "    if 'id' not in request:\n        continue\n"
            "    if mode == 'timeout':\n        time.sleep(30)\n"
            "    if mode == 'garbage':\n        print('diagnostic on stdout', flush=True)\n        continue\n"
            "    if request['method'] == 'initialize':\n"
            "        result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}}, "
            "'serverInfo': {'name': 'fixture', 'version': '1'}}\n"
            "    else:\n"
            "        schema = {'type': 'object', 'required': ['image_path'], "
            "'properties': {'image_path': {'type': 'string'}}}\n"
            "        result = {'tools': [{'name': 'readtext', 'inputSchema': schema}]}\n"
            "        if mode == 'missing-tool':\n            result = {'tools': []}\n"
            "    response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}\n"
            "    if mode == 'error':\n        response = {'jsonrpc': '2.0', 'id': request['id'], "
            "'error': {'code': -32601, 'message': 'unsupported method'}}\n"
            "    if mode == 'wrong-id':\n        response['id'] = 99\n"
            "    print(json.dumps(response), flush=True)\n"
        )
        return [sys.executable, str(path)]

    def test_should_initialize_and_discover_readtext_over_stdio(self) -> None:
        """The positive control executes two requests against a running child."""
        count = asyncio.run(self.module.smoke_mcp(self.server("valid"), timeout=2))
        assert count == 1

    def test_should_reject_protocol_failures_and_empty_discovery(self) -> None:
        """Green cannot mean no tools, an error envelope, or arbitrary stdout."""
        for mode, message in [
            ("missing-tool", "readtext"),
            ("error", "unsupported method"),
            ("garbage", "JSON"),
            ("wrong-id", "response id"),
        ]:
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, message):
                asyncio.run(self.module.smoke_mcp(self.server(mode), timeout=2))

    def test_should_bound_waiting_for_a_silent_server(self) -> None:
        """A nonresponsive packaged binary must fail the job instead of hanging."""
        with self.assertRaises(TimeoutError):
            asyncio.run(self.module.smoke_mcp(self.server("timeout"), timeout=0.1))

    def test_should_extract_exact_binary_bytes_from_tar_and_zip(self) -> None:
        """Both release archive formats feed their extracted binary to the gate."""
        payload = b"packaged-binary-bytes"
        archive = self.root / "release.tar.gz"
        with tarfile.open(archive, "w:gz") as handle:
            member = tarfile.TarInfo("./sceptre")
            member.size = len(payload)
            member.mode = 0o755
            handle.addfile(member, io.BytesIO(payload))
        target = self.root / "tar"
        assert self.module.unpack_binary(archive, target).read_bytes() == payload
        archive = self.root / "release.zip"
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("sceptre.exe", payload)
        assert self.module.unpack_binary(archive, self.root / "zip").read_bytes() == payload

    def test_should_reject_empty_archive_and_escaping_members(self) -> None:
        """A green archive gate must contain a binary and never extract outside."""
        for member, message in [("missing", "binary"), ("../sceptre.exe", "Unsafe")]:
            archive = self.root / f"{member.replace('/', '_')}.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr(member, b"bad")
            with self.assertRaisesRegex(ValueError, message):
                self.module.unpack_binary(archive, self.root / "unpacked")


if __name__ == "__main__":
    unittest.main()
