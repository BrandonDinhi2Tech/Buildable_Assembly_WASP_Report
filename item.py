from db import create_db_conn
import requests
import json
import pandas as pd
from io import StringIO

# TODO: Get rid of the intermediate item_list.csv creation, should be able to go straight from json to postgresql
# requests the entire inventory from WASP and puts it into a csv
# use streamgridrequestcsvflat if you want info on individual items i.e. serial number, location
def entire_inventory_api_call():
    url = "http://i2techinventory:8703/public-api/ic/item/streamgridrequestcsvflat"

    payload = json.dumps({
    "AdditionalSkipCount": 0,
    "PageSize": 0,
    "PageNumber": 0,
    "Sort": [],
    # better to filter item_list.csv using pandas since doing it using fieldtitles only returns the fields
    # that are mentioned inside FieldTitles
    # I want the raw file returned from the api that I can manipulate later basically
    "FieldTitles": [],
    "FilterBehavior": 0
    })

    # I am using my own API key, need to update this later to a different user's API key
    headers = {
    'Authorization': 'Bearer JlJlZnJlc2hfdG9rZW49UlQ6Rl0qOW8hSXQxI3RAamRsZWNmRyVLb1VJUXNxJi5pc3N1ZWQ9MjAyNi0wMy0yN1QyMTowODowNS43ODE5NDE4WiYuZXhwaXJlcz0yMDk5LTEyLTMxVDAwOjAwOjAwLjAwMDAwMDBaJlRva2VuPWh2WWlyMEM5bDhZOEdETnBDQnk2VHBQYk5XcEgwanA5Z1VpbENabVNaalpfNUJsWVJHcXB5QV9JdUJYOWtrX250LTNhWTZsLWRaRXZkR19KWFRJYXlldXJ4WmlROUdQcjAxcGNDWkxJaHh5eklsd0lYLXdOckNXV0xRdGhRV0NhZDJYVkFkV0xRbEtSVzhwdlpSZGxpWVRKZmlXeC1ja0ZMMzFZaU53dDFpUkpUVmZzSzlKM1AzMjlNNHN4NDhaeHFrYTRmMUtWN1BiX01CbE5EbExLZmxSUDFXQlZTU3BSM2ROaHA1ai1QeDZmR3BTRHQ0VkJST05oRTVjQ0FCMjIyWkdoY2k0R05EVXlDdW9tZ3BqMXNfUHpKMDJiQmpHOTBvSy1Kcnp4U01PeTFYMkJhbFJxQ2ZKbXVGNW9NT3FZcUFwUjhueDFwWks4djV2eGQ5MWRFX3FxVnF3JmNsaWVudF9pZD1JbnZlbnRvcnlDb250cm9sX2xvY2FsaG9zdCZVc2VySWQ9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUzJnJvbGVzPUFQSSBMb2dpbiZodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lPWJyYW5kb24uZGluaEBpMnRlY2hpbmMuY29tJmh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL25hbWVpZGVudGlmaWVyPTU2ZTVlNzU0LTc3NDQtNDJlYi1hNzZmLTU4MjdlMTM4YzllMyZodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL2FjY2Vzc2NvbnRyb2xzZXJ2aWNlLzIwMTAvMDcvY2xhaW1zL2lkZW50aXR5cHJvdmlkZXI9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUz',
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload, timeout=30)
    response.raise_for_status()
    csv_data = response.text
    return pd.read_csv(StringIO(csv_data))

def inventory_to_database(df):
    # Rename columns
    df.rename(columns={
        'AssetTag': 'WASPNumber',
        'AssetTypeNumber': 'Type',
        'AssetDescription': 'Description',
        'CostMethodName': 'CostMethod',
        'ItemCost': 'Cost',
        'ManufacturerName': 'Manufacturer',
        'CategoryDescription': 'Category',
        'ItemAlterNumber': 'AlternateNumber',
        'Part Drawing Number': 'PartDrawingNumber',
        'Part Drawing Description': 'PartDrawingDescription'
    }, inplace=True)

    df['Description'] = df['Description'].str.replace(r'[\r\n]+', ' ', regex=True)
    df = df.where(pd.notna(df), None)

    # Filter and transform
    items_filtered = df[['WASPNumber', 'Type', 'Description', 'CostMethod', 'Cost',
                          'Manufacturer', 'Category', 'StockingUnit', 'AlternateNumber',
                          'OnOrder', 'CommittedQty', 'SerialNumber', 'LocationCode',
                          'SiteName', 'TotalAvailable', 'TotalCheckedOut', 'TotalInHouse',
                          'PartDrawingNumber', 'PartDrawingDescription']].copy()

    items_filtered = items_filtered.where(pd.notna(items_filtered), None)

    int_columns = ['OnOrder', 'CommittedQty', 'TotalAvailable', 'TotalCheckedOut', 'TotalInHouse']
    for col in int_columns:
        items_filtered[col] = pd.to_numeric(items_filtered[col], errors='coerce').astype('Int64')

    # Stream DataFrame directly to PostgreSQL via StringIO
    try:
        conn = create_db_conn()
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS Items CASCADE")
        cursor.execute("""
            CREATE TABLE Items (
                id SERIAL PRIMARY KEY,
                WASPNumber VARCHAR(32),
                Type VARCHAR(64),
                Description TEXT,
                CostMethod VARCHAR(32),
                Cost NUMERIC(10, 2),
                Manufacturer VARCHAR(64),
                Category VARCHAR(32),
                StockingUnit VARCHAR(32),
                AlternateNumber VARCHAR(256),
                OnOrder INTEGER,
                CommittedQty INTEGER,
                SerialNumber VARCHAR(64),
                LocationCode TEXT,
                SiteName TEXT,
                TotalAvailable INTEGER,
                TotalCheckedOut INTEGER,
                TotalInHouse INTEGER,
                PartDrawingNumber VARCHAR(32),
                PartDrawingDescription TEXT
            )
        """)

        # Write DataFrame to an in-memory buffer instead of a file
        buffer = StringIO()
        items_filtered.to_csv(buffer, index=False)
        buffer.seek(0)

        cursor.copy_expert("""
            COPY Items (
                WASPNumber, Type, Description, CostMethod, Cost,
                Manufacturer, Category, StockingUnit, AlternateNumber,
                OnOrder, CommittedQty, SerialNumber, LocationCode, SiteName,
                TotalAvailable, TotalCheckedOut, TotalInHouse,
                PartDrawingNumber, PartDrawingDescription
            )
            FROM STDIN WITH CSV HEADER DELIMITER ','
        """, buffer)

        conn.commit()
        print("Items Imported")
    except Exception as e:
        print('Failed data import', e)
        raise
    finally:
        cursor.close()
        conn.close()
        
def get_item_cost(waspnumber, conn=None):
    if conn is None:
        conn=create_db_conn()
        close_after = True
    else:
        close_after = False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT cost
                FROM items
                WHERE waspnumber = %s
                ORDER BY waspnumber LIMIT 1;
            """
        , (waspnumber,))
        row = cursor.fetchone()[0]
        return row
    
    finally:
        if close_after:
            cursor.close()
            conn.close()
