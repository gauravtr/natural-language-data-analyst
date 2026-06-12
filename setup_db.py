"""
setup_db.py — Create the BI Copilot demo database.
Run once: python setup_db.py
Generates a DuckDB file with ~800 orders, seasonal patterns,
and interesting analytics for demo queries.
"""

import duckdb
import random
from datetime import date, timedelta
import os

random.seed(42)


def setup_db(path: str = "bi_copilot.duckdb") -> None:
    if os.path.exists(path):
        print(f"Database already exists at {path}. Delete it to regenerate.")
        return

    conn = duckdb.connect(path)

    conn.execute("""
    CREATE TABLE categories (
        category_id   INTEGER PRIMARY KEY,
        category_name VARCHAR NOT NULL,
        description   VARCHAR
    )""")

    conn.executemany("INSERT INTO categories VALUES (?, ?, ?)", [
        (1, "Beverages",       "Soft drinks, coffees, teas, ales"),
        (2, "Condiments",      "Sauces, relishes, spreads, seasonings"),
        (3, "Confections",     "Desserts, candies, sweet breads"),
        (4, "Dairy Products",  "Cheeses and fresh dairy"),
        (5, "Grains & Cereals","Breads, crackers, pasta, cereal"),
        (6, "Meat & Poultry",  "Prepared meats and premium cuts"),
        (7, "Produce",         "Dried fruit, fresh vegetables"),
        (8, "Seafood",         "Fish, shellfish, and products"),
    ])

    conn.execute("""
    CREATE TABLE products (
        product_id      INTEGER PRIMARY KEY,
        product_name    VARCHAR NOT NULL,
        category_id     INTEGER REFERENCES categories(category_id),
        unit_price      DECIMAL(10, 2) NOT NULL,
        units_in_stock  INTEGER DEFAULT 0
    )""")

    products = [
        (1,  "Chai",                     1,  18.00,  39),
        (2,  "Chang",                    1,  19.00,  17),
        (3,  "Cote de Blaye",            1, 263.50,  17),
        (4,  "Outback Lager",            1,  15.00, 100),
        (5,  "Steeleye Stout",           1,  18.00,  20),
        (6,  "Aniseed Syrup",            2,  10.00,  13),
        (7,  "Chef Anton Cajun",         2,  22.00,  53),
        (8,  "Grandma Boysenberry",      2,  25.00,   0),
        (9,  "Louisiana Hot Sauce",      2,  21.05,  76),
        (10, "Vegie Spread",             2,  43.90,  24),
        (11, "Teatime Biscuits",         3,   9.20,  25),
        (12, "Sir Rodney Marmalade",     3,  81.00,  40),
        (13, "Chocolade",               3,  12.75,  15),
        (14, "Pavlova",                  3,  17.45,  29),
        (15, "Tarte au sucre",           3,  49.30,  17),
        (16, "Queso Cabrales",           4,  21.00,  22),
        (17, "Mozzarella di Giovanni",   4,  34.80,  14),
        (18, "Raclette Courdavault",     4,  55.00,  79),
        (19, "Camembert Pierrot",        4,  34.00,  19),
        (20, "Gudbrandsdalsost",         4,  36.00,  26),
        (21, "Filo Mix",                 5,   7.00,  38),
        (22, "Gnocchi di nonna Alice",   5,  38.00,  21),
        (23, "Ravioli Angelo",           5,  19.50,  36),
        (24, "Tunnbrod",                 5,   9.00,  61),
        (25, "Wimmers Semmelknoedel",    5,  33.25,  22),
        (26, "Mishi Kobe Niku",          6,  97.00,  29),
        (27, "Alice Mutton",             6,  39.00,   0),
        (28, "Pate chinois",             6,  24.00, 115),
        (29, "Tourtiere",                6,   7.45,  21),
        (30, "Thuringer Rostbratwurst",  6, 123.79,   0),
        (31, "Uncle Bob Organic",        7,  30.00, 120),
        (32, "Tofu",                     7,  23.25,  35),
        (33, "Longlife Tofu",            7,  10.00,   4),
        (34, "Manjimup Dried Apples",    7,  53.00,  20),
        (35, "Konbu",                    8,   6.00,  24),
        (36, "Carnarvon Tigers",         8,  62.50,  42),
        (37, "Boston Crab Meat",         8,  18.40, 123),
        (38, "Gravad lax",               8,  26.00,  11),
        (39, "Inlagd Sill",              8,  19.00, 112),
        (40, "Escargots Bourgogne",      8,  13.25,  62),
    ]
    conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)

    conn.execute("""
    CREATE TABLE customers (
        customer_id  VARCHAR(5) PRIMARY KEY,
        company_name VARCHAR NOT NULL,
        country      VARCHAR,
        city         VARCHAR,
        segment      VARCHAR
    )""")

    customers = [
        ("ALFKI","Alfreds Futterkiste","Germany","Berlin","Consumer"),
        ("ANATR","Ana Trujillo","Mexico","Mexico City","Consumer"),
        ("ANTON","Antonio Moreno","Mexico","Mexico City","Corporate"),
        ("AROUT","Around the Horn","UK","London","Corporate"),
        ("BERGS","Berglunds snabbkop","Sweden","Lulea","Home Office"),
        ("BLAUS","Blauer See Delikatessen","Germany","Mannheim","Consumer"),
        ("BOLID","Bolido Comidas","Spain","Madrid","Consumer"),
        ("BONAP","Bon app","France","Marseille","Corporate"),
        ("BOTTM","Bottom-Dollar Markets","Canada","Vancouver","Corporate"),
        ("BSBEV","B's Beverages","UK","London","Home Office"),
        ("COMMI","Comercio Mineiro","Brazil","Sao Paulo","Corporate"),
        ("EASTC","Eastern Connection","UK","London","Corporate"),
        ("ERNSH","Ernst Handel","Austria","Graz","Corporate"),
        ("FAMIA","Familia Arquibaldo","Brazil","Sao Paulo","Consumer"),
        ("FOLKO","Folk och fa HB","Sweden","Brakne-Hoby","Home Office"),
        ("FRANK","Frankenversand","Germany","Munich","Corporate"),
        ("GREAL","Great Lakes Food","USA","Eugene","Corporate"),
        ("HANAR","Hanari Carnes","Brazil","Rio de Janeiro","Corporate"),
        ("HILAA","HILARION-Abastos","Venezuela","San Cristobal","Corporate"),
        ("HUNGC","Hungry Coyote","USA","Elgin","Home Office"),
        ("HUNGO","Hungry Owl","Ireland","Cork","Corporate"),
        ("ISLAT","Island Trading","UK","Cowes","Consumer"),
        ("KOENE","Koenig Weinkellerei","Germany","Brandenburg","Corporate"),
        ("LAMAI","La maison d Asie","France","Toulouse","Home Office"),
        ("LEHMS","Lehmanns Marktstand","Germany","Frankfurt","Corporate"),
        ("LILAS","LILA-Supermercado","Venezuela","Barquisimeto","Corporate"),
        ("LINOD","LINO-Delicateses","Venezuela","Margarita","Corporate"),
        ("LONEP","Lonesome Pine","USA","Portland","Home Office"),
        ("MAGAA","Magazzini Alimentari","Italy","Bergamo","Corporate"),
        ("MEREP","Mere Paillarde","Canada","Montreal","Consumer"),
        ("NORTS","North South","UK","London","Corporate"),
        ("OCEAN","Oceano Atlantico","Argentina","Buenos Aires","Consumer"),
        ("OLDWO","Old World Delicatessen","USA","Anchorage","Corporate"),
        ("PARIS","Paris specialites","France","Paris","Corporate"),
        ("PERIC","Pericles Comidas","Mexico","Mexico City","Consumer"),
        ("PICCO","Piccolo und mehr","Austria","Salzburg","Consumer"),
        ("QUEEN","Queen Cozinha","Brazil","Sao Paulo","Corporate"),
        ("QUICK","QUICK-Stop","Germany","Cunewalde","Corporate"),
        ("RANCH","Rancho grande","Argentina","Buenos Aires","Corporate"),
        ("RATTC","Rattlesnake Canyon","USA","Albuquerque","Corporate"),
        ("REGGC","Reggiani Caseifici","Italy","Reggio Emilia","Consumer"),
        ("RICAR","Ricardo Adocicados","Brazil","Rio de Janeiro","Consumer"),
        ("RICSU","Richter Supermarkt","Switzerland","Geneva","Corporate"),
        ("SANTG","Sante Gourmet","Norway","Stavern","Corporate"),
        ("SAVEA","Save-a-lot Markets","USA","Boise","Corporate"),
        ("SEVES","Seven Seas Imports","UK","London","Corporate"),
        ("SIMOB","Simons bistro","Denmark","Kobenhavn","Consumer"),
        ("SPECD","Specialites du monde","France","Paris","Corporate"),
        ("SUPRD","Supreme Delicacies","Belgium","Charleroi","Corporate"),
        ("THEBI","The Big Cheese","USA","Portland","Consumer"),
        ("TOMSP","Toms Spezialitaten","Germany","Munster","Consumer"),
        ("TORTU","Tortuga Restaurante","Mexico","Mexico City","Consumer"),
        ("TRADH","Tradicao Hipermercados","Brazil","Sao Paulo","Corporate"),
        ("VAFFE","Vaffeljernet","Denmark","Arhus","Consumer"),
        ("VICTE","Victuailles en stock","France","Lyon","Corporate"),
        ("VINET","Vins et alcools","France","Reims","Corporate"),
        ("WANDK","Die Wandernde Kuh","Germany","Stuttgart","Consumer"),
        ("WARTH","Wartian Herkku","Finland","Oulu","Corporate"),
        ("WHITC","White Clover Markets","USA","Seattle","Corporate"),
        ("WOLZA","Wolski Zajazd","Poland","Warszawa","Consumer"),
    ]
    conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", customers)

    conn.execute("""
    CREATE TABLE employees (
        employee_id  INTEGER PRIMARY KEY,
        first_name   VARCHAR NOT NULL,
        last_name    VARCHAR NOT NULL,
        title        VARCHAR,
        hire_date    DATE,
        region       VARCHAR
    )""")

    conn.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?)", [
        (1, "Nancy",    "Davolio",   "Sales Representative",    date(2021, 5,  1), "North"),
        (2, "Andrew",   "Fuller",    "VP Sales",                date(2020, 8, 14), "North"),
        (3, "Janet",    "Leverling", "Sales Representative",    date(2021, 4,  1), "West"),
        (4, "Margaret", "Peacock",   "Sales Representative",    date(2021, 5,  3), "East"),
        (5, "Steven",   "Buchanan",  "Sales Manager",           date(2022,10, 17), "North"),
        (6, "Michael",  "Suyama",    "Sales Representative",    date(2022,10, 17), "West"),
        (7, "Robert",   "King",      "Sales Representative",    date(2022, 1,  2), "East"),
        (8, "Laura",    "Callahan",  "Inside Sales Coordinator",date(2022, 3,  5), "South"),
        (9, "Anne",     "Dodsworth", "Sales Representative",    date(2022,11, 15), "South"),
    ])

    conn.execute("""
    CREATE TABLE orders (
        order_id     INTEGER PRIMARY KEY,
        customer_id  VARCHAR(5) REFERENCES customers(customer_id),
        employee_id  INTEGER REFERENCES employees(employee_id),
        order_date   DATE NOT NULL,
        shipped_date DATE,
        ship_country VARCHAR,
        freight      DECIMAL(10, 2)
    )""")

    conn.execute("""
    CREATE TABLE order_details (
        order_id    INTEGER REFERENCES orders(order_id),
        product_id  INTEGER REFERENCES products(product_id),
        unit_price  DECIMAL(10, 2) NOT NULL,
        quantity    SMALLINT NOT NULL,
        discount    DECIMAL(4, 2) DEFAULT 0,
        PRIMARY KEY (order_id, product_id)
    )""")

    cust_ids  = [c[0] for c in customers]
    heavy     = cust_ids[:15]
    country   = {c[0]: c[2] for c in customers}

    order_id    = 10248
    all_orders  = []
    all_details = []

    cur = date(2022, 7, 4)
    end = date(2024, 12, 31)

    while cur <= end:
        month = cur.month
        n = random.randint(3,6) if month in (11,12) else \
            random.randint(1,3) if month in (6,7,8) else \
            random.randint(2,4)

        for _ in range(n):
            cust = random.choice(heavy) if random.random() < 0.45 else random.choice(cust_ids)
            emp  = random.randint(1, 9)
            shipped = cur + timedelta(days=random.randint(3,14))
            if shipped > end:
                shipped = None

            all_orders.append((
                order_id, cust, emp, cur,
                shipped, country[cust],
                round(random.uniform(2, 120), 2)
            ))

            for p in random.sample(products, k=random.randint(1,5)):
                qty  = random.randint(1, 25)
                disc = random.choice([0,0,0,0.05,0.10,0.15,0.20])
                all_details.append((order_id, p[0], p[3], qty, disc))

            order_id += 1

        cur += timedelta(days=1)

    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", all_orders)
    conn.executemany("INSERT INTO order_details VALUES (?, ?, ?, ?, ?)", all_details)

    n_ord = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    n_det = conn.execute("SELECT COUNT(*) FROM order_details").fetchone()[0]
    rev   = conn.execute(
        "SELECT ROUND(SUM(unit_price*quantity*(1-discount)),2) FROM order_details"
    ).fetchone()[0]

    print(f"\nDatabase created: {path}")
    print(f"  Orders:        {n_ord:,}")
    print(f"  Order details: {n_det:,}")
    print(f"  Total revenue: ${rev:,.2f}")
    conn.close()


if __name__ == "__main__":
    setup_db()
