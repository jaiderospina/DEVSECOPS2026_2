import { writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { securityHeaders } from '../security-policy.js'

export function renderNginxConfig(env = process.env) {
const headers = Object.entries(securityHeaders(env)).map(([name, value]) =>
  '        add_header ' + name + ' "' + value + '" always;').join('\n')

// Puerto no privilegiado y directorios temporales permiten USER nginx.
const config = `pid /tmp/nginx.pid;
error_log /dev/stderr warn;
worker_processes auto;
events { worker_connections 1024; }
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    server_tokens off;
    access_log /dev/stdout;
    sendfile on;
    client_body_temp_path /tmp/client_temp;
    proxy_temp_path /tmp/proxy_temp;
    fastcgi_temp_path /tmp/fastcgi_temp;
    uwsgi_temp_path /tmp/uwsgi_temp;
    scgi_temp_path /tmp/scgi_temp;

    # Las cabeceras también se conservan en respuestas 403/404.
${headers}

    # Los nombres no reconocidos siempre se rechazan.
    server {
        listen 5173 default_server;
        listen [::]:5173 default_server;
        server_name "";
        return 403;
    }

    server {
        listen 5173;
        listen [::]:5173;
        server_name localhost *.localhost host.docker.internal
                    ~^[0-9]+\\\\.[0-9]+\\\\.[0-9]+\\\\.[0-9]+$
                    ~^\\\\[?[0-9a-f]*:[0-9a-f:]+\\\\]?$;
        root /usr/share/nginx/html;
        index index.html;

        # Archivos inexistentes del bundle no deben devolver HTML.
        location /assets/ { try_files $uri =404; }
        location ~ /\\\\. { deny all; }
        location / { try_files $uri $uri/ /index.html; }
    }
}
`
return config
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 2) throw new Error('El generador no acepta rutas de salida')
  // Único destino de compilación; wx rechaza archivos o enlaces preexistentes.
  const output = new URL('../nginx.conf', import.meta.url)
  await writeFile(output, renderNginxConfig(), { encoding: 'utf8', flag: 'wx', mode: 0o644 })
}
