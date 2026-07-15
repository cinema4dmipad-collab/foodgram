# Foodgram

Платформа для публикации рецептов. Пользователи могут создавать рецепты, подписываться друг на друга, добавлять рецепты в избранное и в список покупок.

## Технологии

**Бэкенд:** Django 4.2, Django REST Framework, djoser, django-filter, PostgreSQL / SQLite  
**Фронтенд:** React (в отдельном контейнере)  
**Инфраструктура:** Docker, Docker Compose, nginx, Gunicorn

## Модели данных

- **User** — кастомная модель пользователя (авторизация по email)
- **Subscription** — подписки пользователей
- **Tag** — теги рецептов
- **Ingredient** — ингредиенты
- **Recipe** — рецепты (с авто-генерацией короткой ссылки)
- **RecipeIngredient** — количество ингредиентов в рецепте
- **Favorite** — избранные рецепты
- **ShoppingCart** — список покупок

## API Endpoints

### Пользователи (`/api/users/`)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/users/` | Список пользователей |
| POST | `/api/users/` | Регистрация |
| GET | `/api/users/{id}/` | Детали пользователя |
| GET | `/api/users/me/` | Текущий пользователь |
| PUT | `/api/users/me/avatar/` | Загрузить аватар |
| DELETE | `/api/users/me/avatar/` | Удалить аватар |
| GET | `/api/users/subscriptions/` | Список подписок |
| POST | `/api/users/{id}/subscribe/` | Подписаться |
| DELETE | `/api/users/{id}/subscribe/` | Отписаться |
| POST | `/api/users/set_password/` | Сменить пароль |

### Рецепты (`/api/recipes/`)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/recipes/` | Список рецептов (с фильтрацией) |
| POST | `/api/recipes/` | Создать рецепт |
| GET | `/api/recipes/{id}/` | Детали рецепта |
| PATCH | `/api/recipes/{id}/` | Частичное обновление |
| DELETE | `/api/recipes/{id}/` | Удалить рецепт |
| GET | `/api/recipes/{id}/get-link/` | Короткая ссылка |
| POST | `/api/recipes/{id}/favorite/` | Добавить в избранное |
| DELETE | `/api/recipes/{id}/favorite/` | Удалить из избранного |
| POST | `/api/recipes/{id}/shopping_cart/` | Добавить в корзину |
| DELETE | `/api/recipes/{id}/shopping_cart/` | Удалить из корзины |
| GET | `/api/recipes/download_shopping_cart/` | Скачать список покупок |

### Фильтрация рецептов
- `?author={id}` — по автору
- `?tags=breakfast&tags=lunch` — по тегам
- `?is_favorited=1` — только избранные
- `?is_in_shopping_cart=1` — только в корзине

### Теги и ингредиенты
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/tags/` | Список тегов |
| GET | `/api/ingredients/` | Список ингредиентов |
| GET | `/api/ingredients/?name=том` | Поиск по началу названия |

### Аутентификация
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/auth/token/login/` | Вход (получить токен) |
| POST | `/api/auth/token/logout/` | Выход (удалить токен) |

## Установка и запуск

### Локально (без Docker)

```bash
cd foodgram/backend
python -m venv venv
source venv/bin/activate 
pip install -r requirements.txt
python manage.py migrate
python manage.py load_data
python manage.py runserver
```

### Через Docker

```bash
cd foodgram/infra
cp .env.example .env
docker-compose up
```

Приложение будет доступно по адресу `http://localhost:8080`.

## Переменные окружения

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `SECRET_KEY` | — | Секретный ключ Django |
| `DEBUG` | `True` | Режим отладки |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Разрешённые хосты |
| `DB_ENGINE` | `sqlite3` | Движок БД |
| `DB_NAME` | `db.sqlite3` | Название БД |
| `DB_USER` | — | Пользователь PostgreSQL |
| `DB_PASSWORD` | — | Пароль PostgreSQL |
| `DB_HOST` | — | Хост PostgreSQL |
| `DB_PORT` | — | Порт PostgreSQL |
| `DOCKER_USERNAME` | — | Имя на Docker Hub |

## Команды управления

```bash
python manage.py load_data          # загрузить ингредиенты (data/ingredients.json) и теги

# Внутри Docker-контейнера:
docker exec -it foodgram-backend python manage.py load_data
python manage.py load_test_data     # загрузить тестовые пользователи и рецепты
python manage.py clean_data         # очистить тестовые данные
```

## Структура проекта

```
foodgram/
├── backend/              # Django-приложение
│   ├── api/              # API (views, serializers, urls)
│   ├── recipes/          # Модели рецептов и админка
│   ├── foodgram/         # Конфиг проекта (settings, urls)
│   └── manage.py
├── frontend/             # React-приложение
├── infra/                # Docker, nginx, .env
│   ├── docker-compose.yml
│   └── nginx.conf
├── data/                 # Данные для загрузки
├── docs/                 # Спецификация API (OpenAPI)
└── postman_collection/   # Коллекция Postman для тестов
```
