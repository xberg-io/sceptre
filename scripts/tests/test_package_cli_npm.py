import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "release"))

import package_cli_npm as pkg  # noqa: E402

VERSION = "0.10.1"
MANIFEST = {
    "name": pkg.ROOT_PACKAGE,
    "version": VERSION,
    "license": "MIT",
    "author": {"name": "x"},
    "repository": {"type": "git", "url": "u"},
}


def write_tar(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as tf:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


def write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


class PackageCliNpmTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.archives = tmp / "archives"
        self.archives.mkdir()
        self.out = tmp / "out"
        self.manifest = tmp / "package.json"
        self.manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")

    def add_all(self) -> None:
        for target in pkg.TARGETS:
            archive = self.archives / target.archive
            members = {"./": b"", f"./{target.binary}": b"binary-" + target.suffix.encode()}
            if target.os == "win32":
                write_zip(archive, {target.binary: members[f"./{target.binary}"]})
            else:
                write_tar(archive, {f"./{target.binary}": members[f"./{target.binary}"]})

    def write_sums(self, overrides: dict[str, str] | None = None, skip: str | None = None) -> None:
        lines = []
        for path in sorted(self.archives.iterdir()):
            if path.name == skip:
                continue
            digest = (overrides or {}).get(path.name) or hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.name}")
        (self.archives / pkg.sums_name(VERSION)).write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_package(self) -> tuple[list[str], list[str]]:
        return pkg.package_all(self.archives, VERSION, self.out, self.manifest)

    def test_targets_are_exactly_the_four_release_builds(self) -> None:
        self.assertEqual(
            sorted(t.suffix for t in pkg.TARGETS), ["darwin-arm64", "linux-arm64-gnu", "linux-x64-gnu", "win32-x64"]
        )
        self.assertEqual(pkg.sums_name("0.10.1"), "sceptre_0.10.1_checksums.txt")

    def test_packages_every_archive_and_pins_the_root_optional_dependencies(self) -> None:
        self.add_all()
        self.write_sums()
        built, skipped = self.run_package()
        self.assertEqual(len(built), 4)
        self.assertEqual(skipped, [])
        root = json.loads((self.out / "root" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(root["optionalDependencies"], dict.fromkeys(sorted(built), VERSION))
        linux = json.loads((self.out / "linux-x64-gnu" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual((linux["os"], linux["cpu"], linux["libc"]), (["linux"], ["x64"], ["glibc"]))
        self.assertEqual((self.out / "linux-x64-gnu" / "bin" / "sceptre").read_bytes(), b"binary-linux-x64-gnu")
        self.assertTrue((self.out / "win32-x64" / "bin" / "sceptre.exe").is_file())

    def test_a_missing_archive_is_skipped_and_reported(self) -> None:
        self.add_all()
        (self.archives / "sceptre-aarch64-apple-darwin.tar.gz").unlink()
        self.write_sums()
        built, skipped = self.run_package()
        self.assertEqual(len(built), 3)
        self.assertEqual(skipped, [f"{pkg.ROOT_PACKAGE}-darwin-arm64"])

    def test_a_tampered_archive_is_refused(self) -> None:
        self.add_all()
        self.write_sums(overrides={"sceptre-aarch64-apple-darwin.tar.gz": "0" * 64})
        with self.assertRaisesRegex(pkg.PackagingError, "checksum mismatch"):
            self.run_package()

    def test_an_archive_without_a_checksum_entry_is_refused(self) -> None:
        self.add_all()
        self.write_sums(skip="sceptre-x86_64-pc-windows-msvc.zip")
        with self.assertRaisesRegex(pkg.PackagingError, "no entry"):
            self.run_package()

    def test_a_missing_checksum_file_is_refused(self) -> None:
        self.add_all()
        with self.assertRaisesRegex(pkg.PackagingError, "not found"):
            self.run_package()

    def test_an_archive_without_the_binary_is_refused(self) -> None:
        self.add_all()
        write_tar(self.archives / "sceptre-aarch64-apple-darwin.tar.gz", {"./README.md": b"x"})
        self.write_sums()
        with self.assertRaisesRegex(pkg.PackagingError, "does not contain sceptre"):
            self.run_package()

    def test_a_path_traversal_member_is_refused(self) -> None:
        self.add_all()
        write_tar(self.archives / "sceptre-aarch64-apple-darwin.tar.gz", {"../sceptre": b"x"})
        self.write_sums()
        with self.assertRaisesRegex(pkg.PackagingError, "unsafe archive member"):
            self.run_package()

    def test_no_archives_at_all_is_an_error(self) -> None:
        self.write_sums()
        with self.assertRaisesRegex(pkg.PackagingError, "nothing to package"):
            self.run_package()

    def test_a_malformed_version_is_refused(self) -> None:
        with self.assertRaisesRegex(pkg.PackagingError, "invalid version"):
            pkg.package_all(self.archives, "latest", self.out, self.manifest)


if __name__ == "__main__":
    unittest.main()
