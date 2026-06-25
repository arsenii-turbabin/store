# Store

Django-based online store with promo code support.

## Stack

- Python 3.12
- Django 4.2
- Django REST Framework
- PostgreSQL
- Docker Compose
- pytest + pytest-django

## Quick Start

```bash
# 1. Clone and enter
git clone <repo>
cd test_store

# 2. Environment
cp .env.example .env
# fill SECRET_KEY and DB credentials

# 3. Start PostgreSQL
docker compose up -d db

# 4. Install dependencies
pip install -r requirements.txt

# 5. Migrate & run
python manage.py migrate
python manage.py runserver
```

## API

### Create order

```
POST /api/orders/
Authorization: Basic ... (or Session)
```

#### Request body

```json
{
    "goods": [
        {
            "good_id": 1,
            "quantity": 2
        }
    ],
    "promo_code": "SUMMER2025"
}
```

`promo_code` is optional.

#### Response — `201 Created`

```json
{
    "order_id": 1,
    "user_id": 1,
    "goods": [
        {
            "good_id": 1,
            "quantity": 2,
            "price": 100.00,
            "discount": "0.1",
            "total": 180.00
        }
    ],
    "price": 200.00,
    "discount": "0.1",
    "total": 180.00
}
```

#### Errors — `400 Bad Request`

```json
{
    "detail": "Promo code is expired"
}
```

### Promo code rules

- Promo code must exist.
- Promo code must not be expired.
- Promo code has a global usage limit (`max_usages`).
- A user can use a promo code only once.
- Promo code may be restricted to certain categories.
- Goods with `promo_excluded=True` are never discounted.

## Tests

```bash
pytest orders/tests/ -v