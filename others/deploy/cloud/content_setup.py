"""Fixed cloud management entry; owner credentials never reach the API or controller."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import secrets

HOST_SHARED = Path('/opt/labconnect/shared')
MANAGEMENT = Path('/run/cloud-management')
CONTROL_ROOT = '/opt/labconnect/shared/content-control'
SOCKET = '/run/labconnect-content/control.sock'


def read_env(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines()
                if '=' in line and not line.startswith('#'))


def write_private(path, data, *, uid=0, gid=0, mode=0o600):
    temporary = path.with_name(path.name + '.pending')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(mode)
    os.chown(temporary, uid, gid)
    os.replace(temporary, path)


def migration_file():
    migration = HOST_SHARED / 'migration.env'
    if not migration.exists():
        if (HOST_SHARED / 'content-management.json').exists():
            raise RuntimeError('Owner configuration missing; existing credentials preserved')
        original = read_env(HOST_SHARED / 'api.env')['DATABASE_URL']
        write_private(migration, 'DATABASE_URL=' + original + '\n')


def configure_files(release):
    manifest = json.loads((release / 'manifest.json').read_text())
    parser = json.loads((release / 'parser-image.json').read_text())
    if parser['image'] != manifest['image_ids']['parser']:
        raise RuntimeError('Parser manifest mismatch')
    migration_file()
    client, server, tasks = (HOST_SHARED / name for name in ('content-client', 'content-server', 'content-control'))
    for directory in (client, server, tasks):
        directory.mkdir(mode=0o700, exist_ok=True)
    os.chown(client, 0, 10001)
    client.chmod(0o750)
    previous_file = server / 'control.json'
    previous = json.loads(previous_file.read_text()) if previous_file.exists() else None
    journal = tasks / 'journal'
    if previous is None and any(journal.glob('*.json')):
        raise RuntimeError('Controller identity missing for existing history; preserved')
    if previous:
        if previous['root'] != CONTROL_ROOT or previous['socket'] != SOCKET:
            raise RuntimeError('Existing cloud controller path differs; preserved')
        for path in journal.glob('*.json'):
            record = json.loads(path.read_text())
            if not record.get('released') or not record.get('stop_confirmed'):
                raise RuntimeError('Old cloud executions need actual stop/release before deployment')
    key = previous['key'] if previous else secrets.token_urlsafe(48)
    instance = previous['instance'] if previous else secrets.token_hex(16)
    config = {'protocol': 'labconnect.content-control/2', 'socket': SOCKET, 'key': key}
    write_private(server / 'control.json', json.dumps({**config, 'root': CONTROL_ROOT,
        'instance': instance, 'image': parser['image'], 'client_gid': 10001}) + '\n')
    for name, value in [('parser-client.json', config), ('runtime.json', {
            'storage_root': '/opt/labconnect/others/runtime/content',
            'parser_client': '/run/labconnect-content/parser-client.json'}), ('image.json', parser)]:
        write_private(client / name, json.dumps(value) + '\n', uid=10001, gid=10001, mode=0o400)
    print(json.dumps({'private_content_files_ready': True, 'controller_identity_preserved': previous is not None}))


def runtime_data(owner):
    from sqlalchemy.engine import make_url
    path = MANAGEMENT / 'content-management.json'
    if path.exists():
        data = json.loads(path.read_text())
    else:
        role = 'c1_run_' + secrets.token_hex(6)
        url = make_url(owner).set(username=role, password=secrets.token_urlsafe(36))
        data = {'runtime_role': role, 'runtime_url': url.render_as_string(hide_password=False)}
        write_private(path, json.dumps(data) + '\n')
    url, admin = make_url(data['runtime_url']), make_url(owner)
    if (not re.fullmatch(r'c1_run_[0-9a-f]{12}', data['runtime_role'])
            or url.username != data['runtime_role'] or not url.password
            or (url.host, url.port, url.database) != (admin.host, admin.port, admin.database)
            or url.username == admin.username):
        raise RuntimeError('Existing cloud runtime configuration differs; preserved')
    return data


def owner_engine():
    from sqlalchemy import create_engine
    return create_engine(os.environ['DATABASE_URL'])


def grant(connection, role):
    if not re.fullmatch(r'c1_run_[0-9a-f]{12}', role):
        raise RuntimeError('Unexpected cloud runtime role')
    database = connection.dialect.identifier_preparer.quote(connection.exec_driver_sql('SELECT current_database()').scalar_one())
    connection.exec_driver_sql(f'GRANT CONNECT ON DATABASE {database} TO "{role}"')
    connection.exec_driver_sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
    connection.exec_driver_sql(f'GRANT USAGE ON SCHEMA public TO "{role}"')
    connection.exec_driver_sql(f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
    connection.exec_driver_sql(f'GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO "{role}"')
    connection.exec_driver_sql(f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO "{role}"')


def prepare_role():
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    data = runtime_data(os.environ['DATABASE_URL'])
    role, engine = data['runtime_role'], owner_engine()
    with engine.begin() as connection:
        exists = connection.execute(text('SELECT 1 FROM pg_roles WHERE rolname=:role'), {'role': role}).scalar()
        if not exists:
            password = make_url(data['runtime_url']).password
            if not re.fullmatch(r'[A-Za-z0-9_-]+', password):
                raise RuntimeError('Unexpected generated password format')
            connection.exec_driver_sql(f'CREATE ROLE "{role}" LOGIN PASSWORD \'{password}\' '
                'NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
        grant(connection, role)
    verify_role(data['runtime_url'])
    api = MANAGEMENT / 'api.env'
    lines = api.read_text().splitlines()
    write_private(api, '\n'.join(line for line in lines if not line.startswith('DATABASE_URL='))
                  + '\nDATABASE_URL=' + data['runtime_url'] + '\n')
    print(json.dumps({'runtime_role_ready': role, 'other_api_settings_preserved': True}))


def verify_role(url):
    from sqlalchemy import create_engine, text
    engine = create_engine(url)
    with engine.connect() as db:
        flags = db.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls '
                                'FROM pg_roles WHERE rolname=current_user')).one()
        owners = db.execute(text("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind IN ('r','p') AND pg_has_role(current_user,c.relowner,'MEMBER')")).scalar_one()
        database_owner = db.execute(text("SELECT pg_has_role(current_user,datdba,'MEMBER') FROM pg_database "
                                          'WHERE datname=current_database()')).scalar_one()
        if any(flags) or owners or database_owner:
            raise RuntimeError('Unsafe cloud API database role')
    engine.dispose()


def snapshot(identifier, *, compare=False):
    from sqlalchemy import text
    if not re.fullmatch(r'[0-9a-f]{40}-[0-9TZ]+', identifier):
        raise RuntimeError('Invalid snapshot identity')
    path = MANAGEMENT / 'snapshots' / (identifier + '.json')
    engine = owner_engine()
    with engine.connect() as db:
        names = (list(json.loads(path.read_text())) if compare else list(db.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars()))
        values = {}
        for name in names:
            if name == 'alembic_version':
                continue
            quoted = engine.dialect.identifier_preparer.quote(name)
            count, checksum = db.execute(text(f"SELECT count(*),md5(coalesce(string_agg(row_to_json(t)::text,E'\\n' "
                f"ORDER BY row_to_json(t)::text),'')) FROM public.{quoted} t")).one()
            values[name] = {'count': count, 'content_md5': checksum}
    if compare:
        if values != json.loads(path.read_text()):
            raise RuntimeError('Original cloud rows changed during migration; preserve backup and stop')
    else:
        path.parent.mkdir(mode=0o700, exist_ok=True)
        if path.exists():
            raise RuntimeError('Original snapshot already exists; preserved')
        write_private(path, json.dumps(values, indent=2) + '\n')
    print(json.dumps({'old_tables_checked': len(values), 'snapshot_matches': compare}))


def grant_check():
    from sqlalchemy import text
    data = runtime_data(os.environ['DATABASE_URL'])
    with owner_engine().begin() as db:
        grant(db, data['runtime_role'])
        heads = list(db.execute(text('SELECT version_num FROM alembic_version')).scalars())
        if heads != ['c1d0c000001']:
            raise RuntimeError('Unexpected cloud migration head')
    verify_role(data['runtime_url'])
    print(json.dumps({'migration': heads[0], 'runtime_nonowner': True}))


def verify():
    from app.core.config import settings
    from app.core.content_runtime import build_runtime
    from sqlalchemy import text
    from app.core.db import engine
    verify_role(str(settings.DATABASE_URL))
    with engine.connect() as db:
        heads = list(db.execute(text('SELECT version_num FROM alembic_version')).scalars())
    if heads != ['c1d0c000001']:
        raise RuntimeError('Unexpected actual cloud migration')
    runtime = build_runtime()
    if runtime.storage is None:
        raise RuntimeError('Cloud content runtime is unavailable')
    capabilities = asyncio.run(runtime.runner.capabilities())
    print(json.dumps({'source_sha': os.environ['LABCONNECT_SOURCE_SHA'], 'migration': heads[0],
                      'runtime_nonowner': True, 'content_capabilities_ready': True,
                      'parser_image': capabilities.image_digest, 'socket_configured': 'socket' in runtime.runner.configuration}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['migration-file', 'files', 'prepare-role', 'snapshot', 'compare', 'grant-check', 'verify'])
    parser.add_argument('--sha')
    parser.add_argument('--snapshot-id')
    args = parser.parse_args()
    if args.action == 'migration-file':
        migration_file()
    elif args.action == 'files':
        if not args.sha or not re.fullmatch('[0-9a-f]{40}', args.sha):
            parser.error('files requires a fixed release SHA')
        configure_files(Path('/opt/labconnect/releases') / args.sha)
    elif args.action == 'prepare-role':
        prepare_role()
    elif args.action in {'snapshot', 'compare'}:
        snapshot(args.snapshot_id or '', compare=args.action == 'compare')
    elif args.action == 'grant-check':
        grant_check()
    else:
        verify()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Driver exceptions may contain CREATE ROLE SQL/passwords: never emit that traceback.
        print(json.dumps({'failed': True, 'error_type': type(error).__name__,
                          'reason': str(error) if type(error) is RuntimeError else 'Private management operation failed'}))
        raise SystemExit(1) from None
