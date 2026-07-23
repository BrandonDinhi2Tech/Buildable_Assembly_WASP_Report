from db import create_db_conn
import requests
import json
import pandas as pd
from io import StringIO

# requests the entire transaction history from WASP and returns it as a DataFrame
# FieldTitles is left empty (same convention as item.entire_inventory_api_call) so
# the API returns the full raw set of columns rather than only the ones named here;
# we do our own column selection in build_history_to_database().
def transaction_history_api_call():
    url = f"http://i2techinventory:8703/public-api/transactions/streamgridrequestcsv"

    payload = json.dumps({
        "AdditionalSkipCount": 0,
        "PageSize": 0,
        "PageNumber": 0,
        "Sort": [
            {"Field": "UserTransactionDate", "Dir": "desc"}
        ],
        "FieldTitles": [],
        "FilterBehavior": 0
    })

    headers = {
        'Authorization': 'Bearer JlJlZnJlc2hfdG9rZW49UlQ6Rl0qOW8hSXQxI3RAamRsZWNmRyVLb1VJUXNxJi5pc3N1ZWQ9MjAyNi0wMy0yN1QyMTowODowNS43ODE5NDE4WiYuZXhwaXJlcz0yMDk5LTEyLTMxVDAwOjAwOjAwLjAwMDAwMDBaJlRva2VuPWh2WWlyMEM5bDhZOEdETnBDQnk2VHBQYk5XcEgwanA5Z1VpbENabVNaalpfNUJsWVJHcXB5QV9JdUJYOWtrX250LTNhWTZsLWRaRXZkR19KWFRJYXlldXJ4WmlROUdQcjAxcGNDWkxJaHh5eklsd0lYLXdOckNXV0xRdGhRV0NhZDJYVkFkV0xRbEtSVzhwdlpSZGxpWVRKZmlXeC1ja0ZMMzFZaU53dDFpUkpUVmZzSzlKM1AzMjlNNHN4NDhaeHFrYTRmMUtWN1BiX01CbE5EbExLZmxSUDFXQlZTU3BSM2ROaHA1ai1QeDZmR3BTRHQ0VkJST05oRTVjQ0FCMjIyWkdoY2k0R05EVXlDdW9tZ3BqMXNfUHpKMDJiQmpHOTBvSy1Kcnp4U01PeTFYMkJhbFJxQ2ZKbXVGNW9NT3FZcUFwUjhueDFwWks4djV2eGQ5MWRFX3FxVnF3JmNsaWVudF9pZD1JbnZlbnRvcnlDb250cm9sX2xvY2FsaG9zdCZVc2VySWQ9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUzJnJvbGVzPUFQSSBMb2dpbiZodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lPWJyYW5kb24uZGluaEBpMnRlY2hpbmMuY29tJmh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL25hbWVpZGVudGlmaWVyPTU2ZTVlNzU0LTc3NDQtNDJlYi1hNzZmLTU4MjdlMTM4YzllMyZodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL2FjY2Vzc2NvbnRyb2xzZXJ2aWNlLzIwMTAvMDcvY2xhaW1zL2lkZW50aXR5cHJvdmlkZXI9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUz',
        'Content-Type': 'application/json'
        }

    response = requests.post(url, headers=headers, data=payload)
    response.raise_for_status()
    csv_data = response.text
    return pd.read_csv(StringIO(csv_data))


