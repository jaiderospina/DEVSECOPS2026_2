"""Issue lab-only session fixtures; output must be captured privately."""
import sys, os, json, secrets
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'/app')
from database import engine
from sqlalchemy import text
import jwt
assert os.environ['DB_HOST']=='postgres' and os.environ['DB_NAME']=='iam_zap'
now=datetime.now(timezone.utc)
tokens={}
with engine.begin() as c:
    for u in c.execute(text("SELECT id,email FROM usuarios_plataforma ORDER BY id")).mappings().all():
        assert u['email'].endswith('@example.invalid')
        jti=secrets.token_hex(24)
        c.execute(text('INSERT INTO sesiones(usuario_id,jti,fecha_expiracion) VALUES (:u,:j,:e)'),{'u':u['id'],'j':jti,'e':now+timedelta(hours=2)})
        tokens[u['email']]=jwt.encode({'sub':str(u['id']),'jti':jti,'iat':now,'exp':now+timedelta(hours=2)},os.environ['JWT_SECRET'],algorithm='HS256')
    a=c.execute(text("SELECT id FROM companias WHERE codigo='ZAP_A'")).scalar_one()
    b=c.execute(text("SELECT id FROM companias WHERE codigo='ZAP_B'")).scalar_one()
    ids=dict(c.execute(text('SELECT email,id FROM usuarios_plataforma')).all())
print(json.dumps({'tokens':tokens,'company':a,'other_company':b,'users':ids}))
