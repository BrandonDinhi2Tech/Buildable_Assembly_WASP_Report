from db import create_db_conn
import requests
import json
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv


# search for locations
def location_api_call(location_search_term=None, site_search_term=None):
    url = f"http://i2techinventory:8703/public-api/locations/infosearch"

    payload = json.dumps({
        "LocationCode": location_search_term,
        "SiteName": site_search_term
    })

    # I am using my own API key, need to update this later to a different user's API key
    headers = {
    'Authorization': f"Bearer {os.getenv('WASP_TOKEN')}",
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload, timeout=15)
    response.raise_for_status()
    return response.json()

# make a location table with all of the locations in WASP, their sites, and their descriptions
def update_location_table():
    try:
        conn = create_db_conn()
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS locations")

        create_locations = """
        CREATE TABLE locations (
            SiteName TEXT NOT NULL,
            LocationCode TEXT NOT NULL,
            LocationDescription TEXT,
            PRIMARY KEY (SiteName, LocationCode)
        );
        """
        cursor.execute(create_locations)

        # get all of the locations
        all_location_api_response = location_api_call()
        rows = [
            (
                location.get("SiteName"),
                location.get("LocationCode"),
                location.get("LocationDescription")
            )
            for location in all_location_api_response.get("Data", [])
        ]
        #print(rows)

        execute_values(
            cursor,
            """
            INSERT INTO locations (
                SiteName,
                LocationCode,
                LocationDescription
            ) VALUES %s
            """,
            rows
        )

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        print('Failed location table update', e)
        raise

