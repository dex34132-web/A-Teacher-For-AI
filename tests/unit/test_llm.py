"""Rigorous tests for core/llm.py auto-detection and client behavior."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm


class TestStripJsonc(unittest.TestCase):
    def test_strips_line_comments(self):
        src = '{\n  "a": 1, // comment\n  "b": 2\n}'
        out = llm._strip_jsonc(src)
        self.assertIn('"a": 1', out)
        self.assertNotIn("comment", out)

    def test_strips_block_comments(self):
        src = '{ /* block */ "a": 1 }'
        out = llm._strip_jsonc(src)
        self.assertIn('"a": 1', out)
        self.assertNotIn("block", out)

    def test_strips_trailing_commas(self):
        src = '{"a": [1, 2,], "b": {"c": 3,},}'
        out = llm._strip_jsonc(src)
        obj = json.loads(out)
        self.assertEqual(obj, {"a": [1, 2], "b": {"c": 3}})

    def test_parses_real_config(self):
        src = '''{
            "model": "groq/openai/gpt-oss-120b",
            "provider": {
                "groq": {
                    "options": {
                        "baseURL": "https://api.groq.com/openai/v1",
                        "apiKey": "env://GROQ_API_KEY"
                    }
                }
            }
        }'''
        out = llm._strip_jsonc(src)
        obj = json.loads(out)
        self.assertEqual(obj["model"], "groq/openai/gpt-oss-120b")


class TestResolveRef(unittest.TestCase):
    def test_plain_passthrough(self):
        self.assertEqual(llm._resolve_ref("https://example.com"), "https://example.com")

    def test_env_ref_resolves(self):
        os.environ["LLM_TEST_VAR"] = "secret123"
        try:
            self.assertEqual(llm._resolve_ref("env://LLM_TEST_VAR"), "secret123")
        finally:
            del os.environ["LLM_TEST_VAR"]

    def test_env_ref_missing_returns_empty(self):
        self.assertEqual(llm._resolve_ref("env://NOPE_NOPE_NOPE"), "")

    def test_empty(self):
        self.assertEqual(llm._resolve_ref(""), "")
        self.assertEqual(llm._resolve_ref("   "), "")


class TestReadOpencodeConfig(unittest.TestCase):
    def test_returns_none_when_no_files(self):
        with mock.patch("core.llm.os.path.expanduser", return_value="/nonexistent/path"):
            self.assertIsNone(llm._read_opencode_config())

    def test_reads_valid_config(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = os.path.join(td, ".config", "opencode")
            os.makedirs(cfg_dir)
            path = os.path.join(cfg_dir, "opencode.jsonc")
            with open(path, "w") as f:
                f.write('{"model": "groq/m", "provider": {"groq": {"options": {"baseURL": "https://x/v1", "apiKey": "k"}}}}')
            with mock.patch("core.llm.os.path.expanduser", return_value=td):
                cfg = llm._read_opencode_config()
            self.assertIsNotNone(cfg)
            self.assertEqual(cfg["model"], "groq/m")

    def test_skips_invalid_json(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = os.path.join(td, ".config", "opencode")
            os.makedirs(cfg_dir)
            path = os.path.join(cfg_dir, "opencode.json")
            with open(path, "w") as f:
                f.write("{not json")
            with mock.patch("core.llm.os.path.expanduser", return_value=td):
                self.assertIsNone(llm._read_opencode_config())


class TestDetectFromOpencode(unittest.TestCase):
    def test_full_detection(self):
        cfg = {
            "model": "groq/openai/gpt-oss-120b",
            "provider": {
                "groq": {
                    "options": {
                        "baseURL": "https://api.groq.com/openai/v1",
                        "apiKey": "env://GROQ_API_KEY",
                    },
                    "models": {
                        "openai/gpt-oss-120b": {"id": "gpt-oss-120b"},
                    },
                }
            },
        }
        with mock.patch("core.llm._read_opencode_config", return_value=cfg):
            os.environ["GROQ_API_KEY"] = "testkey"
            try:
                res = llm._detect_from_opencode()
            finally:
                del os.environ["GROQ_API_KEY"]
        self.assertIsNotNone(res)
        base, model, key = res
        self.assertEqual(base, "https://api.groq.com/openai/v1")
        self.assertEqual(model, "gpt-oss-120b")
        self.assertEqual(key, "testkey")

    def test_no_model_returns_none(self):
        with mock.patch("core.llm._read_opencode_config", return_value={"provider": {}}):
            self.assertIsNone(llm._detect_from_opencode())

    def test_no_base_url_returns_none(self):
        cfg = {"model": "groq/m", "provider": {"groq": {"options": {}}}}
        with mock.patch("core.llm._read_opencode_config", return_value=cfg):
            self.assertIsNone(llm._detect_from_opencode())

    def test_simple_model_spec(self):
        cfg = {
            "model": "my-model",
            "baseURL": "https://x/v1",
            "apiKey": "k",
        }
        with mock.patch("core.llm._read_opencode_config", return_value=cfg):
            res = llm._detect_from_opencode()
        self.assertIsNotNone(res)
        self.assertEqual(res[1], "my-model")


class TestDetectPriority(unittest.TestCase):
    def test_env_vars_win(self):
        os.environ["TOOLIO_LLM_BASE_URL"] = "https://env/v1"
        os.environ["TOOLIO_LLM_MODEL"] = "env-model"
        os.environ["TOOLIO_LLM_API_KEY"] = "env-key"
        try:
            with mock.patch("core.llm._detect_from_opencode", return_value=("https://oc/v1", "oc-model", "oc-key")):
                res = llm._detect()
            self.assertEqual(res, ("https://env/v1", "env-model", "env-key"))
        finally:
            for v in ("TOOLIO_LLM_BASE_URL", "TOOLIO_LLM_MODEL", "TOOLIO_LLM_API_KEY"):
                os.environ.pop(v, None)

    def test_falls_to_opencode_when_no_env(self):
        for v in ("TOOLIO_LLM_BASE_URL", "TOOLIO_LLM_MODEL", "TOOLIO_LLM_API_KEY"):
            os.environ.pop(v, None)
        with mock.patch("core.llm._detect_from_opencode", return_value=("https://oc/v1", "oc-model", "oc-key")):
            res = llm._detect()
        self.assertEqual(res, ("https://oc/v1", "oc-model", "oc-key"))

    def test_returns_none_when_nothing(self):
        for v in ("TOOLIO_LLM_BASE_URL", "TOOLIO_LLM_MODEL", "TOOLIO_LLM_API_KEY"):
            os.environ.pop(v, None)
        with mock.patch("core.llm._detect_from_opencode", return_value=None):
            with mock.patch("core.llm._detect_from_ollama", return_value=None):
                self.assertIsNone(llm._detect())


class TestLlmAvailable(unittest.TestCase):
    def test_disabled_env(self):
        os.environ["TOOLIO_LLM_ENABLED"] = "0"
        try:
            self.assertFalse(llm.llm_available())
        finally:
            os.environ.pop("TOOLIO_LLM_ENABLED", None)

    def test_no_config_returns_false(self):
        for v in ("TOOLIO_LLM_BASE_URL", "TOOLIO_LLM_MODEL", "TOOLIO_LLM_API_KEY", "TOOLIO_LLM_ENABLED"):
            os.environ.pop(v, None)
        with mock.patch("core.llm._detect", return_value=None):
            self.assertFalse(llm.llm_available())

    def test_ollama_no_key_available(self):
        with mock.patch("core.llm._detect", return_value=("http://localhost:11434/v1", "llama", "")):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TOOLIO_LLM_ENABLED", None)
                self.assertTrue(llm.llm_available())

    def test_remote_requires_key(self):
        with mock.patch("core.llm._detect", return_value=("https://api.x/v1", "m", "")):
            os.environ.pop("TOOLIO_LLM_ENABLED", None)
            self.assertFalse(llm.llm_available())
        with mock.patch("core.llm._detect", return_value=("https://api.x/v1", "m", "key")):
            os.environ.pop("TOOLIO_LLM_ENABLED", None)
            self.assertTrue(llm.llm_available())


class TestLlmComplete(unittest.TestCase):
    def test_returns_none_when_unavailable(self):
        with mock.patch("core.llm.llm_available", return_value=False):
            self.assertIsNone(llm.llm_complete("hi"))

    def test_parses_openai_response(self):
        fake = json.dumps({"choices": [{"message": {"content": "42"}}]})
        cm = mock.MagicMock()
        cm.__enter__ = mock.MagicMock(return_value=cm)
        cm.__exit__ = mock.MagicMock(return_value=False)
        cm.read = mock.MagicMock(return_value=fake.encode())
        with mock.patch("core.llm.llm_available", return_value=True):
            with mock.patch("core.llm._base_url", return_value="https://x/v1"):
                with mock.patch("core.llm._model", return_value="m"):
                    with mock.patch("core.llm._api_key", return_value="k"):
                        with mock.patch("core.llm._timeout", return_value=5.0):
                            with mock.patch("urllib.request.urlopen", return_value=cm):
                                self.assertEqual(llm.llm_complete("hi"), "42")

    def test_returns_none_on_http_error(self):
        with mock.patch("core.llm.llm_available", return_value=True):
            with mock.patch("core.llm._base_url", return_value="https://x/v1"):
                with mock.patch("core.llm._model", return_value="m"):
                    with mock.patch("core.llm._api_key", return_value="k"):
                        with mock.patch("core.llm._timeout", return_value=5.0):
                            with mock.patch("urllib.request.urlopen", side_effect=Exception("boom")):
                                self.assertIsNone(llm.llm_complete("hi"))

    def test_returns_none_on_bad_json(self):
        cm = mock.MagicMock()
        cm.__enter__ = mock.MagicMock(return_value=cm)
        cm.__exit__ = mock.MagicMock(return_value=False)
        cm.read = mock.MagicMock(return_value=b"not json")
        with mock.patch("core.llm.llm_available", return_value=True):
            with mock.patch("core.llm._base_url", return_value="https://x/v1"):
                with mock.patch("core.llm._model", return_value="m"):
                    with mock.patch("core.llm._api_key", return_value="k"):
                        with mock.patch("core.llm._timeout", return_value=5.0):
                            with mock.patch("urllib.request.urlopen", return_value=cm):
                                self.assertIsNone(llm.llm_complete("hi"))


class TestLlmJudge(unittest.TestCase):
    def test_returns_none_when_no_options(self):
        self.assertIsNone(llm.llm_judge("pick", options=[]))

    def test_picks_matching_option(self):
        with mock.patch("core.llm.llm_complete", return_value="yes"):
            self.assertEqual(llm.llm_judge("q", options=["yes", "no"]), "yes")

    def test_returns_none_when_llm_unavailable(self):
        with mock.patch("core.llm.llm_complete", return_value=None):
            self.assertIsNone(llm.llm_judge("q", options=["a", "b"]))


class TestLlmDetect(unittest.TestCase):
    def test_returns_dict(self):
        with mock.patch("core.llm._detect", return_value=None):
            d = llm.llm_detect()
            self.assertFalse(d["available"])
            self.assertEqual(d["model"], "")

    def test_masks_api_key(self):
        with mock.patch("core.llm._detect", return_value=("https://x/v1", "m", "secret")):
            d = llm.llm_detect()
            self.assertEqual(d["api_key"], "***")
            self.assertEqual(d["model"], "m")


if __name__ == "__main__":
    unittest.main()
