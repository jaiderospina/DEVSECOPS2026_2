import unittest
from gateway import allowed
class GatewayTests(unittest.TestCase):
    cfg={'hosts':{'identity:8003':{'patterns':[r'/usuarios',r'/usuarios/[^/]+',r'/auth/me']}}}
    def test_write_methods_blocked(self):
        for method in ('POST','PUT','PATCH','DELETE','OPTIONS','TRACE','CONNECT'):
            self.assertFalse(allowed('identity:8003','/usuarios',method,self.cfg))
    def test_scope_escape_blocked(self):
        for host,path in [('host.docker.internal:8003','/usuarios'),('identity:8003','/auth/login'),('identity:8003','/usuarios/cargas'),('identity:8003','/usuarios/%63argas'),('identity:8003','http://identity:8003/usuarios'),('identity:8003','/usuarios/%2e%2e'),('identity:8003','/usuarios/1/rol')]:
            self.assertFalse(allowed(host,path,'GET',self.cfg))
    def test_allowed_get(self):
        self.assertTrue(allowed('identity:8003','/usuarios/2?q=test','GET',self.cfg))
if __name__=='__main__': unittest.main()