# Loads transaction history into the build_history table.
# A build transaction is any record with a non-null OrderNumber where
# TransactionType is 'Add' (the finished assembly going into stock) or
# 'Remove' (a component consumed out of stock to build it). Every other
# transaction type (Move To/From, Check Out, Pick, etc.) is kept too, since
# it's cheap to store and useful for other kinds of inventory-movement
# reporting later -- filter down to builds at query time via the
# build_history_bom view created below.
def build_history_to_database(df):
    df.rename(columns={
        'AssetTransQuantity': 'Quantity',
        'AssetDescription': 'ItemDescription',
        'AssetTag': 'WASPNumber',
        'AssetTypeNumber': 'ItemType',
        'LocationCode': 'Location',
        'SiteName': 'Site',
        'TransTypeDescription': 'TransactionType',
        'UserTransactionDate': 'TransactionDate',
        'ManufacturerName': 'Manufacturer',
    }, inplace=True)

    df['ItemDescription'] = df['ItemDescription'].str.replace(r'[\r\n]+', ' ', regex=True)
    df = df.where(pd.notna(df), None)

    build_filtered = df[['OrderNumber', 'WASPNumber', 'ItemDescription', 'ItemType',
                          'Location', 'Site', 'SiteDescription', 'TransactionType',
                          'SerialNumber', 'TransactionDate', 'TransactionCost',
                          'Category', 'Manufacturer', 'Lot', 'Quantity']].copy()

    build_filtered = build_filtered.where(pd.notna(build_filtered), None)

    build_filtered['Quantity'] = pd.to_numeric(build_filtered['Quantity'], errors='coerce')
    build_filtered['TransactionCost'] = pd.to_numeric(build_filtered['TransactionCost'], errors='coerce')
    # parsing to a real Timestamp (rather than leaving the raw string) sidesteps
    # the source's 7-digit fractional seconds, which Postgres's timestamp parser
    # won't accept; to_csv() below serializes this as hh:mm:ss and NaT as blank
    build_filtered['TransactionDate'] = pd.to_datetime(build_filtered['TransactionDate'], errors='coerce')

    try:
        conn = create_db_conn()
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS build_history CASCADE")
        cursor.execute("""
            CREATE TABLE build_history (
                id SERIAL PRIMARY KEY,
                OrderNumber TEXT,
                WASPNumber VARCHAR(32),
                ItemDescription TEXT,
                ItemType VARCHAR(64),
                Location TEXT,
                Site TEXT,
                SiteDescription TEXT,
                TransactionType VARCHAR(64),
                SerialNumber VARCHAR(64),
                TransactionDate TIMESTAMP,
                TransactionCost NUMERIC(10, 2),
                Category VARCHAR(32),
                Manufacturer VARCHAR(64),
                Lot TEXT,
                Quantity NUMERIC
            )
        """)
        cursor.execute("CREATE INDEX idx_build_history_order ON build_history (OrderNumber)")
        cursor.execute("CREATE INDEX idx_build_history_type ON build_history (TransactionType)")

        # Write DataFrame to an in-memory buffer instead of a file, same as item.py
        buffer = StringIO()
        build_filtered.to_csv(buffer, index=False)
        buffer.seek(0)

        cursor.copy_expert("""
            COPY build_history (
                OrderNumber, WASPNumber, ItemDescription, ItemType,
                Location, Site, SiteDescription, TransactionType,
                SerialNumber, TransactionDate, TransactionCost,
                Category, Manufacturer, Lot, Quantity
            )
            FROM STDIN WITH CSV HEADER DELIMITER ','
        """, buffer)

        # Bill-of-materials view built from the build transactions:
        # for each OrderNumber, join the 'Add' row (the resulting assembly)
        # to every 'Remove' row (the components consumed to build it).
        cursor.execute("DROP VIEW IF EXISTS build_history_bom")
        cursor.execute("""
            CREATE VIEW build_history_bom AS
            SELECT
                a.ordernumber,
                a.transactiondate       AS build_date,
                a.itemdescription       AS assembly_description,
                a.waspnumber            AS assembly_waspnumber,
                a.serialnumber          AS assembly_serial,
                c.itemdescription       AS component_description,
                c.waspnumber            AS component_waspnumber,
                c.serialnumber          AS component_serial,
                c.quantity              AS component_quantity,
                c.transactioncost       AS component_cost,
                c.category              AS component_category,
                c.manufacturer          AS component_manufacturer,
                c.lot                   AS component_lot
            FROM build_history a
            JOIN build_history c
                ON a.ordernumber = c.ordernumber
               AND c.transactiontype = 'Remove'
            WHERE a.ordernumber IS NOT NULL
              AND a.transactiontype = 'Add'
        """)

        conn.commit()
        print("Build History Imported")
    except Exception as e:
        print('Failed build history import', e)
    finally:
        cursor.close()
        conn.close()


# convenience wrapper matching the item.py / location.py / assembly.py naming pattern,
# so main.py can call buildhistory.update_build_history_table() alongside the others
def update_build_history_table():
    build_history_to_database(transaction_history_api_call())


# ---------------------------------------------------------------------------
# Multi-level build drill-down
#
# build_history_bom only shows one level: a build order's own components.
# But some of those components are themselves sub-assemblies that had their
# own separate build order. To tell "this component is a sub-assembly that
# was built under its own order" apart from "this is a raw/purchased part",
# we match the exact serialized unit: a Remove-row component expands into
# another build only if its (WASPNumber, SerialNumber) exactly matches the
# (WASPNumber, SerialNumber) of some other build's Add row. Non-serialized
# parts (blank SerialNumber) never expand -- they're always leaves.
#
# get_build_tree()          -> every level of the tree (useful for auditing /
#                              seeing which sub-assembly builds got pulled in)
# get_build_item_history()  -> only the bottom-level (leaf) items -- the
#                              "individual item level history" of everything
#                              that ultimately went into a top-level assembly
# ---------------------------------------------------------------------------

