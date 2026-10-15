"""Exercise the published build script's macOS compiler runtime linkage."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tomllib


class MacosLinkTests(unittest.TestCase):
    """Run the real build script independently of Cargo dependency compilation."""

    def setUp(self) -> None:
        """Give each test its own disposable build script executable."""
        self.repository = Path(__file__).resolve().parents[2]
        directory = tempfile.TemporaryDirectory(prefix="sceptre-macos-link-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        suffix = ".exe" if sys.platform == "win32" else ""
        self.binary = self.root / f"build-script{suffix}"

    def compile_script(self) -> None:
        """Compile the same build script that Cargo executes for consumers."""
        result = subprocess.run(
            ["rustc", "--edition=2024", str(self.repository / "crates/sceptre/build.rs"), "-o", str(self.binary)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_script(self, **overrides: str) -> subprocess.CompletedProcess[str]:
        """Supply Cargo's target/feature inputs without inheriting provisioning state."""
        if not self.binary.exists():
            self.compile_script()
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("CARGO_FEATURE_", "CARGO_CFG_TARGET_", "ORT_")) and key != "CC"
        }
        environment.update(overrides)
        return subprocess.run([str(self.binary)], env=environment, capture_output=True, text=True, check=False)

    @staticmethod
    def link_directives(result: subprocess.CompletedProcess[str]) -> list[str]:
        """Select directives that affect linker arguments from Cargo bookkeeping."""
        return [line for line in result.stdout.splitlines() if line.startswith("cargo:rustc-link-")]

    @unittest.skipUnless(sys.platform == "darwin", "requires the macOS clang compiler runtime")
    def test_should_link_real_compiler_runtime_for_bundled_macos(self) -> None:
        """The linked archive must exist in the compiler's actual runtime directory."""
        compiler = shutil.which("clang")
        self.assertIsNotNone(compiler, "clang is required to verify macOS bundled linkage")
        discovery = subprocess.run(
            [compiler, "--print-file-name=libclang_rt.osx.a"], capture_output=True, text=True, check=False
        )
        self.assertEqual(discovery.returncode, 0, discovery.stderr)
        archive = Path(discovery.stdout.strip())
        self.assertEqual(archive.is_file(), True, str(archive))
        result = self.run_script(CARGO_CFG_TARGET_OS="macos", CARGO_FEATURE_ORT_BUNDLED="1", CC=compiler)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.link_directives(result),
            [f"cargo:rustc-link-search=native={archive.parent}", "cargo:rustc-link-lib=static=clang_rt.osx"],
        )

    def test_should_skip_compiler_discovery_when_runtime_linkage_is_not_needed(self) -> None:
        """Other targets and dynamic or pure Rust builds must not invoke a compiler."""
        for overrides in [
            {"CARGO_CFG_TARGET_OS": "linux", "CARGO_FEATURE_ORT_BUNDLED": "1"},
            {"CARGO_CFG_TARGET_OS": "windows", "CARGO_FEATURE_ORT_BUNDLED": "1"},
            {"CARGO_CFG_TARGET_OS": "macos"},
            {"CARGO_CFG_TARGET_OS": "macos", "CARGO_FEATURE_ORT_DYNAMIC": "1"},
            {"CARGO_CFG_TARGET_OS": "macos", "CARGO_FEATURE_ORT_BUNDLED": "1", "CARGO_FEATURE_ORT_DYNAMIC": "1"},
        ]:
            with self.subTest(overrides=overrides):
                result = self.run_script(CC=str(self.root / "missing-compiler"), **overrides)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.link_directives(result), [])

    def test_should_report_compiler_context_when_runtime_discovery_fails(self) -> None:
        """A missing compiler must fail explicitly before creating broken linker flags."""
        for compiler in [str(self.root / "missing-compiler"), r"Z:\missing-directory\missing-compiler"]:
            with self.subTest(compiler=compiler):
                result = self.run_script(CARGO_CFG_TARGET_OS="macos", CARGO_FEATURE_ORT_BUNDLED="1", CC=compiler)
                self.assertNotEqual(result.returncode, 0)
                # OsString is Debug-formatted inside a String returned by main, escaping twice. ~keep
                self.assertIn(compiler.replace("\\", r"\\\\"), result.stderr)
                self.assertRegex(result.stderr, r"(?i)(discover|locat|query|runtime)")
                self.assertEqual(self.link_directives(result), [])

    def test_should_include_build_script_in_published_library(self) -> None:
        """Crates.io consumers need the workaround as well as repository builds."""
        manifest = self.repository / "crates/sceptre/Cargo.toml"
        package = tomllib.loads(manifest.read_text())["package"]
        self.assertIn("/build.rs", package["include"])


if __name__ == "__main__":
    unittest.main()
