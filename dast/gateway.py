"""Fail-closed GET gateway. Scanner has no direct network access to the APIs."""
import http.server,http.client,threading,json,re,time
from urllib.parse import urlsplit,unquote
from pathlib import Path
CONFIG=Path('/run/scan/config.json')
LOG=Path('/results/gateway.jsonl')
lock=threading.Lock()
def config(): return json.loads(CONFIG.read_text())
def allowed(host,path,method,cfg):
    if method!='GET' or host not in cfg['hosts']: return False
    p=urlsplit(path)
    if p.scheme or p.netloc or '#' in path or '\\' in path: return False
    decoded=unquote(p.path)
    if decoded == '/usuarios/cargas' or decoded.startswith('/usuarios/cargas/'): return False
    if any(x in decoded for x in ('..','\\','\x00','\r','\n')): return False
    return any(re.fullmatch(pattern,p.path) for pattern in cfg['hosts'][host]['patterns'])
def record(data):
    with lock:
        with LOG.open('a') as f: f.write(json.dumps(data)+'\n')
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def handle_request(self):
        cfg=config(); host=self.headers.get('Host','')
        info={'run':cfg['run'],'host':host,'method':self.command,'path':urlsplit(self.path).path,'allowed':False}
        if not allowed(host,self.path,self.command,cfg):
            info['status']=403;record(info)
            self.send_error(403,'DAST scope rejected');return
        info['allowed']=True
        target=cfg['hosts'][host]
        conn=http.client.HTTPConnection(target['upstream'],target['port'],timeout=15)
        headers={k:v for k,v in self.headers.items() if k.lower() not in ('host','authorization','connection','content-length','transfer-encoding','x-http-method-override','x-method-override','x-http-method')}
        if cfg.get('token'): headers['Authorization']='Bearer '+cfg['token']
        headers['Host']=host
        try:
            conn.request('GET',self.path,headers=headers)
            response=conn.getresponse(); body=response.read()
            self.send_response_only(response.status)
            for k,v in response.getheaders():
                if k.lower() not in ('connection','transfer-encoding','content-length'): self.send_header(k,v)
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            info['status']=response.status
        except Exception as e:
            info['status']=502; info['error']=type(e).__name__
            self.send_error(502,'Laboratory upstream unavailable')
        finally:
            conn.close();record(info)
    do_GET=do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=do_HEAD=do_TRACE=do_CONNECT=handle_request

def keepalive():
    while True:
        cfg=config()
        for token in cfg.get('keepalive_tokens',[]):
            c=http.client.HTTPConnection(cfg['hosts']['identity:8003']['upstream'],8003,timeout=5)
            try:
                c.request('GET','/auth/me',headers={'Authorization':'Bearer '+token})
                r=c.getresponse();r.read()
                record({'run':'keepalive','host':'identity:8003','method':'GET','path':'/auth/me','allowed':True,'status':r.status})
            except Exception: pass
            finally: c.close()
        time.sleep(45)
if __name__=='__main__':
    threading.Thread(target=keepalive,daemon=True).start()
    for port in (8003,8004):
        threading.Thread(target=http.server.ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever,daemon=True).start()
    http.server.ThreadingHTTPServer(('0.0.0.0',8005),Handler).serve_forever()
