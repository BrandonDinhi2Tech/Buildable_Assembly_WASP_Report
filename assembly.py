from db import create_db_conn
import requests
import json

#requests WASP for the details of an assembly
def assembly_api_call(assembly_number):
    url = f"http://i2techinventory:8703/public-api/ic/item/getassemblyitem/{assembly_number}"

    payload = json.dumps({})

    # I am using my own API key, need to update this later to a different user's API key
    headers = {
    'Authorization': 'Bearer JlJlZnJlc2hfdG9rZW49UlQ6Rl0qOW8hSXQxI3RAamRsZWNmRyVLb1VJUXNxJi5pc3N1ZWQ9MjAyNi0wMy0yN1QyMTowODowNS43ODE5NDE4WiYuZXhwaXJlcz0yMDk5LTEyLTMxVDAwOjAwOjAwLjAwMDAwMDBaJlRva2VuPWh2WWlyMEM5bDhZOEdETnBDQnk2VHBQYk5XcEgwanA5Z1VpbENabVNaalpfNUJsWVJHcXB5QV9JdUJYOWtrX250LTNhWTZsLWRaRXZkR19KWFRJYXlldXJ4WmlROUdQcjAxcGNDWkxJaHh5eklsd0lYLXdOckNXV0xRdGhRV0NhZDJYVkFkV0xRbEtSVzhwdlpSZGxpWVRKZmlXeC1ja0ZMMzFZaU53dDFpUkpUVmZzSzlKM1AzMjlNNHN4NDhaeHFrYTRmMUtWN1BiX01CbE5EbExLZmxSUDFXQlZTU3BSM2ROaHA1ai1QeDZmR3BTRHQ0VkJST05oRTVjQ0FCMjIyWkdoY2k0R05EVXlDdW9tZ3BqMXNfUHpKMDJiQmpHOTBvSy1Kcnp4U01PeTFYMkJhbFJxQ2ZKbXVGNW9NT3FZcUFwUjhueDFwWks4djV2eGQ5MWRFX3FxVnF3JmNsaWVudF9pZD1JbnZlbnRvcnlDb250cm9sX2xvY2FsaG9zdCZVc2VySWQ9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUzJnJvbGVzPUFQSSBMb2dpbiZodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lPWJyYW5kb24uZGluaEBpMnRlY2hpbmMuY29tJmh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL25hbWVpZGVudGlmaWVyPTU2ZTVlNzU0LTc3NDQtNDJlYi1hNzZmLTU4MjdlMTM4YzllMyZodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL2FjY2Vzc2NvbnRyb2xzZXJ2aWNlLzIwMTAvMDcvY2xhaW1zL2lkZW50aXR5cHJvdmlkZXI9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUz',
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    # assembly_details = response.text
    # print(assembly_details)
    return response.json()

# gets a list of all unique assembly numbers
def get_all_assemblies(conn=None):
    if conn is None:
        conn = create_db_conn()
        close_after = True
    else:
        close_after = False

    try:
        cursor = conn.cursor()
        cursor.execute("""SELECT DISTINCT ON (WASPNumber) id
                            FROM items
                            WHERE type = 'Assembly'
                            ORDER BY WASPNumber, id DESC;
                       """)
        return [row[0] for row in cursor.fetchall()] # returns a list of all of the unique assemblies
    except Exception as e:
        print('Failed to get all assembly numbers', e)
    finally:
        if close_after:
            conn.close()

# gets a concatenation of the wasp number of an assembly and its description for the UI
def get_assy_wasp_and_desc(unit_type=None, conn=None):
    if conn is None:
        conn=create_db_conn()
        close_after = True
    else:
        close_after = False

    try:
        cursor = conn.cursor()
        params = (
            ['8%', '9%', 'A%', 'B%', 'C%', 'X%'],
            unit_type if unit_type else ['%']
        )
        cursor.execute("""
                        SELECT DISTINCT waspnumber, description
                        FROM items
                        WHERE type = 'Assembly' AND waspnumber LIKE ANY(%s) AND category LIKE ANY(%s)
                        ORDER BY waspnumber;
                    """, params)
        rows = cursor.fetchall()

        assembly_list = [
            {"waspnumber": row[0], "description": row[1]}
        for row in rows
        ]

        return assembly_list
        
    finally:
        if close_after:
            conn.close()

#make/update assembly table containing all of the assemblies
def update_bom_table():
    try:
        conn = create_db_conn()
        cursor = conn.cursor()

        # Drop table if exists
        cursor.execute("DROP TABLE IF EXISTS bom")

        # structure is as follows:
        # each component of an assembly will get an entry into this table as a component_item_id, with the corresponding parent id
        # the cost will be the cost of the component in the context of being inside its particular parent
        # so if for example one item is in multiple assemblies, it will have multiple entries in this table with different parent ids and potentially different costs
        # TODO: the WASP API is broken, getting the costs of each of the components in a BOM doesn't work. Falling back to the cost of the item listed in its item page for now until they fix
        create_bom = """
        CREATE TABLE bom (
            parent_item_id INTEGER NOT NULL REFERENCES items(id),
            component_item_id INTEGER NOT NULL REFERENCES items(id),
            quantity NUMERIC NOT NULL,
            cost NUMERIC NOT NULL,
            scrap_on_disassembly BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (parent_item_id, component_item_id)
        );
        """
        cursor.execute(create_bom)

        assembly_numbers = get_all_assemblies(conn) #list of all assembly IDs

        for assembly_num in assembly_numbers:
            cursor.execute("SELECT WASPNumber FROM items WHERE id = %s", (assembly_num,)) #get waspnumber 
            assembly_wasp_num = cursor.fetchone()[0]

            raw_bom = assembly_api_call(assembly_wasp_num) # call wasp api for the assembly details
            bom = raw_bom["Data"]["ItemBillOfMaterials"] # drill into where the actual bom is in the json response

            for component in bom:
                component_wasp = component["ItemNumber"]
                quantity = component["Quantity"]
                cost = component["Cost"]
                scrap_on_disassembly = component["ScrapOnDisassembly"]

                # get component id
                cursor.execute(
                    "SELECT id FROM items WHERE waspnumber = %s LIMIT 1;",
                    (component_wasp,)
                )
                component_id = cursor.fetchone()[0]

                # insert into bom table
                # ON CONFLICT DO UPDATE SET is for if there are duplicate entries for an item in a bom (this can happen due to how WASP handles entering an item into a BOM that was already there)
                cursor.execute(
                    """
                    INSERT INTO bom (parent_item_id, component_item_id, quantity, cost, scrap_on_disassembly)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (parent_item_id, component_item_id)
                    DO UPDATE SET
                        quantity = bom.quantity + EXCLUDED.quantity,
                        cost = EXCLUDED.cost,
                        scrap_on_disassembly = EXCLUDED.scrap_on_disassembly
                    """,
                    (assembly_num, component_id, quantity, cost, scrap_on_disassembly)
                )
        conn.commit()

        cursor.close()
        conn.close()
        

    except Exception as e:
        print('Failed bom update', e)