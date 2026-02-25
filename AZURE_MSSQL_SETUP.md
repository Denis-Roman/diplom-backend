# Azure MSSQL Setup (Django backend)

## Що вже зроблено в проекті

- У `config/settings.py` вже є підтримка `mssql-django`.
- Додано авто-нормалізацію Azure логіна: якщо `DB_HOST` типу `*.database.windows.net` і `DB_USER` без `@server`, суфікс додається автоматично.
- Локальний override (`.env.local`) перемкнено на `DB_ENGINE=mssql`.

## Поточний блокер

Підключення падає з помилкою Azure SQL `40615`: клієнтський IP не дозволений firewall'ом SQL Server.

## Що потрібно зробити в Azure Portal

1. Відкрити `Azure Portal` → `SQL servers` → ваш сервер (host із `.env`).
2. Перейти в `Networking` → `Firewall rules`.
3. Додати правило для вашого публічного IP (або поточного діапазону).
4. За потреби увімкнути `Allow Azure services and resources to access this server`.
5. Зберегти зміни і почекати 1-5 хвилин.

## Перевірка після firewall

```bash
cd master
C:/Users/PC/Downloads/diplom-main/master/venv/Scripts/python.exe check_db_connection.py
```

Очікуємо успішний вивід `DB_NAME`, `SQL_VERSION`, `TABLES_COUNT`.

## Міграції після успішного конекту

```bash
cd master
C:/Users/PC/Downloads/diplom-main/master/venv/Scripts/python.exe manage.py migrate
```

## Мінімальні env-поля для Azure SQL

- `DB_ENGINE=mssql`
- `DB_NAME=...`
- `DB_USER=...` (можна без `@server`, код додасть автоматично для Azure)
- `DB_PASSWORD=...`
- `DB_HOST=your-server.database.windows.net`
- `DB_PORT=1433`
- `DB_DRIVER=ODBC Driver 18 for SQL Server`
- `DB_EXTRA_PARAMS=Encrypt=yes;TrustServerCertificate=no;`

## Примітка

`.env.local` має вищий пріоритет за `.env` (див. `load_dotenv(... override=True)`).
Якщо в `.env.local` стоїть `DB_ENGINE=sqlite`, MSSQL не активується навіть при правильному `.env`.
