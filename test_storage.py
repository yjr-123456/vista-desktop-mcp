import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from PIL import Image
from memory_store import SessionStore


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.store = SessionStore()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def bind(self, session="task-one"):
        return self.store.bind(self.workspace, session)

    def test_unbound_server_does_not_create_files(self):
        with self.assertRaisesRegex(ValueError, "configure_session"):
            self.store.require()
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_workspace_path_and_metadata(self):
        info = self.bind()
        expected = self.workspace / ".agents/vista-desktop/sessions/task-one"
        self.assertEqual(Path(info["session_dir"]), expected)
        self.assertTrue((expected / "session.json").is_file())
        self.assertTrue((expected.parent.parent / ".gitignore").is_file())
        self.assertEqual(self.store.bind(self.workspace)["session_id"], "task-one")

    def test_invalid_workspace_and_session_ids(self):
        for value in ("../escape", "CON", "a/b", "", "x" * 101):
            with self.assertRaises(ValueError):
                self.store.bind(self.workspace, value)
        with self.assertRaises(ValueError):
            self.store.bind("relative")
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_evidence_hash_and_search(self):
        self.bind()
        memory = self.store.require()
        frame = memory.archive(Image.new("RGB", (20, 10), "red"), {"action": "test"})
        entry = memory.remember("已验证红色窗口", [0], ["颜色", "Window"])
        evidence = entry["evidence"][0]
        self.assertEqual(evidence["sha256"], hashlib.sha256(Path(frame["path"]).read_bytes()).hexdigest())
        self.assertEqual(memory.recall("window 红色", 10)[0]["id"], entry["id"])
        self.assertEqual(memory.recall("missing", 10), [])
        self.assertIn(evidence["relative_path"], (memory.directory / "MEMORY.md").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            memory.remember("nonexistent evidence", [999], [])
        self.assertEqual(len(memory.recall("", 10)), 1)

    def test_resume_preserves_frames_and_notes(self):
        self.bind()
        memory = self.store.require()
        memory.archive(Image.new("RGB", (20, 10)), {"action": "test"})
        (memory.directory / "WORKING.md").write_text("checkpoint", encoding="utf-8")
        self.store.close()
        with self.assertRaises(ValueError):
            self.bind()
        self.store.bind(self.workspace, "task-one", resume=True)
        self.assertEqual(self.store.require().turn, 0)
        self.assertEqual((self.store.require().directory / "WORKING.md").read_text(), "checkpoint")

    def test_workspace_isolation_and_concurrent_writer_rejection(self):
        self.bind()
        other = SessionStore()
        try:
            with self.assertRaisesRegex(ValueError, "another MCP process"):
                other.bind(self.workspace, "task-one", resume=True)
            self.assertEqual(self.store.require().directory.name, "task-one")
            second = self.workspace / "another-project"
            second.mkdir()
            other.bind(second, "task-one")
            self.assertNotEqual(self.store.require().directory, other.require().directory)
        finally:
            other.close()

    def test_portable_memory_after_moving_workspace(self):
        self.bind()
        self.store.require().archive(Image.new("RGB", (20, 10)), {"action": "test"})
        self.store.require().remember("portable", [0], [])
        self.store.close()
        relocated = self.workspace / "relocated"
        relocated.mkdir()
        shutil.move(str(self.workspace / ".agents"), str(relocated / ".agents"))
        self.store.bind(relocated, "task-one", resume=True)
        memory = self.store.require()
        evidence = memory.recall("portable", 1)[0]["evidence"][0]
        self.assertTrue((memory.directory / evidence["relative_path"]).is_file())
        self.assertEqual(memory.pixels(0, None, 1, 1)["rgb"], [[(0, 0, 0)]])

    def test_legacy_explicit_root_is_supported(self):
        root = self.workspace / "legacy"
        self.store.bind(data_root=root, session_id="old")
        self.assertEqual(self.store.require().directory, root / "old")
        self.assertIsNone(self.store.info()["workspace"])


if __name__ == "__main__":
    unittest.main()
