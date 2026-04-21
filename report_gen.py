from db import create_db_conn
import pandas as pd
from datetime import datetime
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter
import os


# this function is to generate the report in a spreadsheet for the user to review
# takes into account the assembly's WASP number and the contract that the program should calculate inventory from
# also takes into account whether or not inspection and/or on-order quantities should be in the buildable amount calculation
# also has option for sanitizing item costs from the report
# also has an option for inputting a desired amount of units to see how available inventory compares to the desired amount
def create_report(assembly_num, contract, output_directory, include_inspection=False, include_on_order=False, include_cost=False, desired_amount=None):

    # depending on the contract, the site that you can pull parts from changes
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
        #print("assembly_id:", assembly_id)
        # cursor.execute(
        #     "SELECT * FROM bom WHERE parent_item_id = %s",
        #     (assembly_id,)
        # )
        #print("bom rows:", cursor.fetchall())
        get_report = """
                            SELECT
                                parent.waspnumber AS "Assembly",
                                comp_master.waspnumber AS "Component",
                                comp_master.category AS "Component Category",
                                comp_master.description AS "Component Description",
                                comp_master.manufacturer AS "Component Manufacturer",
                                b.quantity AS "Quantity in BOM",
                                COALESCE(inv.totalavailable, 0) AS "Available Quantity In Contract's Stock",
                                COALESCE(inspection.totalavailable, 0) AS "Quantity Pending Inspection",
                                COALESCE(comp_master.onorder, 0) AS "Quantity on Order",
                                COALESCE(kit.totalavailable, 0) AS "Quantity Kitted for Contract"
                            """
        params = [] # this will hold all of the %s params for the sql execution later
        output_file_name = f"{assembly_num} Report for {contract}" # this will be the output file name which changes based on the parameters of the report
        output_file_name_addition = " Including" # this will be concatenated to output_file_name if needed
        add_to_output_file_name = False # indicates whether output_file_name needs something added to it

        #if we want to include item costs in the report
        if include_cost == True:
            get_report += """
                            ,
                            comp_master.cost AS "Component Cost"
                        """
            output_file_name_addition += " Cost"
            add_to_output_file_name = True
        else:
            output_file_name_addition += " No Cost"
            add_to_output_file_name = True
        
        # if we want to include pending inspection quantities in the buildable amount calculation
        if include_inspection == True and include_on_order == False:
            get_report += """
                            ,
                            COALESCE(inv.totalavailable, 0) + COALESCE(inspection.totalavailable, 0) AS "Available Quantity Including Items Pending Inspection",
                            FLOOR((COALESCE(inv.totalavailable, 0) + COALESCE(inspection.totalavailable, 0)) / b.quantity) AS "Buildable Amount"
                        """
            output_file_name_addition += " Inspection"
            add_to_output_file_name = True
            if desired_amount:
                get_report += """
                                ,
                                ((COALESCE(inv.totalavailable, 0) + COALESCE(inspection.totalavailable, 0)) - %s * b.quantity) AS "Available-Desired Quantity"
                            """
                params.append(desired_amount)
                output_file_name_addition += " Desired Amount"
                add_to_output_file_name = True

        # if we want to include on order quantities in the buildable amount calculation
        elif include_inspection == False and include_on_order == True:
            get_report += """
                            ,
                            COALESCE(inv.totalavailable, 0) + COALESCE(comp_master.onorder, 0) AS "Available Quantity Including Items On Order",
                            FLOOR((COALESCE(inv.totalavailable, 0) + COALESCE(comp_master.onorder, 0)) / b.quantity) AS "Buildable Amount"
                        """
            output_file_name_addition += " On-Order"
            add_to_output_file_name = True
            if desired_amount:
                get_report += """
                                ,
                                ((COALESCE(inv.totalavailable, 0) + COALESCE(comp_master.onorder, 0)) - %s * b.quantity) AS "Available-Desired Quantity"
                            """
                params.append(desired_amount)
                output_file_name_addition += " Desired Amount"
                add_to_output_file_name = True

        # if we want to include both on order quantities and pending inspection quantities in the buildable amount calculation
        elif include_inspection == True and include_on_order == True:
            get_report += """
                            ,
                            COALESCE(inv.totalavailable, 0) + COALESCE(comp_master.onorder, 0) + COALESCE(inspection.totalavailable, 0) AS "Available Quantity Including Items On Order and Pending Inspection",
                            FLOOR((COALESCE(inv.totalavailable, 0) + COALESCE(comp_master.onorder, 0) + COALESCE(inspection.totalavailable, 0)) / b.quantity) AS "Buildable Amount"
                        """
            output_file_name_addition += " Inspection and On-Order"
            add_to_output_file_name = True
            if desired_amount:
                get_report += """
                                ,
                                ((COALESCE(inv.totalavailable, 0) + COALESCE(comp_master.onorder, 0) + COALESCE(inspection.totalavailable, 0)) - %s * b.quantity) AS "Available-Desired Quantity"
                            """
                params.append(desired_amount)
                output_file_name_addition += " Desired Amount"
                add_to_output_file_name = True

        # if we just want the stock count included in the buildable amount calculation
        else:
            get_report += """
                            ,
                            FLOOR(COALESCE(inv.totalavailable, 0) / b.quantity) AS "Buildable Amount"
                        """
            output_file_name_addition += " Stock Only"
            add_to_output_file_name = True
            if desired_amount:
                get_report += """
                                ,
                                (COALESCE(inv.totalavailable, 0) - %s * b.quantity) AS "Available-Desired Quantity"
                            """
                params.append(desired_amount)
                output_file_name_addition += " Desired Amount"
                add_to_output_file_name = True

        # adding all additional parameters to output file name as well as the file extension and the datetime of creation
        if add_to_output_file_name == True:
            output_file_name += output_file_name_addition
            output_file_name += f" {datetime.now().strftime("%Y-%m-%d_%H%M%S")}.xlsx"
        
        if output_directory:
            full_path = os.path.join(output_directory, output_file_name)

        get_report += """
                    FROM bom b

                    -- parent assembly
                    JOIN items parent
                        ON parent.id = b.parent_item_id

                    -- component "master" row
                    JOIN items comp_master
                        ON comp_master.id = b.component_item_id

                    -- aggregate inventory FIRST
                    LEFT JOIN (
                        SELECT waspnumber, SUM(totalavailable) AS totalavailable, MAX(onorder) as onorder
                        FROM items
                        WHERE sitename = %s
                        GROUP BY waspnumber
                    ) inv
                        ON inv.waspnumber = comp_master.waspnumber

                    -- aggregate inspection FIRST
                    LEFT JOIN (
                        SELECT waspnumber, SUM(totalavailable) AS totalavailable
                        FROM items
                        WHERE sitename = 'Lab'
                        AND locationcode = 'Inspection'
                        GROUP BY waspnumber
                    ) inspection
                        ON inspection.waspnumber = comp_master.waspnumber

                    -- aggregate kitted first
                    LEFT JOIN (
                        SELECT waspnumber, SUM(totalavailable) AS totalavailable
                        FROM items
                        WHERE locationcode LIKE ANY(%s)
                        GROUP BY waspnumber
                    ) kit
                        ON kit.waspnumber = comp_master.waspnumber

                    WHERE parent.id = %s

                    GROUP BY
                        parent.waspnumber,
                        comp_master.waspnumber,
                        comp_master.description,
                        b.quantity,
                        comp_master.cost,
                        comp_master.manufacturer,
                        comp_master.category,
                        inv.totalavailable,
                        comp_master.onorder,
                        inspection.totalavailable,
                        kit.totalavailable

                    ORDER BY comp_master.waspnumber;
                    """
        
        #pick a site to draw parts from, execute the query, and put into dataframe
        df = None
        match contract:
            case 'RGI35':
                params.append('RGI35 i2Tech Stock')
                params.append(['%RGI35%', '%LV-L01%'])
                params.append(assembly_id)
                df = pd.read_sql_query(get_report, conn, params=params)
            case 'QIN05':
                params.append('QIN05-STK')
                params.append(['%QIN05%'])
                params.append(assembly_id)
                df = pd.read_sql_query(get_report, conn, params=params)
            case 'QIN11':
                params.append('QIN11-STK')
                params.append(['%QIN11%'])
                params.append(assembly_id)
                df = pd.read_sql_query(get_report, conn, params=params)
            case 'General':
                params.append('SiteA')
                params.append(['%SiteA%'])
                params.append(assembly_id)
                df = pd.read_sql_query(get_report, conn, params=params)
            case _:
                print("Pick a valid contract.")

        assembly_buildable = df["Buildable Amount"].min() #amount of the assembly that can be built

        # getting description of the assembly for the title page
        cursor.execute("SELECT description FROM items WHERE waspnumber = %s LIMIT 1;", (assembly_num,))
        assembly_description = cursor.fetchone()[0]

        # output sql query to excel spreadsheet
        with pd.ExcelWriter(full_path, engine="openpyxl") as writer:
            ws = writer.book.create_sheet(title="Title Page")
            ws.cell(row=1, column=1, value=f"WASP Buildable Report {output_file_name_addition}")
            ws.cell(row=2, column=1, value=f"BOM: {assembly_num}")
            ws.cell(row=3, column=1, value=f"Desc: {assembly_description}")
            ws.cell(row=4, column=1, value=f"Buildable Units: {assembly_buildable}")

            ws.cell(row=1, column=2, value=f"Date: {datetime.now()}")
            df.to_excel(writer, index=False, sheet_name="Report")

            # highlighting cells that are short in red
            ws = writer.book["Report"]

            target_header = "Available-Desired Quantity"

            # trying to find available-desired quantity column
            col_idx = None
            for cell in ws[1]:
                if cell.value == target_header:
                    col_idx = cell.column
                    break

            # highlighting all items that are short of meeting the desired amount
            # these items will show up as negative
            if col_idx:
                col_letter = get_column_letter(col_idx)
                max_row = len(df) + 1

                ws.conditional_formatting.add(
                    f"{col_letter}2:{col_letter}{max_row}",
                    CellIsRule(
                        operator="lessThan",
                        formula=["0"],
                        fill=PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
                    )
                )


        cursor.close()
        conn.close()

    except Exception as e:
        print('Failed to create report', e)