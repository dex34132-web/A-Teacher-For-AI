d868272 feat(cli): add school and school-bridge console scripts; drop teacher/lerev aliases
 pyproject.toml                            | 3 +--  tests/unit/test_school_identity_compat.py | 8 +++++---  2 files changed, 6 insertions(+), 5 deletions(-)
diff --git a/pyproject.toml b/pyproject.toml
index d567144..80392a6 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -26,22 +26,21 @@ classifiers = [
     "Topic :: Software Development :: Libraries",
     "Topic :: Scientific/Engineering :: Artificial Intelligence",
 ]
 
 dependencies = [
     "pydantic>=2.0,<3.0",
 ]
 
 [project.scripts]
 school = "school.cli:main"
-# Legacy alias (pre-rename installs used `lerev`); kept for compatibility.
-lerev = "school.cli:main"
+school-bridge = "school.bridge:main"
 
 [project.optional-dependencies]
 dev = [
     "pytest>=8.0",
     "pytest-cov>=5.0",
     "pytest-asyncio>=0.23",
     "ruff>=0.5",
     "mypy>=1.10",
 ]
 web = [
diff --git a/tests/unit/test_school_identity_compat.py b/tests/unit/test_school_identity_compat.py
index 9fcd7e0..9f84199 100644
--- a/tests/unit/test_school_identity_compat.py
+++ b/tests/unit/test_school_identity_compat.py
@@ -128,25 +128,27 @@ class TestLegacyCompat:
         from school.bridge import main
 
         assert shim.main is main
 
     def test_lerev_cli_shim(self) -> None:
         import lerev.cli as shim
         from school.cli import main
 
         assert shim.main is main
 
-    def test_pyproject_keeps_legacy_console_script(self) -> None:
+    def test_pyproject_console_scripts(self) -> None:
         text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
         assert 'name = "school"' in text
-        assert 'name = "lerev"' not in text
-        assert 'lerev = "school.cli:main"' in text
+        assert 'school = "school.cli:main"' in text
+        assert 'school-bridge = "school.bridge:main"' in text
+        assert "teacher =" not in text
+        assert "lerev =" not in text
 
     def test_legacy_plugin_methods(self, tmp_path: Path) -> None:
         with patch.object(Path, "home", return_value=tmp_path):
             config = SchoolConfig()
         assert config.lerev_plugin_file().name == "lerev.ts"
         assert not config.is_lerev_installed()
 
     def test_legacy_home_envs_not_honoured(self, tmp_path: Path) -> None:
         home = tmp_path / "legacy_root"
         (home / "school").mkdir(parents=True)

