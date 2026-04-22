# Backend DMS Django para WordPress

API REST de gestión documental con firma y workflow.

Motor de base de datos configurado: PostgreSQL.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Neon (Postgres) + Render

1. En Neon, copia el **Connection string** (como aparece en el modal “Connect to your database”).
2. En Render, crea la variable de entorno:
   - `DATABASE_URL=<pega el string completo>`
3. Opcional (recomendado para serverless/pooler):
   - `DB_CONN_MAX_AGE=0`

Si no defines `DATABASE_URL`, el proyecto usará `DB_HOST/DB_USER/DB_PASSWORD/...` (útil para Postgres local).

## Endpoints

### Auth
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

### Usuarios
- `POST /api/users/register/`
- `GET /api/users/me/`

### Documentos
- `POST /api/documents/`
- `GET /api/documents/`
- `GET /api/documents/{id}/`
- `PATCH /api/documents/{id}/`
- `DELETE /api/documents/{id}/`
- `POST /api/documents/{id}/approve/`
- `POST /api/documents/{id}/reject/`

### Firmas
- `POST /api/signatures/sign/`
- `GET /api/signatures/document/{id}/`

## Filtros

`/api/documents/?status=pending&user=1&date_from=2026-01-01&date_to=2026-12-31`

## Seguridad y hardening

- JWT con rotación de refresh token y clave de firma configurable (`JWT_SIGNING_KEY`).
- Throttling global y por scope (`auth`, `documents`).
- Headers de seguridad (`HSTS`, `X-Frame-Options`, `nosniff`, cookies seguras en producción).
- CORS y CSRF de confianza para WordPress.
- Auditoría persistente de eventos críticos: login, firma, aprobación, rechazo (`workflows.AuditEvent`).
- Logging en formato JSON para integración con observabilidad.

## WordPress

1. Login en `/api/auth/login/`.
2. Guardar JWT y enviar `Authorization: Bearer <token>`.
3. Crear documento.
4. Firmar documento.
5. Consultar estado.

## Tests

```bash
python manage.py test
```
