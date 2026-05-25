# Database Migration Steps (MySQL Workbench) -> Final 5-Table Schema

This project uses MySQL by default (see `config.py`). Goal: keep ONLY these tables:

- `users`
- `item_master`
- `restaurant_tables`
- `orders`
- `order_details`

## Option A (Recommended): Fresh database schema (cleanest)

1. In MySQL Workbench, create a fresh database (example): `sromsdb`
2. Update env vars if needed:
   - `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB`
3. Run the Flask app once:
   - It will run `db.create_all()` and then `seed.ensure_seed_data()`

Default users:
- Admin: `admin / admin123`
- Kitchen: `kitchen / kitchen123`

## Option B: Cleanup existing database (DROP duplicate/unnecessary tables)

1. **Backup first** (WorkBench: Server → Data Export)
2. Stop Flask server
3. Run this SQL in MySQL Workbench (replace `sromsdb` if different):

```sql
USE sromsdb;

-- drop duplicates / old tables (only if they exist)
DROP TABLE IF EXISTS admin;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS menu_item;
DROP TABLE IF EXISTS tables;
DROP TABLE IF EXISTS restaurant_table;
DROP TABLE IF EXISTS order_item;

-- keep ONLY the final 5 tables created by SQLAlchemy:
-- users, item_master, restaurant_tables, orders, order_details
```

4. Run Flask app once so `db.create_all()` ensures final schema exists
5. Verify in Workbench that only the 5 tables exist

## Optional: Regenerate QR URLs/images

- `python scripts/generate_qr_codes.py`
   - `python scripts/generate_qr_codes.py`
