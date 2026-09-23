import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.model_assets import join_parts
from scripts.setup_local import prepare, read_env


class InstallTests(unittest.TestCase):
    def test_fresh_setup_and_repeat_preserve_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prepare(root)
            paths = [root / '.env.local', root / '.runtime/copilot.env', root / '.runtime/api-security.env']
            before = [path.read_bytes() for path in paths]
            self.assertGreaterEqual(len(read_env(paths[0])['POSTGRES_PASSWORD']), 32)
            self.assertGreaterEqual(len(read_env(paths[2])['JWT_SECRET']), 32)
            prepare(root)
            self.assertEqual(before, [path.read_bytes() for path in paths])

    def test_existing_deployment_and_settings_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / '.runtime').mkdir()
            (root / '.runtime/deployment.env').write_text('POSTGRES_PASSWORD=existing-deployment-value\n')
            (root / '.env.local').write_text('# Keep comment\nPOSTGRES_USER=myuser\nPOSTGRES_PASSWORD=\n')
            prepare(root)
            values = read_env(root / '.env.local')
            self.assertEqual(values['POSTGRES_PASSWORD'], 'existing-deployment-value')
            self.assertEqual(values['POSTGRES_USER'], 'myuser')
            self.assertIn('# Keep comment', (root / '.env.local').read_text())


class ModelTests(unittest.TestCase):
    def test_reconstruct_exact_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            chunks = [bytes(range(256)), b'\x00GGUF\xff' * 10]
            parts = []
            for index, content in enumerate(chunks):
                name = f'model.part{index}'
                (directory / name).write_bytes(content)
                parts.append({'filename': name, 'size': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
            expected = b''.join(chunks)
            target = directory / 'assembled.gguf'
            join_parts(parts, directory, target, hashlib.sha256(expected).hexdigest(), len(expected))
            self.assertEqual(target.read_bytes(), expected)

    def test_corrupt_part_cannot_become_model(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / 'part').write_bytes(b'wrong')
            parts = [{'filename': 'part', 'size': 5, 'sha256': hashlib.sha256(b'right').hexdigest()}]
            target = directory / 'assembled.gguf'
            with self.assertRaises(ValueError):
                join_parts(parts, directory, target, parts[0]['sha256'], 5)
            self.assertFalse(target.exists())

    def test_existing_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            target = directory / 'existing.gguf'
            target.write_bytes(b'keep')
            with self.assertRaises(ValueError):
                join_parts([], directory, target, hashlib.sha256(b'other').hexdigest(), 5)
            self.assertEqual(target.read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
