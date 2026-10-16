"""Exercise published-archive acceptance with real local protocol children."""

import asyncio
import hashlib
import http.server
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


class PublishedReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "scripts"))
        self.addCleanup(sys.path.remove, str(root / "scripts"))
        spec = importlib.util.spec_from_file_location("published_release", root / "scripts/verify_published_release.py")
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_require_one_exact_checksum_and_reject_corrupt_bytes(self) -> None:
        archive = self.root / "sceptre-test.zip"
        archive.write_bytes(b"archive")
        digest = hashlib.sha256(b"archive").hexdigest()
        row = f"{digest}  {archive.name}\n"
        self.assertEqual(self.module.verify_checksum(archive, row), digest)
        for invalid in ["", row + row, row.replace(digest, "0" * 64), row.replace(archive.name, "other.zip")]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.module.verify_checksum(archive, invalid)

    def test_should_count_four_facts_and_reject_wrong_or_empty_ocr(self) -> None:
        lines = {"lines": [{"text": "Cedar supplied 17 widgets."}]}
        result = {"structuredContent": lines, "content": [{"type": "text", "text": json.dumps(lines)}]}
        self.assertEqual(self.module.validate_ocr(result), 4)
        for invalid in [
            {**result, "isError": True},
            {**result, "structuredContent": {"lines": []}},
            {**result, "structuredContent": {"lines": [{"text": "Cedar supplied 18 widgets."}]}},
            {**result, "content": []},
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.module.validate_ocr(invalid)

    def server(self, mode: str) -> list[str]:
        server = self.root / "server.py"
        server.write_text(
            "import json,sys,time\n"
            f"mode={mode!r}\n"
            "for line in sys.stdin:\n"
            " q=json.loads(line)\n"
            " if 'id' not in q: continue\n"
            " if mode=='timeout': time.sleep(30)\n"
            " if q['method']=='initialize':\n"
            "  r={'protocolVersion':'2024-11-05','capabilities':{'tools':{}}}\n"
            " elif q['method']=='tools/list':\n"
            "  schema={'required':['image_path'],'properties':{'image_path':{'type':'string'}}}\n"
            "  tools=[{'name':'readtext','inputSchema':schema}]\n"
            "  if mode=='missing': tools=[]\n"
            "  if mode=='extra': tools.append({'name':'surprise'})\n"
            "  r={'tools':tools}\n"
            " else:\n"
            "  data={'lines':[{'text':'Cedar supplied 17 widgets.'}]}\n"
            "  if mode=='wrong-fact': data['lines'][0]['text']='Cedar supplied 18 widgets.'\n"
            "  r={'structuredContent':data,'content':[{'type':'text','text':json.dumps(data)}]}\n"
            "  if mode=='error': r['isError']=True\n"
            " print(json.dumps({'jsonrpc':'2.0','id':q['id'],'result':r}),flush=True)\n"
        )
        return [sys.executable, str(server)]

    def test_should_execute_initialize_list_and_real_tools_call(self) -> None:
        proof = asyncio.run(self.module.check_mcp(self.server("valid"), self.root / "image.png", self.root, {}, 2))
        self.assertEqual(proof["actual_facts"], 4)
        self.assertEqual(proof["tool_names"], ["readtext"])
        self.assertEqual(proof["actual_native_ocr_calls"], 1)
        self.assertEqual(set(proof["responses"]), {"initialize", "tools/list", "tools/call"})

    def test_should_reject_empty_extra_tools_errors_wrong_facts_and_timeout(self) -> None:
        for mode in ["missing", "extra", "error", "wrong-fact", "timeout"]:
            with self.subTest(mode=mode), self.assertRaises((ValueError, TimeoutError)):
                asyncio.run(self.module.check_mcp(self.server(mode), self.root / "image.png", self.root, {}, 0.2))

    def test_should_reap_real_child_when_protocol_evidence_cannot_be_written(self) -> None:
        async def exercise(mode: str) -> None:
            observed = []
            create = asyncio.create_subprocess_exec

            async def capture(*args: str, **kwargs: object) -> asyncio.subprocess.Process:
                process = await create(*args, **kwargs)
                observed.append(process)
                return process

            with patch.object(asyncio, "create_subprocess_exec", side_effect=capture):
                try:
                    with self.assertRaises((IsADirectoryError, PermissionError)) as caught:
                        await self.module.check_mcp(self.server(mode), self.root / "image.png", self.root, {}, 0.1)
                    self.assertEqual(len(observed), 1)
                    self.assertIsNotNone(observed[0].returncode, "proof-write failure leaked the real native child")
                    if mode == "timeout":
                        self.assertIsInstance(caught.exception.__context__, TimeoutError)
                finally:
                    for process in observed:
                        if process.returncode is None:
                            process.kill()
                        await process.wait()

        (self.root / "protocol.json").mkdir()
        for mode in ["valid", "timeout"]:
            with self.subTest(mode=mode):
                asyncio.run(exercise(mode))

    def test_should_validate_pinned_cache_on_every_hit(self) -> None:
        target = self.root / "model.onnx"
        target.write_bytes(b"model")
        digest = hashlib.sha256(b"model").hexdigest()
        self.module.cached_download("https://invalid.example/model", target, digest)
        with self.assertRaisesRegex(ValueError, "sha256"):
            self.module.cached_download("https://invalid.example/model", target, "0" * 64)

    def test_should_download_actual_http_bytes_and_enforce_size_limit(self) -> None:
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"published-model")

            def log_message(self, *_args: object) -> None:
                pass

        with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/model"
                target = self.root / "downloaded.onnx"
                digest = hashlib.sha256(b"published-model").hexdigest()
                self.module.cached_download(url, target, digest)
                self.assertEqual(target.read_bytes(), b"published-model")
                with self.assertRaisesRegex(ValueError, "exceeded"):
                    self.module.download(url, self.root / "oversized", limit=2)
                self.assertFalse((self.root / "oversized").exists())
            finally:
                server.shutdown()
                thread.join(timeout=2)

    def test_should_check_packaged_version_and_four_platform_census(self) -> None:
        self.assertEqual(len(self.module.PLATFORMS), 4)
        self.module.validate_version("sceptre 0.8.1\n", "0.8.1")
        with self.assertRaisesRegex(ValueError, "version"):
            self.module.validate_version("sceptre 0.8.0\n", "0.8.1")

    def test_should_reject_unrecognized_platform_or_injected_version(self) -> None:
        for version, triple in [("../0.8.1", "x86_64-unknown-linux-gnu"), ("0.8.1", "invented")]:
            with self.subTest(version=version, triple=triple), self.assertRaises(ValueError):
                self.module.release_asset(version, triple)


if __name__ == "__main__":
    unittest.main()
