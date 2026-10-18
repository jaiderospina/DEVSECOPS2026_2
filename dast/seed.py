"""Synthetic database fixture only; refuses non-empty identity databases."""
import os, sys
sys.path.insert(0, '/app')
from sqlalchemy import text
from database import engine
from pwdlib import PasswordHash
from cryptography.fernet import Fernet
import pyotp, secrets

def seed():
    assert os.environ['DB_HOST'] == 'postgres' and os.environ['DB_NAME'] == 'iam_zap'
    with engine.begin() as c:
        assert c.execute(text('SELECT count(*) FROM usuarios_plataforma')).scalar_one() == 0, 'Refusing non-empty database'
        companies = []
        for code in ('ZAP_A', 'ZAP_B'):
            companies.append(c.execute(text('INSERT INTO companias(codigo,nombre) VALUES (:code,:code) RETURNING id'), {'code': code}).scalar_one())
        roles = ['ADMIN_TI', 'ADMIN_SOPORTE', 'LIDER_FACTURACION', 'LIDER_LOGISTICA', 'LIDER_GESTION_HUMANA', 'LIDER_FACTURACION']
        for i, role in enumerate(roles):
            uid = c.execute(text('INSERT INTO usuarios_plataforma(nombre,email,id_externo) VALUES (:n,:e,:x) RETURNING id'), {'n':f'Synthetic ZAP {i}', 'e':f'zap{i}@example.invalid', 'x':f'ZAP_{i}'}).scalar_one()
            c.execute(text("INSERT INTO credenciales(usuario_id,password_hash,password_expira_en) VALUES (:u,:h,NOW()+INTERVAL '60 days')"), {'u':uid,'h':PasswordHash.recommended().hash(secrets.token_urlsafe(24))})
            c.execute(text('INSERT INTO usuario_roles_plataforma(usuario_id,rol_id) SELECT :u,id FROM roles_plataforma WHERE nombre=:r'), {'u':uid,'r':role})
            c.execute(text('INSERT INTO usuario_companias_plataforma(usuario_id,compania_id) VALUES (:u,:c)'), {'u':uid,'c':companies[1 if i==5 else 0]})
            c.execute(text('INSERT INTO mfa_totp(usuario_id,secreto_cifrado,activo,fecha_enrolamiento) VALUES (:u,:s,TRUE,NOW())'), {'u':uid,'s':Fernet(os.environ['MFA_ENCRYPTION_KEY'].encode()).encrypt(pyotp.random_base32().encode()).decode()})
        c.execute(text("INSERT INTO permisos_usuario_compania(usuario_id,compania_id,codigo,habilitado) SELECT u.id,uc.compania_id,'facturacion.aprobaciones.consultar',TRUE FROM usuarios_plataforma u JOIN usuario_companias_plataforma uc ON uc.usuario_id=u.id WHERE u.email IN ('zap2@example.invalid','zap5@example.invalid')"))
    print('Synthetic fixture: 6 identities, 2 ZAP companies; no mail, no normal data')

if __name__ == '__main__': seed()
