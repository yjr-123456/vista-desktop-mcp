import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
import server

class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        context_patch = patch.object(server.helpers, "active_window", return_value={"hwnd": 10, "pid": 20})
        context_patch.start()
        self.addCleanup(context_patch.stop)
        self.desktop = MagicMock()
        self.desktop.capture.return_value = Image.new('RGB', (320, 200), 'white')
        self.desktop.gui.KEYBOARD_KEYS = ['enter']
        with patch.object(server, 'WindowsDesktop', return_value=self.desktop), patch.object(server.atexit, 'register') as register:
            self.mcp = server.build_server(data_root=Path(self.temp.name), session='test')
            self.close = register.call_args.args[0]
    def tearDown(self):
        self.close()
        self.temp.cleanup()
    def call(self, tool, **args):
        return self.mcp._tool_manager.get_tool(tool).fn(**args)
    def test_denied_focus_returns_recovery_image(self):
        with patch.object(server.helpers, 'focus_window', side_effect=RuntimeError('denied')):
            result = self.call('windows', action='focus', hwnd=10, expected_pid=20)
        self.assertFalse(json.loads(result[0].text)['focused'])
        self.assertTrue(any(item.type == 'image' for item in result))
        self.desktop.gui.click.assert_not_called()
    def test_stale_window_is_still_an_error(self):
        with patch.object(server.helpers, 'focus_window', side_effect=ValueError('stale')):
            with self.assertRaises(ValueError):
                self.call('windows', action='focus', hwnd=10, expected_pid=20)
    def test_guard_rejects_without_typing_and_returns_full_view(self):
        with patch.object(server.helpers, 'active_window', return_value={'hwnd': 11, 'pid': 20}):
            result = self.call('play', action='type', text='private', expected_hwnd=10, expected_pid=20,
                               preview_region=server.Region(x=0,y=0,width=10,height=10))
        self.assertEqual(json.loads(result[0].text)['status'], 'not_applied')
        self.desktop.type_unicode.assert_not_called()
        self.assertEqual(json.loads(result[1].text)['preview_width'],320)
        self.assertNotIn('private', next(Path(self.temp.name).rglob('history.jsonl')).read_text())
    def test_guard_allows_matching_foreground(self):
        with patch.object(server.helpers, 'active_window', return_value={'hwnd': 10, 'pid': 20}):
            self.call('play', action='type', text='hello', expected_hwnd=10, expected_pid=20, seconds=0)
        self.desktop.type_unicode.assert_called_once_with('hello')
    def test_incomplete_guard_rejected_before_input(self):
        with self.assertRaises(ValueError):
            self.call('play', action='type', text='hello', expected_hwnd=10)
        self.desktop.type_unicode.assert_not_called()
    def test_move_has_no_duplicate_settle_wait(self):
        with patch.object(server.time,'sleep') as sleep:
            self.call('play', action='move', x=30,y=30,seconds=0.4)
        sleep.assert_not_called()
        self.desktop.gui.moveTo.assert_called_once_with(30,30,duration=0.4)

    def test_initial_observe_returns_binding_and_evidence(self):
        with tempfile.TemporaryDirectory() as workspace:
            try:
                result = self.call('configure_session', workspace=workspace, initial_observe=True)
                self.assertIn('session', json.loads(result[0].text))
                meta = json.loads(result[1].text)
                self.assertEqual(meta['action'], 'initial_observe')
                self.assertEqual(meta['active_window'], {'hwnd':10,'pid':20})
                self.assertTrue(Path(meta['path']).is_file())
                self.assertEqual(result[2].type, 'image')
            finally:
                self.close()
    def test_default_binding_does_not_capture(self):
        with tempfile.TemporaryDirectory() as workspace:
            try:
                result = self.call('configure_session', workspace=workspace)
                self.assertIn('session_id',result)
                self.desktop.capture.assert_not_called()
            finally:
                self.close()
    def test_window_query_failure_keeps_visual_evidence(self):
        with patch.object(server.helpers, 'active_window', side_effect=RuntimeError('window closed')):
            result = self.call('observe')
        meta = json.loads(result[0].text)
        self.assertIsNone(meta['active_window'])
        self.assertEqual(meta['window_context_error'], 'window closed')
        self.assertEqual(result[1].type,'image')

if __name__ == '__main__':
    unittest.main()