_BUILD_TREE_CTE = """
    WITH RECURSIVE build_tree AS (
        SELECT
            a.ordernumber       AS order_number,
            NULL::text          AS parent_order,
            a.ordernumber       AS root_order,
            a.waspnumber        AS root_waspnumber,
            a.serialnumber      AS root_serial,
            a.transactiondate   AS root_build_date,
            a.itemdescription   AS root_description,
            1                   AS depth,
            ARRAY[a.ordernumber] AS path
        FROM build_history a
        WHERE a.transactiontype = 'Add'
          AND (
                (%(order_number)s IS NOT NULL AND a.ordernumber = %(order_number)s)
             OR (%(waspnumber)s IS NOT NULL AND a.waspnumber = %(waspnumber)s)
          )

        UNION ALL

        SELECT
            child_add.ordernumber,
            bt.order_number         AS parent_order,
            bt.root_order,
            bt.root_waspnumber,
            bt.root_serial,
            bt.root_build_date,
            bt.root_description,
            bt.depth + 1,
            bt.path || child_add.ordernumber
        FROM build_tree bt
        JOIN build_history comp
            ON comp.ordernumber = bt.order_number
           AND comp.transactiontype = 'Remove'
        JOIN build_history child_add
            ON child_add.transactiontype = 'Add'
           AND child_add.waspnumber = comp.waspnumber
           AND child_add.serialnumber = comp.serialnumber
           AND child_add.serialnumber IS NOT NULL
           AND NOT (child_add.ordernumber = ANY(bt.path))  -- guard against cycles
    )
"""


def get_build_tree(order_number=None, waspnumber=None, conn=None):
    """
    Returns every level of the build tree rooted at a top-level build order
    (order_number=) or every build order ever made for an assembly type
    (waspnumber=). One row per build order encountered, tagged with its
    depth and which root build it rolled up under.
    """
    if order_number is None and waspnumber is None:
        raise ValueError("Provide either order_number or waspnumber")

    if conn is None:
        conn = create_db_conn()
        close_after = True
    else:
        close_after = False

    query = _BUILD_TREE_CTE + """
        SELECT * FROM build_tree ORDER BY root_order, depth, order_number;
    """

    try:
        return pd.read_sql_query(
            query, conn, params={"order_number": order_number, "waspnumber": waspnumber}
        )
    finally:
        if close_after:
            conn.close()


def get_build_item_history(order_number=None, waspnumber=None, conn=None):
    """
    Returns the individual (leaf) item-level history for a top-level build
    order (order_number=) or every build ever made of an assembly type
    (waspnumber=) -- recursively expanding any component that was itself
    built under its own build order, all the way down to raw/purchased
    parts. Each row is one component consumption, tagged with which
    top-level build (root_order / root_build_date) it ultimately fed into.
    """
    if order_number is None and waspnumber is None:
        raise ValueError("Provide either order_number or waspnumber")

    if conn is None:
        conn = create_db_conn()
        close_after = True
    else:
        close_after = False

    query = _BUILD_TREE_CTE + """
        SELECT
            bt.root_order,
            bt.root_waspnumber,
            bt.root_serial,
            bt.root_build_date,
            bt.root_description         AS root_assembly_description,
            comp.ordernumber            AS immediate_build_order,
            comp.itemdescription        AS component_description,
            comp.waspnumber             AS component_waspnumber,
            comp.serialnumber           AS component_serial,
            comp.quantity,
            comp.transactioncost,
            comp.transactiondate,
            comp.category,
            comp.manufacturer,
            comp.lot
        FROM build_tree bt
        JOIN build_history comp
            ON comp.ordernumber = bt.order_number
           AND comp.transactiontype = 'Remove'
        WHERE NOT EXISTS (
            -- exclude components that are themselves an expandable sub-assembly;
            -- their own components already show up one level deeper in the tree
            SELECT 1 FROM build_history child_add
            WHERE child_add.transactiontype = 'Add'
              AND child_add.waspnumber = comp.waspnumber
              AND child_add.serialnumber = comp.serialnumber
              AND child_add.serialnumber IS NOT NULL
        )
        ORDER BY bt.root_build_date DESC, comp.transactiondate;
    """

    try:
        return pd.read_sql_query(
            query, conn, params={"order_number": order_number, "waspnumber": waspnumber}
        )
    finally:
        if close_after:
            conn.close()
