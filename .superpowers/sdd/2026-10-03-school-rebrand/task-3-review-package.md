4c6b7ab feat(cli): school install removes stale previous-brand plugin and skill artifacts
 school/cli.py          | 34 ++++++++++++++++++++++++++++++++++  tests/unit/test_cli.py | 29 +++++++++++++++++++++++++++++  2 files changed, 63 insertions(+)
diff --git a/school/cli.py b/school/cli.py
index 209e364..8c2d395 100644
--- a/school/cli.py
+++ b/school/cli.py
@@ -87,20 +87,51 @@ def _clean_legacy_plugin(config: SchoolConfig, verbose: bool = True) -> bool:
         except OSError:
             pass
 
     return removed
 
 
 # Legacy alias (pre-rename helper name).
 _clean_legacy_plugin_dir = _clean_legacy_plugin
 
 
+def _clean_stale_brand(config: SchoolConfig, verbose: bool = True) -> bool:
+    """Remove previous-brand artefacts so OpenCode never loads duplicates.
+
+    Deletes ``plugins/teacher.ts`` and ``skills/teacher-routing/`` written
+    by pre-rebrand installs of this product.
+    """
+    removed = False
+
+    stale_plugin = config.opencode_plugins_dir() / "teacher.ts"
+    if stale_plugin.is_file():
+        try:
+            stale_plugin.unlink()
+            removed = True
+            if verbose:
+                print(f"Removed stale previous-brand plugin: {stale_plugin}")
+        except OSError:
+            pass
+
+    stale_skill = config.opencode_plugins_dir().parent / "skills" / "teacher-routing"
+    if stale_skill.is_dir():
+        try:
+            shutil.rmtree(stale_skill)
+            removed = True
+            if verbose:
+                print(f"Removed stale previous-brand skill: {stale_skill}")
+        except OSError:
+            pass
+
+    return removed
+
+
 def _cmd_install(args: argparse.Namespace) -> None:
     """Install School globally for OpenCode."""
     config = SchoolConfig()
     force = getattr(args, "force", False)
 
     print("School Installer")
     print("----------------------------")
 
     print(f"Python: {sys.version_info.major}.{sys.version_info.minor} OK")
 
@@ -110,20 +141,23 @@ def _cmd_install(args: argparse.Namespace) -> None:
         print("WARNING: OpenCode config not found")
         print(f"  Expected at: {config.opencode_config_file()}")
         print("  School will work in development mode only.")
         return
 
     print(f"OpenCode config: {config_file}")
 
     # Clean up stale pre-rename plugin artefacts
     _clean_legacy_plugin(config)
 
+    # Remove stale previous-brand artefacts (rebrand cleanup)
+    _clean_stale_brand(config)
+
     # Check if already installed
     plugin_file = config.school_plugin_file()
     if plugin_file.exists() and not force:
         print(f"School is already installed at: {plugin_file}")
         print("Use --force to reinstall.")
         return
 
     # Create plugins directory (auto-discovery)
     plugins_dir = config.opencode_plugins_dir()
     plugins_dir.mkdir(parents=True, exist_ok=True)
diff --git a/tests/unit/test_cli.py b/tests/unit/test_cli.py
index 4771a12..e85c46b 100644
--- a/tests/unit/test_cli.py
+++ b/tests/unit/test_cli.py
@@ -68,20 +68,49 @@ class TestCLI:
         ):
             config = MockConfig.return_value
             config.is_school_installed.return_value = True
             config.school_plugin_file.return_value = plugins_dir / "school.ts"
             config.opencode_config_file.return_value = config_file
             main()
 
         captured = capsys.readouterr()
         assert "already installed" in captured.out.lower()
 
+    def test_install_removes_stale_teacher_artifacts(self, tmp_path: Path) -> None:
+        """school install deletes the previous brand's plugin and skill."""
+        config_dir = tmp_path / ".config" / "opencode"
+        config_dir.mkdir(parents=True)
+        config_file = config_dir / "opencode.jsonc"
+        config_file.write_text('{"plugin": []}', encoding="utf-8")
+        plugins_dir = config_dir / "plugins"
+        plugins_dir.mkdir(parents=True)
+        stale_plugin = plugins_dir / "teacher.ts"
+        stale_plugin.write_text("// stale previous brand", encoding="utf-8")
+        stale_skill = config_dir / "skills" / "teacher-routing"
+        stale_skill.mkdir(parents=True)
+        (stale_skill / "SKILL.md").write_text("name: teacher-routing", encoding="utf-8")
+
+        with (
+            patch("sys.argv", ["school", "install", "--force"]),
+            patch("school.cli.SchoolConfig") as MockConfig,
+        ):
+            config = MockConfig.return_value
+            config.is_school_installed.return_value = False
+            config.opencode_plugins_dir.return_value = plugins_dir
+            config.school_plugin_file.return_value = plugins_dir / "school.ts"
+            config.opencode_config_file.return_value = config_file
+            main()
+
+        assert not stale_plugin.exists(), "stale teacher.ts must be deleted"
+        assert not stale_skill.exists(), "stale teacher-routing skill must be deleted"
+        assert (plugins_dir / "school.ts").exists()
+
     def test_uninstall_safety(self, tmp_path: Path) -> None:
         """school uninstall does not remove user memory."""
         memory_dir = tmp_path / ".school" / "memory"
         memory_dir.mkdir(parents=True)
         memory_file = memory_dir / "test.json"
         memory_file.write_text('{"test": true}', encoding="utf-8")
 
         # Uninstall should NOT remove .school/memory/
         # This is tested by verifying the directory still exists after uninstall
         assert memory_dir.exists()

