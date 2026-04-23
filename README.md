# Backend DMS Django para WordPress

API REST de gestión documental con firma y workflow.

Motor de base de datos configurado: PostgreSQL.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Entornos (local vs producción) — Opción A: 2 archivos + `source`

### 1) Crea tus archivos reales (no van a git)

```bash
cp .env.local.example .env.local
cp .env.prod.example .env.prod
```

Edita credenciales en cada archivo.

### 2) Carga el entorno en tu terminal (debe ser `source`)

Local:

```bash
source ./scripts/use_env.sh local
```

Producción/Neon (cuando quieras apuntar tu shell local a prod **con cuidado**):

```bash
source ./scripts/use_env.sh prod
```

Alternativa equivalente:

```bash
set -a
source .env.local   # o: source .env.prod
set +a
```

### 3) Verifica a qué DB está apuntando tu shell

```bash
python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default'])"
```

### 4) Arranca Django

```bash
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

### Admin sin estilos en Render (`DEBUG=False`)

En producción necesitas generar estáticos:

**Build Command (Render)**
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

El proyecto ya incluye **WhiteNoise** para servir `/static/` desde `STATIC_ROOT`.

Si ves errores tipo `admin/css/base.css could not be found` con storage “Manifest”, casi siempre significa que **no corrió `collectstatic` en el build** o falló silenciosamente: revisa logs de **Build** en Render.

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

## Portal web (Constructora Indico)

Rutas principales:

- `/` home + acceso
- `/login/` login de Django (redirige a `/aprobaciones/`)
- `/aprobaciones/` bandeja
- `/aprobaciones/nuevo/` alta con selección de firmantes
- `/aprobaciones/<id>/` detalle con progreso
- `/aprobaciones/<id>/firmar/` flujo por pasos (revisión → firma → finalizar)
- `/aprobaciones/<id>/pdf-firmado/` descarga del PDF firmado acumulado

Notas:

- Si un documento tiene `DocumentSignatory`, el estado pasa a `approved` cuando **todos** firman.
- Si no hay firmantes asignados, el flujo antiguo por API mantiene `signed` al firmar.
- En cada firma se regenera un PDF firmado: original + hoja de firmas (nombre, documento y firma).

## Tests

```bash
python manage.py test
```
