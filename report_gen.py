from db import create_db_conn
import requests
import json
import pandas as pd

# need to define parameters
# this function is to generate the report in a spreadsheet for the user to review
# needs to take into account the assembly number and the contract that the program should calculate inventory from
def create_report(assembly_num):
    assembly_cat = None
    try:
        conn = create_db_conn()
        cursor = conn.cursor()

        cursor.execute("""
                        SELECT Category
                        FROM items
                        WHERE WASPNumber = %s
                       """,
                       (assembly_num,))
        assembly_cat = cursor.fetchone()[0] # this determines which site we can pull from

        cursor.close()
        conn.close()
    except Exception as e:
        print('Failed getting assembly category', e)

    # depending on the unit the assembly is for, the site that you can pull parts from changes
    match assembly_cat:
        case '616-12 RGI35 i2AX(BLK2)':
            try:
                conn = create_db_conn()
                cursor = conn.cursor()

                # Need to get all items in BOM for assembly, their quantities in the BOM, their cost, and the amount of each item available in the appropriate site
                # then need to write result to a spreadsheet (csv/xlsx)
                cursor.execute("""SELECT id 
                               FROM items 
                               WHERE WASPNumber = %s
                               ORDER BY id DESC
                               LIMIT 1
                               """, (assembly_num,))
                assembly_id = cursor.fetchone()[0] 
                print("assembly_id:", assembly_id)
                cursor.execute(
                    "SELECT * FROM bom WHERE parent_item_id = %s",
                    (assembly_id,)
                )
                print("bom rows:", cursor.fetchall())
                get_report = """
                            SELECT
                                parent.waspnumber AS assembly,
                                comp_master.waspnumber AS component,
                                comp_master.description AS component_description,
                                b.quantity AS bom_quantity,
                                b.cost AS bom_cost,
                                COALESCE(SUM(inv.totalavailable), 0) AS qty_available
                            FROM bom b

                            -- parent assembly
                            JOIN items parent
                                ON parent.id = b.parent_item_id

                            -- component "master" row
                            JOIN items comp_master
                                ON comp_master.id = b.component_item_id

                            -- all inventory rows for that component, only pulling from specified site
                            LEFT JOIN items inv
                                ON inv.waspnumber = comp_master.waspnumber
                            AND inv.sitename = %s

                            WHERE parent.id = %s

                            GROUP BY
                                assembly,
                                component,
                                component_description,
                                b.quantity,
                                b.cost

                            ORDER BY comp_master.waspnumber;
                            """
                cursor.execute(get_report, ('RGI35 i2Tech Stock', assembly_id))
                rows = cursor.fetchall()
                for row in rows:
                    print(row)

            except Exception as e:
                print('Failed to create report', e)

        case '910-01 i2DAS (QIN05, QIN11)':
            # try:
            #     conn = create_db_conn()
            #     cursor = conn.cursor()

            #     # Need to get all items in BOM for assembly, their quantities in the BOM, their cost, and the amount of each item available in the appropriate site
            #     # then need to write result to a spreadsheet (csv/xlsx)
            #     cursor.execute("""SELECT id 
            #                    FROM items 
            #                    WHERE WASPNumber = %s
            #                    ORDER BY id DESC
            #                    LIMIT 1
            #                    """, (assembly_num,))
            #     assembly_id = cursor.fetchone()[0] 
            #     print("assembly_id:", assembly_id)
            #     cursor.execute(
            #         "SELECT * FROM bom WHERE parent_item_id = %s",
            #         (assembly_id,)
            #     )
            #     print("bom rows:", cursor.fetchall())
            #     get_report = """
            #                 SELECT
            #                     parent.waspnumber AS assembly,
            #                     comp_master.waspnumber AS component,
            #                     b.quantity AS bom_quantity,
            #                     b.cost AS bom_cost,
            #                     COALESCE(SUM(inv.totalavailable), 0) AS qty_available
            #                 FROM bom b

            #                 -- parent assembly
            #                 JOIN items parent
            #                     ON parent.id = b.parent_item_id

            #                 -- component "master" row
            #                 JOIN items comp_master
            #                     ON comp_master.id = b.component_item_id

            #                 -- all inventory rows for that component, only pulling from specified site
            #                 LEFT JOIN items inv
            #                     ON inv.waspnumber = comp_master.waspnumber
            #                 AND inv.sitename = %s

            #                 WHERE parent.id = %s

            #                 GROUP BY
            #                     parent.waspnumber,
            #                     comp_master.waspnumber,
            #                     b.quantity,
            #                     b.cost

            #                 ORDER BY comp_master.waspnumber;
            #                 """
            #     cursor.execute(get_report, ('910-01 i2DAS (QIN05, QIN11)', assembly_id))
            #     rows = cursor.fetchall()
            #     for row in rows:
            #         print(row)

            # except Exception as e:
            #     print('Failed to create report', e)
            pass

        case _:
            print('Please choose an assembly designated as part of the BOM')
