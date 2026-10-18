FROM nginx:stable-alpine-slim@sha256:32463212baf0e7d91aded2e9b843a4f2b9e017804b8c9d5bae7b51dcef64389c
COPY nginx.conf /etc/nginx/nginx.conf
USER nginx
EXPOSE 8443 8444 8445 8446
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
