# Foodgram — AGENTS.md

## Project structure

```
backend/          # Django 4.2 + DRF + djoser (fully built)
frontend/         # React 17 (CRA), React Router 5, proxy → http://web:8000/
infra/            # Docker Compose + nginx config
docs/             # openapi-schema.yml, redoc.html
data/             # ingredients.json, ingredients.csv — seed data
postman_collection/  # Postman collection + clear_db.sh
```

## Backend

- **Stack**: Django 4.2.x, DRF 3.14.x, djoser 2.2.x, django-filter, Pillow, gunicorn, psycopg2-binary.
- `AUTH_USER_MODEL = 'api.User'` — `email` is `USERNAME_FIELD`, token auth via `rest_framework.authentication.TokenAuthentication`.
- Default permission: `AllowAny`. Recipe write/update/delete: `IsAuthenticatedOrReadOnly` + `IsAuthor`.
- **Pagination**: `?limit=` query param, default 6, max 1000 (`api.pagination.CustomPagination`).
- **Ingredient search**: `?name=` prefix filter (`name__istartswith`), no pagination.
- **Recipe filtering**: `?author=`, `?tags=breakfast&tags=lunch` (slug, OR logic), `?is_favorited=1`, `?is_in_shopping_cart=1`.
- **Short links**: `GET /api/recipes/{id}/get-link/` returns `{"short-link": "<6-char-code>"}`.
- **Shopping cart download**: `GET /api/recipes/download_shopping_cart/` returns `text/plain` attachment `shopping-list.txt` (ingredients summed).
- **Avatar**: PUT/DELETE `/api/users/me/avatar/`, images sent as Base64 data URIs.
- **Subscriptions**: POST/DELETE `/api/users/{id}/subscribe/`, list at `/api/users/subscriptions/?recipes_limit=3`.
- **Seed data**: `python manage.py load_data` creates 3 tags (breakfast/lunch/dinner) + ingredients from `data/ingredients.json`.
- Database: SQLite (dev) / PostgreSQL (production via `DB_*` env vars).
- Dev server auto-serves built frontend at `/` — no proxy needed.

```
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py load_data
python backend/manage.py runserver
# Open http://localhost:8000/
```

## Frontend

- React 17 + React Router 5 (not v6). `classnames`, `react-tooltip`, `react-meta-tags`.
- `proxy` in `package.json` → `"http://web:8000/"` (Docker only).
- For local dev, build once: `cd frontend && npm install && npm run build` — Django serves it.

## Linting

- flake8 config in `setup.cfg` — ignores W503; excludes tests/, */migrations/, data/, venv/, env/, docs/, frontend/, infra/.
- `*/settings.py:E501` ignored.

## API testing

- Primary suite: Postman collection at `postman_collection/foodgram.postman_collection.json`.
- Clean test data between runs: `bash postman_collection/clear_db.sh` (deletes known test users via `manage.py shell`).
- Requires 2+ ingredients and 3 tags in DB (load seed data first).

## Deployment (4 containers)

- `infra/docker-compose.yml` — PostgreSQL + backend (gunicorn) + frontend build + nginx.
- `infra/.env.example` → copy to `.env`, fill secrets.
- `infra/nginx.conf` proxies `/api/`, `/admin/`, `/media/` to backend on port 8000.
- Backend Dockerfile runs `collectstatic` at build time.
- GitHub Actions CI/CD: lint → build & push images → deploy via SSH (`./github/workflows/deploy.yml`).
- Requires `DOCKER_USERNAME`, `HOST`, `USER`, `SSH_KEY` secrets.
