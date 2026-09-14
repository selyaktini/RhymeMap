"""The project's own paths.

Several modules locate the repository root by walking up from ``__file__``.
The number of ``.parent`` hops is a function of how deep the module sits, so
moving a file one directory changes what it points at -- silently. Moving
``export_for_web.py`` into the package did exactly that: it kept one hop, so
``PROJECT_ROOT`` became ``rhymemap/``, the exporter wrote ``rhymemap/web/data.js``
where nothing serves it, and the bundled demo verse stopped being found.

Nothing failed loudly. The export "succeeded" with one verse missing.
"""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path

# The real root, found by a rule none of the modules use: the directory holding
# pyproject.toml. If this file moves, this walk is the one thing to update.
REPO_ROOT = Path(__file__).resolve().parent.parent

MODULES_WITH_ROOT = [
    "rhymemap.cache",
    "rhymemap.main",
    "rhymemap.webexport",
    "scripts.serve_web",
    "eval.ablation",
    "eval.artist_id",
    "eval.build_gold",
    "eval.tune",
    "analysis.config",
]


class TestProjectRoot(unittest.TestCase):
    def test_pyproject_marks_the_root(self):
        self.assertTrue((REPO_ROOT / "pyproject.toml").is_file())

    def test_every_module_agrees_where_the_root_is(self):
        for name in MODULES_WITH_ROOT:
            with self.subTest(module=name):
                module = importlib.import_module(name)
                self.assertEqual(
                    Path(module.PROJECT_ROOT).resolve(),
                    REPO_ROOT,
                    f"{name}.PROJECT_ROOT has the wrong number of .parent hops",
                )

    def test_web_dir_holds_the_page_it_claims_to(self):
        """WEB_DIR must be the directory the server serves, not a phantom."""
        for name in ("rhymemap.webexport", "scripts.serve_web"):
            with self.subTest(module=name):
                module = importlib.import_module(name)
                self.assertTrue(
                    (Path(module.WEB_DIR) / "index.html").is_file(),
                    f"{name}.WEB_DIR does not contain index.html",
                )


class TestPackaging(unittest.TestCase):
    def test_no_top_level_src_package(self):
        """`src` as an installed top-level name collides with every other project."""
        self.assertFalse((REPO_ROOT / "src").exists())

    def test_only_the_library_is_distributed(self):
        """`analysis` and `scripts` are repository tooling.

        Shipping them would install two more generic top-level names into
        site-packages -- exactly the collision the src/ -> rhymemap/ rename was
        for. They stay importable from a clone; they are not distributed.
        """
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[tool.setuptools.packages.find]", text)
        include = text.split("include = [")[1].split("]")[0]
        self.assertIn('"rhymemap*"', include)
        self.assertNotIn('"analysis', include)
        self.assertNotIn('"scripts', include)

    def test_every_subpackage_is_distributed(self):
        """An explicit `packages = [...]` list does not recurse.

        It built a wheel with rhymemap/sources/ -- the whole song-loading layer
        -- missing, and nothing failed until the package was imported from
        outside the source tree. The find directive is what prevents that.
        """
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn("\npackages = [", text,
                         "an explicit package list misses subpackages; use the find directive")
        for path in (REPO_ROOT / "rhymemap").rglob("__init__.py"):
            with self.subTest(package=path.parent.name):
                self.assertTrue(path.parent.name.startswith("rhymemap")
                                or path.parent.parent.name == "rhymemap",
                                f"{path.parent} would not be matched by include = [\"rhymemap*\"]")

    def test_repository_tooling_is_still_importable(self):
        for package in ("rhymemap", "analysis", "scripts"):
            with self.subTest(package=package):
                self.assertTrue((REPO_ROOT / package / "__init__.py").is_file(),
                                f"{package} has no __init__.py, so `python -m {package}.x` is fragile")


if __name__ == "__main__":
    unittest.main()
