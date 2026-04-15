from db import create_db_conn
import requests
import json
from psycopg2.extras import execute_values

# search for locations
def location_api_call(location_search_term=None, site_search_term=None):
    url = f"http://i2techinventory:8703/public-api/locations/infosearch"

    payload = json.dumps({
        "LocationCode": location_search_term,
        "SiteName": site_search_term
    })

    # I am using my own API key, need to update this later to a different user's API key
    headers = {
    'Authorization': 'Bearer JlJlZnJlc2hfdG9rZW49UlQ6Rl0qOW8hSXQxI3RAamRsZWNmRyVLb1VJUXNxJi5pc3N1ZWQ9MjAyNi0wMy0yN1QyMTowODowNS43ODE5NDE4WiYuZXhwaXJlcz0yMDk5LTEyLTMxVDAwOjAwOjAwLjAwMDAwMDBaJlRva2VuPWh2WWlyMEM5bDhZOEdETnBDQnk2VHBQYk5XcEgwanA5Z1VpbENabVNaalpfNUJsWVJHcXB5QV9JdUJYOWtrX250LTNhWTZsLWRaRXZkR19KWFRJYXlldXJ4WmlROUdQcjAxcGNDWkxJaHh5eklsd0lYLXdOckNXV0xRdGhRV0NhZDJYVkFkV0xRbEtSVzhwdlpSZGxpWVRKZmlXeC1ja0ZMMzFZaU53dDFpUkpUVmZzSzlKM1AzMjlNNHN4NDhaeHFrYTRmMUtWN1BiX01CbE5EbExLZmxSUDFXQlZTU3BSM2ROaHA1ai1QeDZmR3BTRHQ0VkJST05oRTVjQ0FCMjIyWkdoY2k0R05EVXlDdW9tZ3BqMXNfUHpKMDJiQmpHOTBvSy1Kcnp4U01PeTFYMkJhbFJxQ2ZKbXVGNW9NT3FZcUFwUjhueDFwWks4djV2eGQ5MWRFX3FxVnF3JmNsaWVudF9pZD1JbnZlbnRvcnlDb250cm9sX2xvY2FsaG9zdCZVc2VySWQ9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUzJnJvbGVzPUFQSSBMb2dpbiZodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lPWJyYW5kb24uZGluaEBpMnRlY2hpbmMuY29tJmh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL25hbWVpZGVudGlmaWVyPTU2ZTVlNzU0LTc3NDQtNDJlYi1hNzZmLTU4MjdlMTM4YzllMyZodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL2FjY2Vzc2NvbnRyb2xzZXJ2aWNlLzIwMTAvMDcvY2xhaW1zL2lkZW50aXR5cHJvdmlkZXI9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUz',
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    # assembly_details = response.text
    # print(assembly_details)
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

