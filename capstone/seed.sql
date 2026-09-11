-- Sample sales schema + data for the SQL Query Agent (Project 1 capstone).
-- Idempotent: safe to run more than once (e.g. re-run after a schema tweak).
-- Runs against whatever database DATABASE_URL/SUPABASE_ADMIN_URL points at
-- (Supabase's default "postgres" database, or a local Postgres via
-- docker-compose.yml).

DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date DATE NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

INSERT INTO customers (name, email, country) VALUES
    ('Priya Nair', 'priya.nair@example.com', 'India'),
    ('Marcus Webb', 'marcus.webb@example.com', 'USA'),
    ('Sofia Alvarez', 'sofia.alvarez@example.com', 'Spain'),
    ('Daniel Kim', 'daniel.kim@example.com', 'South Korea'),
    ('Grace Osei', 'grace.osei@example.com', 'Ghana'),
    ('Liam O''Brien', 'liam.obrien@example.com', 'Ireland'),
    ('Yuki Tanaka', 'yuki.tanaka@example.com', 'Japan'),
    ('Amara Diallo', 'amara.diallo@example.com', 'Senegal');

INSERT INTO products (name, category, price) VALUES
    ('Wireless Mouse', 'Electronics', 24.99),
    ('Mechanical Keyboard', 'Electronics', 89.99),
    ('USB-C Hub', 'Electronics', 34.50),
    ('Standing Desk', 'Furniture', 349.00),
    ('Office Chair', 'Furniture', 219.00),
    ('Notebook Set', 'Stationery', 12.50),
    ('Desk Lamp', 'Furniture', 45.00),
    ('Noise-Cancelling Headphones', 'Electronics', 199.99);

INSERT INTO orders (customer_id, order_date, status) VALUES
    (1, '2026-06-02', 'completed'),
    (2, '2026-06-05', 'completed'),
    (3, '2026-06-10', 'completed'),
    (1, '2026-06-18', 'completed'),
    (4, '2026-07-01', 'completed'),
    (5, '2026-07-03', 'cancelled'),
    (6, '2026-07-09', 'completed'),
    (2, '2026-07-15', 'completed'),
    (7, '2026-07-22', 'completed'),
    (8, '2026-08-01', 'completed'),
    (3, '2026-08-05', 'completed'),
    (4, '2026-08-12', 'completed'),
    (5, '2026-08-20', 'completed'),
    (6, '2026-08-27', 'refunded'),
    (1, '2026-09-01', 'completed');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 2, 24.99),
    (1, 3, 1, 34.50),
    (2, 4, 1, 349.00),
    (3, 2, 1, 89.99),
    (4, 6, 5, 12.50),
    (5, 5, 2, 219.00),
    (6, 8, 1, 199.99),
    (7, 1, 1, 24.99),
    (7, 7, 1, 45.00),
    (8, 4, 1, 349.00),
    (9, 2, 2, 89.99),
    (10, 3, 3, 34.50),
    (11, 8, 1, 199.99),
    (12, 6, 10, 12.50),
    (13, 5, 1, 219.00),
    (14, 7, 2, 45.00),
    (15, 1, 3, 24.99),
    (15, 2, 1, 89.99);

-- Read-only role used by the SQL Query Agent: even a query that slips past
-- the app-level SELECT-only check cannot write, because this role has no
-- write grants at the database level.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'capstone_reader') THEN
        CREATE ROLE capstone_reader WITH LOGIN PASSWORD 'capstone_reader';
    END IF;
END
$$;
GRANT CONNECT ON DATABASE postgres TO capstone_reader;
GRANT USAGE ON SCHEMA public TO capstone_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO capstone_reader;
