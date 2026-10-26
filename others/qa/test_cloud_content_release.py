"""Deployment tooling only; no real cloud, database, dependency install or service mutation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setup = load('cloud_content_setup', 'others/deploy/cloud/content_setup.py')
builder = load('cloud_controller_build', 'others/deploy/cloud/controller_build.py')
cloud = load('cloud_release_tool', 'others/scripts/cloud.py')
prepare = load('cloud_parser_prepare', 'others/deploy/content/prepare.py')


class CloudContentReleaseTests(unittest.TestCase):
    def test_controller_context_has_only_standard_library_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = builder.context(ROOT, Path(temporary))
            self.assertTrue(all(name in files for name in builder.FILES))
            for unwanted in ('app/main.py', 'app/core/config.py', '.env', 'speech', 'models'):
                self.assertFalse(any(unwanted in name for name in files))
            self.assertEqual((Path(temporary) / 'others/backend/app/__init__.py').read_bytes(), b'')

    def test_cloud_parser_profile_is_fixed_and_independent_of_local_control(self):
        with tempfile.TemporaryDirectory() as temporary:
            primary = Path(temporary).resolve()
            with patch.object(prepare, 'ROOT', primary), patch.object(prepare, 'primary_root', return_value=primary), \
                    patch.object(prepare.subprocess, 'check_output', side_effect=['main\n', 'a' * 40]):
                result = prepare.profile_settings('cloud')
                self.assertEqual(Path(result['runtime']), primary / 'others/runtime/cloud-ecs/releases' / ('a' * 40) / 'parser')
            with patch.object(prepare, 'primary_root', return_value=primary), \
                    patch.object(prepare.subprocess, 'check_output', return_value='codex/a-executor'):
                with self.assertRaises(RuntimeError):
                    prepare.profile_settings('cloud')

    def test_cloud_files_preserve_identity_and_fence_unknown_execution(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(setup.os, 'chown', create=True), patch.object(Path, 'chmod'):
            root = Path(temporary)
            shared, release = root / 'shared', root / 'release'
            shared.mkdir()
            release.mkdir()
            api = 'SECRET_KEY=synthetic\nDATABASE_URL=postgresql://owner:synthetic@db/labconnect\nCORS_ORIGINS=synthetic\n'
            (shared / 'api.env').write_text(api)
            image = 'sha256:' + 'a' * 64
            (release / 'manifest.json').write_text(json.dumps({'image_ids': {'parser': image}}))
            (release / 'parser-image.json').write_text(json.dumps({'image': image}))
            with patch.object(setup, 'HOST_SHARED', shared):
                setup.configure_files(release)
                control = shared / 'content-server/control.json'
                before = json.loads(control.read_text())
                migration = (shared / 'migration.env').read_bytes()
                setup.configure_files(release)
                after = json.loads(control.read_text())
                self.assertEqual((before['key'], before['instance']), (after['key'], after['instance']))
                self.assertEqual((shared / 'api.env').read_text(), api)
                self.assertEqual((shared / 'migration.env').read_bytes(), migration)
                client = json.loads((shared / 'content-client/parser-client.json').read_text())
                self.assertEqual(client['socket'], setup.SOCKET)
                self.assertNotIn('root', client)
                journal = shared / 'content-control/journal'
                journal.mkdir()
                (journal / 'sample.json').write_text(json.dumps({'released': False, 'stop_confirmed': False}))
                raw = control.read_bytes()
                with self.assertRaises(RuntimeError):
                    setup.configure_files(release)
                self.assertEqual(control.read_bytes(), raw)

    def test_runtime_credential_reuse_and_database_boundary(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(setup.os, 'chown', create=True):
            with patch.object(setup, 'MANAGEMENT', Path(temporary)):
                first = setup.runtime_data('postgresql://owner:synthetic@db/labconnect')
                second = setup.runtime_data('postgresql://owner:synthetic@db/labconnect')
                self.assertEqual(first, second)
                self.assertRegex(first['runtime_role'], r'^c1_run_[0-9a-f]{12}$')
                with self.assertRaises(RuntimeError):
                    setup.runtime_data('postgresql://owner:synthetic@other/labconnect')

    def test_prepare_role_changes_only_api_database_line(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(setup.os, 'chown', create=True):
            directory = Path(temporary)
            api = directory / 'api.env'
            api.write_text('SECRET_KEY=keep\nCORS_ORIGINS=keep\nDATABASE_URL=postgresql://owner:old@db/labconnect\n')
            engine, connection = MagicMock(), MagicMock()
            engine.begin.return_value.__enter__.return_value = connection
            connection.execute.return_value.scalar.return_value = 1
            connection.exec_driver_sql.return_value.scalar_one.return_value = 'labconnect'
            with patch.object(setup, 'MANAGEMENT', directory), patch.object(setup, 'owner_engine', return_value=engine), \
                    patch.object(setup, 'verify_role'), patch.dict(setup.os.environ, {'DATABASE_URL': 'postgresql://owner:old@db/labconnect'}):
                setup.prepare_role()
                first = api.read_text()
                setup.prepare_role()
                self.assertEqual(first, api.read_text())
                self.assertIn('SECRET_KEY=keep\nCORS_ORIGINS=keep\n', first)
                self.assertNotIn('DATABASE_URL=postgresql://owner:', first)

    def test_owner_flags_and_membership_are_refused(self):
        for flags, owners, member in [((True, False, False, False), 0, False),
                                      ((False,) * 4, 1, False), ((False,) * 4, 0, True),
                                      ((False,) * 4, 0, False)]:
            engine, db = MagicMock(), MagicMock()
            engine.connect.return_value.__enter__.return_value = db
            db.execute.side_effect = [MagicMock(one=lambda: flags), MagicMock(scalar_one=lambda: owners),
                                      MagicMock(scalar_one=lambda: member)]
            with self.subTest(flags=flags, owners=owners, member=member), patch('sqlalchemy.create_engine', return_value=engine):
                if any(flags) or owners or member:
                    with self.assertRaises(RuntimeError):
                        setup.verify_role('postgresql://synthetic@db/labconnect')
                else:
                    setup.verify_role('postgresql://synthetic@db/labconnect')

    def test_https_verify_rejects_old_head_before_remote_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'secrets').mkdir()
            (directory / 'secrets/cloud.env').write_text('PUBLIC_HOST=192.0.2.1\n')
            health = MagicMock()
            health.read.return_value = json.dumps({'status': 'ok', 'contract': '0.5.0',
                                                                        'migration': 'c02d0c00001'}).encode()
            info = MagicMock()
            info.read.return_value = json.dumps({'source_sha': 'a' * 40, 'contract': '0.5.0'}).encode()
            with patch.object(cloud, 'RUNTIME', directory), patch.object(cloud, 'connection', return_value={'host': '192.0.2.1'}), \
                    patch.object(cloud.urllib.request, 'urlopen', side_effect=[health, info]), patch.object(cloud, 'remote') as remote:
                with self.assertRaises(ValueError):
                    cloud.verify('https://192.0.2.1', 'a' * 40)
                remote.assert_not_called()


if __name__ == '__main__':
    unittest.main()
