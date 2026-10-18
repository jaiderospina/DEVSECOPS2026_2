"""GET-only smoke validation and allowlisted OpenAPI export. No ZAP invocation."""
import sys, os, json, secrets
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0, '/app')
from sqlalchemy import text
from database import engine
import jwt

ALLOW = {
 'identity': ('http://identity:8003', ['/', '/auth/me', '/auth/sesiones', '/usuarios', '/usuarios/{usuario_id}', '/companias', '/companias/asignaciones', '/companias/{compania_id}/contexto', '/companias/{compania_id}/usuarios']),
 'permissions': ('http://permissions:8005', ['/', '/v1/companies', '/v1/companies/{company_id}/permissions', '/v1/me/permissions', '/v1/me/views/{code}']),
 'audit': ('http://audit-service:8004', ['/health']),
}
def get(url, token=None):
    req = Request(url, headers={'Authorization':'Bearer '+token} if token else {})
    try:
        with urlopen(req, timeout=10) as r: return r.status, json.load(r)
    except HTTPError as e: return e.code, None

def main():
    assert os.environ['DB_HOST']=='postgres' and os.environ['DB_NAME']=='iam_zap'
    with engine.begin() as c:
        users = c.execute(text('SELECT id,email FROM usuarios_plataforma ORDER BY id')).mappings().all()
        assert len(users)==6 and all(u['email'].endswith('@example.invalid') for u in users)
        # Sessions are ephemeral fixtures, not authentication-flow coverage.
        tokens = {}
        now = datetime.now(timezone.utc)
        for u in users:
            jti = secrets.token_hex(24)
            c.execute(text('INSERT INTO sesiones(usuario_id,jti,fecha_expiracion) VALUES (:u,:j,:e)'), {'u':u['id'],'j':jti,'e':now+timedelta(minutes=30)})
            tokens[u['email']] = jwt.encode({'sub':str(u['id']),'jti':jti,'iat':now,'exp':now+timedelta(minutes=30)}, os.environ['JWT_SECRET'], algorithm='HS256')
        company = c.execute(text("SELECT id FROM companias WHERE codigo='ZAP_A'")).scalar_one()
        other = c.execute(text("SELECT id FROM companias WHERE codigo='ZAP_B'")).scalar_one()
    result = {'active_scan_executed':False,'synthetic_identities':6,'checks':[]}
    for name,(base,paths) in ALLOW.items():
        status,spec = get(base+'/openapi.json'); assert status==200
        filtered = {k:v for k,v in spec.items() if k not in ('paths','servers','webhooks')}
        filtered['servers']=[{'url':base}]
        filtered['paths']={}
        for path in paths:
            assert path in spec['paths'] and 'get' in spec['paths'][path], path
            op = json.loads(json.dumps(spec['paths'][path]['get']))
            op.pop('callbacks',None)
            filtered['paths'][path]={'get':op}
        assert all(set(v)=={'get'} for v in filtered['paths'].values())
        # Remove schemas of excluded write operations as well.
        components = filtered.get('components',{})
        refs=set()
        def walk(x):
            if isinstance(x,dict):
                if '$ref' in x: refs.add(x['$ref'])
                for v in x.values(): walk(v)
            elif isinstance(x,list):
                for v in x: walk(v)
        walk(filtered['paths'])
        old=set()
        while old!=refs:
            old=refs.copy()
            for ref in old:
                parts=ref.split('/')
                if len(parts)==4 and parts[:2]==['#','components']:
                    walk(components[parts[2]][parts[3]])
        filtered['components']={section:{k:v for k,v in values.items() if f'#/components/{section}/{k}' in refs} for section,values in components.items()}
        print('OPENAPI '+name+' '+json.dumps(filtered,separators=(',',':')))
    checks=[
      ('identity-health','http://identity:8003/',None,200),
      ('audit-health','http://audit-service:8004/health',None,200),
      ('permissions-health','http://permissions:8005/',None,200),
      ('identity-me','http://identity:8003/auth/me',tokens['zap1@example.invalid'],200),
      ('identity-companies','http://identity:8003/companias',tokens['zap0@example.invalid'],200),
      ('identity-users','http://identity:8003/usuarios',tokens['zap1@example.invalid'],200),
      ('support-grid',f'http://permissions:8005/v1/companies/{company}/permissions',tokens['zap1@example.invalid'],200),
      ('cross-company-denied',f'http://permissions:8005/v1/companies/{other}/permissions',tokens['zap1@example.invalid'],403),
      ('leader-permissions','http://permissions:8005/v1/me/permissions',tokens['zap2@example.invalid'],200),
      ('leader-view','http://permissions:8005/v1/me/views/facturacion.aprobaciones.consultar',tokens['zap2@example.invalid'],200),
      ('anonymous-denied','http://permissions:8005/v1/companies',None,401),
    ]
    for label,url,token,expected in checks:
        status,_=get(url,token)
        assert status==expected, (label,status,expected)
        result['checks'].append({'name':label,'status':status})
    print('RESULT '+json.dumps(result))
if __name__=='__main__': main()
