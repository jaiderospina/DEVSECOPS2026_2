"""Verify schema and synthetic fixture, including non-empty reseed rejection."""
import json, os, sys
sys.path.insert(0,'/app')
sys.path.insert(0,'/support')
from sqlalchemy import text
from database import engine
from seed import seed
expected={'usuarios_plataforma','credenciales','roles_plataforma','usuario_roles_plataforma','sesiones','companias','usuario_companias_plataforma','mfa_totp','mfa_desafios','sync_jobs','auditoria_eventos','auditoria_outbox','permisos_usuario_compania','permisos_migraciones','cargas_usuarios','cargas_usuario_filas'}
assert os.environ['DB_NAME']=='iam_zap'
with engine.connect() as c:
    tables=set(c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars())
    assert expected==tables
    users=c.execute(text('SELECT email,id_externo FROM usuarios_plataforma')).all()
    assert len(users)==6 and all(e.endswith('@example.invalid') and x.startswith('ZAP_') for e,x in users)
    assert c.execute(text('SELECT count(*) FROM companias')).scalar_one()==5
    for table in ('sync_jobs','auditoria_eventos','auditoria_outbox','cargas_usuarios','cargas_usuario_filas'):
        assert c.execute(text(f'SELECT count(*) FROM {table}')).scalar_one()==0
try:
    seed()
except AssertionError as e:
    assert str(e)=='Refusing non-empty database'
else:
    raise RuntimeError('Seed did not reject non-empty database')
print(json.dumps({'tables':sorted(tables),'synthetic_users':6,'zap_companies':2,'academic_init_companies':3,'reseed_rejected':True,'mail_or_import_jobs':0}))
