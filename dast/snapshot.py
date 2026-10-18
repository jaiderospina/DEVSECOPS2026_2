"""Capture count and per-cell digests in one repeatable-read DB snapshot."""
import sys,os,json,hashlib
sys.path.insert(0,'/app')
from database import engine
from sqlalchemy import text
assert os.environ['DB_NAME']=='iam_zap' and os.environ['DB_HOST']=='postgres'
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
result={}
with engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
    with c.begin():
        c.execute(text('SET TRANSACTION READ ONLY'))
        tables=c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
        for table in tables:
            rows=[dict(r) for r in c.execute(text('SELECT * FROM "'+table+'" ORDER BY 1')).mappings()]
            result[table]={'count':len(rows),'sha256':digest(rows),'cells':{str(r.get('id',i)):{k:digest(v) for k,v in r.items()} for i,r in enumerate(rows)}}
print(json.dumps(result,sort_keys=True))
