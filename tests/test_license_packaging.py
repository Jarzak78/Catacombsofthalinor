"""Distribution notices fail closed and stay attached to native runtimes."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.collect_licenses import (
    NoticeError, PYTHON_LICENSE_MARKERS, ZLIB_LICENSE_MARKERS, audit_analysis, binary_component,
    collect_notices, copy_notices, require_text, source_bytes, verify_embedded_notices,
)


class NoticePackagingTests(unittest.TestCase):
    def test_incomplete_or_wrong_notice_is_rejected(self):
        for data in (b"", b"<html>Not found</html>", b"Python license"):
            with self.subTest(data=data), self.assertRaises(NoticeError):
                require_text(data, PYTHON_LICENSE_MARKERS, "installed LICENSE.txt")

    def test_verified_upstream_cache_supports_offline_build_but_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            url = "https://example.org/verified-license.txt"
            path = cache / (hashlib.sha256(url.encode()).hexdigest() + ".txt")
            path.write_bytes(b"Copyright: official full license")
            with patch("scripts.collect_licenses.urlopen", side_effect=AssertionError("offline")):
                self.assertEqual(source_bytes(url, cache, ("Copyright", "full license")), path.read_bytes())
                path.write_bytes(b"truncated")
                with self.assertRaises(NoticeError):
                    source_bytes(url, cache, ("Copyright", "full license"))

    def test_collection_preserves_exact_installed_bytes_and_publishes_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            (root / "legal").mkdir(parents=True)
            (root / "CREDITS.txt").write_bytes(b"Systems Reference Document attribution\n")
            (root / "legal" / "README.md").write_bytes(b"Project provenance\n")
            (root / "legal" / "CC-BY-4.0.txt").write_bytes(b"Creative Commons full text fixture\n")
            (root / "legal" / "END_USER_TERMS.txt").write_bytes(b"Microsoft runtime-only terms fixture\n")
            python = Path(temporary) / "python"
            python.mkdir()
            installed = ("\r\n".join(PYTHON_LICENSE_MARKERS) + "\r\nCopyright \u00a9\r\n").encode()
            (python / "LICENSE.txt").write_bytes(installed)
            pyi = Path(temporary) / "pyinstaller"
            hooks = pyi / "hooks" / "rthooks"
            hooks.mkdir(parents=True)
            (hooks / "pyi_rth_fixture.py").write_text(
                "# Copyright upstream author\n# Apache License, Version 2.0\n\nimport sys\n", encoding="utf-8")
            copying = pyi / "COPYING.txt"
            copying.write_bytes(b"Bootloader Exception\r\nApache License\r\n")
            dist = SimpleNamespace(version="6.16.0", files=[PurePosixPath("COPYING.txt")],
                                   locate_file=lambda _path: copying)
            sources = []

            def fetch(url, _cache, _markers):
                sources.append(url)
                if url.endswith("python.props"):
                    return b'<lzmaDir Condition="...">$(ExternalsDir)xz-5.2.5\\</lzmaDir>'
                return ("Full original license from " + url + "\n").encode()

            staged = root / "build" / "license-bundle"
            with patch("scripts.collect_licenses.sys.base_prefix", str(python)), \
                    patch("scripts.collect_licenses.platform.python_version", return_value="3.12.10"), \
                    patch("scripts.collect_licenses.distribution", return_value=dist), \
                    patch("scripts.collect_licenses.source_bytes", side_effect=fetch), \
                    patch.dict("sys.modules", {"PyInstaller": SimpleNamespace(__file__=str(pyi / "__init__.py"))}):
                collect_notices(root, staged)
            self.assertEqual((staged / "legal/runtime/Python-Windows-LICENSE.txt").read_bytes(), installed)
            self.assertEqual((staged / "legal/runtime/PyInstaller-COPYING.txt").read_bytes(), copying.read_bytes())
            self.assertIn("https://raw.githubusercontent.com/python/cpython/v3.12.10/Doc/license.rst", sources)
            self.assertIn("https://raw.githubusercontent.com/python/cpython-source-deps/xz-5.2.5/COPYING", sources)
            manifest = json.loads((staged / "legal/runtime/notice-manifest.json").read_text())
            record = next(row for row in manifest["notice_sources"] if row["path"].endswith("Python-Windows-LICENSE.txt"))
            self.assertEqual(record["sha256"], hashlib.sha256(installed).hexdigest())
            self.assertIn("None", manifest["python_modifications"])
            copy_notices(staged, root / "dist")
            for file in staged.rglob("*"):
                if file.is_file():
                    self.assertEqual(file.read_bytes(), (root / "dist" / file.relative_to(staged)).read_bytes())

    def test_missing_installed_python_notices_fail_before_pyinstaller(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "CREDITS.txt").write_text("credits")
            (root / "legal").mkdir()
            (root / "legal/README.md").write_text("provenance")
            (root / "legal/CC-BY-4.0.txt").write_text("CC BY full text fixture")
            (root / "legal/END_USER_TERMS.txt").write_text("runtime-only terms fixture")
            with patch("scripts.collect_licenses.sys.base_prefix", str(root / "missing")):
                with self.assertRaisesRegex(NoticeError, "Official Windows Python license"):
                    collect_notices(root, root / "build/bundle")

    def test_zlib_notice_does_not_need_to_name_the_library(self):
        # The actual PyInstaller 6.16 notice names its authors and conditions,
        # but never says "zlib". Requiring that word broke the Windows build.
        data = ("Jean-loup Gailly and Mark Adler\n"
                "This notice may not be removed or altered from any source distribution.\n").encode()
        self.assertNotIn(b"zlib", data)
        require_text(data, ZLIB_LICENSE_MARKERS, "PyInstaller bootloader LICENSE")

    def test_release_requires_cc_license_and_runtime_terms(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "CREDITS.txt").write_text("credits")
            (root / "legal").mkdir()
            (root / "legal/README.md").write_text("provenance")
            with self.assertRaisesRegex(NoticeError, "CC-BY-4.0.txt"):
                collect_notices(root, root / "build/bundle")
            (root / "legal/CC-BY-4.0.txt").write_text("license")
            with self.assertRaisesRegex(NoticeError, "END_USER_TERMS.txt"):
                collect_notices(root, root / "build/bundle")

    def test_unknown_native_libraries_require_review(self):
        root = Path("/python")
        for name in ("python312.dll", "VCRUNTIME140_1.dll", "tcl86t.dll", "libcrypto-3.dll",
                     "api-ms-win-core-file-l1-1-0.dll", "api-ms-win-crt-runtime-l1-1-0.dll"):
            with self.subTest(name=name):
                self.assertTrue(binary_component(name, root / name, root))
        self.assertIn("CPython extension", binary_component("_lzma.pyd", root / "DLLs/_lzma.pyd", root))
        for name, path in (("mystery.dll", root / "mystery.dll"),
                           ("thirdparty.pyd", root / "Lib/site-packages/thirdparty.pyd"),
                           ("outside.pyd", Path("/outside.pyd"))):
            with self.subTest(name=name), self.assertRaises(NoticeError):
                binary_component(name, path, root)

    def test_actual_pyinstaller_native_inventory_is_hashed_and_audited(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "python312.dll").write_bytes(b"runtime")
            (root / "_bz2.pyd").write_bytes(b"extension")
            toc = root / "Analysis-00.toc"
            toc.write_text(repr((["entry.py"], [], [
                ("python312.dll", str(root / "python312.dll"), "BINARY"),
                ("_bz2.pyd", str(root / "_bz2.pyd"), "EXTENSION"),
                ("ignored.txt", "missing-data", "DATA"),
            ])))
            records = audit_analysis(toc, root)
            self.assertEqual({row["name"] for row in records}, {"python312.dll", "_bz2.pyd"})
            self.assertEqual(next(row for row in records if row["name"] == "python312.dll")["sha256"],
                             hashlib.sha256(b"runtime").hexdigest())
            (root / "surprise.dll").write_bytes(b"unknown")
            toc.write_text(repr([("surprise.dll", str(root / "surprise.dll"), "BINARY")]))
            with self.assertRaisesRegex(NoticeError, "Unreviewed"):
                audit_analysis(toc, root)

    def test_embedded_credit_and_every_license_must_match_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary)
            (staged / "legal").mkdir()
            (staged / "CREDITS.txt").write_bytes(b"attribution")
            (staged / "legal/license.txt").write_bytes(b"complete license")
            entries = {"CREDITS.txt": b"attribution", "legal\\license.txt": b"complete license"}
            archive = SimpleNamespace(toc=entries, extract=lambda name: entries[name])
            readers = SimpleNamespace(CArchiveReader=lambda _path: archive)
            with patch.dict("sys.modules", {"PyInstaller.archive.readers": readers}):
                verify_embedded_notices(Path("game.exe"), staged)
                entries["legal\\license.txt"] = b"truncated"
                with self.assertRaisesRegex(NoticeError, "missing or altered"):
                    verify_embedded_notices(Path("game.exe"), staged)


if __name__ == "__main__":
    unittest.main()
