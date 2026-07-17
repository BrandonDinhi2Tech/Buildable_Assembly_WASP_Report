from db import create_db_conn
import item
import pandas as pd
from datetime import datetime
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter
import os

# builds the query that generates the report
def build_report_query(
    assembly_id,
    contract,
    include_cost=False,
    include_inspection=False,
    include_on_order=False,
    include_kitted=False,
    desired_amount=None,
    include_assembled=False
):
    params = []

    # getting the total amount of each inventory item in each top level BOM
    # this accounts for multi-level BOMs
    assembly_inclusion = "WHERE root_item.sitename = ANY(%s) " # TODO: this should always include the assemblies in the stock assigned to the contract, but it seems that it's not working
    if include_kitted:
        assembly_inclusion = assembly_inclusion + "OR root_item.locationcode LIKE ANY(%s) "
    if include_assembled:
        assembly_inclusion = assembly_inclusion + "OR root_item.category = ANY(%s) "
    cte = f"""
            WITH RECURSIVE flattened_bom AS (
                SELECT 
                    b.parent_item_id AS root_item_id,
                    b.component_item_id,
                    b.quantity::numeric AS total_quantity
                FROM bom b

                JOIN items root_item
                ON root_item.id = b.parent_item_id
                {assembly_inclusion}

                UNION ALL

                SELECT
                    fb.root_item_id,
                    b.component_item_id,
                    fb.total_quantity * b.quantity
                FROM flattened_bom fb
                JOIN bom b
                    ON fb.component_item_id = b.parent_item_id
            ) 
    """

    # ----------------------------
    # 1. SELECT base columns
    # ----------------------------
    select_parts = [
        'parent.waspnumber AS "Assembly"',
        'comp_master.waspnumber AS "Component"',
        'comp_master.category AS "Component Category"',
        'comp_master.description AS "Component Description"',
        'comp_master.manufacturer AS "Component Manufacturer"',
        'b.quantity AS "Quantity in BOM"'
    ]

    if include_cost:
        select_parts.append('comp_master.cost AS "Component Cost"')

    select_parts.append('COALESCE(inv.totalavailable, 0) AS "Available Quantity In Contract\'s Stock"')

    if include_inspection:
        select_parts.append('COALESCE(inspection.totalavailable, 0) AS "Quantity Pending Inspection"')

    if include_on_order:
        select_parts.append('COALESCE(comp_master.onorder, 0) AS "Quantity on Order"')

    if include_kitted:
        select_parts.append('COALESCE(kit.totalavailable, 0) AS "Quantity Kitted for Contract"')

    select_parts.append('COALESCE(assembled.totalavailable, 0) AS "Quantity in Assembled Assemblies"')
    
    

    # ----------------------------
    # 2. Build availability expression
    # ----------------------------
    available_terms = ['COALESCE(inv.totalavailable, 0)']

    if include_inspection:
        available_terms.append('COALESCE(inspection.totalavailable, 0)')

    if include_on_order:
        available_terms.append('COALESCE(comp_master.onorder, 0)')

    if include_kitted:
        available_terms.append('COALESCE(kit.totalavailable, 0)')

    available_terms.append('COALESCE(assembled.totalavailable, 0)')

    available_expr = " + ".join(available_terms)

    # Add computed columns
    select_parts.append(f'{available_expr} AS "Total Available Quantity"')
    select_parts.append(f'FLOOR(({available_expr}) / b.quantity) AS "Buildable Amount"')

    if desired_amount:
        select_parts.append(f'({available_expr} - %s * b.quantity) AS "Available-Desired Quantity"')
        

    # ----------------------------
    # 3. Contract -> parameters
    # ----------------------------
    contract_map = {
        'RGI35': {
            'stock': ['RGI35 i2Tech Stock'],
            'kit_patterns': ['%RGI35%', '%LV-L01%'],
            'assy_category': ['616-12 RGI35 i2AX(BLK2)']
        },
        'QIN05': {
            'stock': ['QIN05-STK'],
            'kit_patterns': ['%QIN05%'],
            'assy_category': ['910-02 i2DAS (QIN05, QIN11)']
        },
        'QIN11': {
            'stock': ['QIN11-STK'],
            'kit_patterns': ['%QIN11%'],
            'assy_category': ['910-02 i2DAS (QIN05, QIN11)']
        },
        'General Stock': {
            'stock': 'SiteA',
            'kit_patterns': ['%SiteA%'],
            'assy_category': ['910-02 i2DAS (QIN05, QIN11)', '616-12 RGI35 i2AX(BLK2)', '610-10 xxx i2ULS(BLK3)']
        },
        'All': {
            'stock': ['RGI35 i2Tech Stock', 'QIN05-STK', 'QIN11-STK', 'SiteA'],
            'kit_patterns': ['%RGI35%', '%LV-L01%', '%QIN05%', '%QIN11%', '%SiteA%'],
            'assy_category': ['910-02 i2DAS (QIN05, QIN11)', '616-12 RGI35 i2AX(BLK2)', '610-10 xxx i2ULS(BLK3)']
        }
    }

    if contract not in contract_map:
        raise ValueError("Invalid contract")

    stock_site = contract_map[contract]['stock']
    kit_patterns = contract_map[contract]['kit_patterns']
    assy_category = contract_map[contract]['assy_category']

    params.append(stock_site) # root_item.sitename
    if include_kitted:
        params.append(kit_patterns) # root_item.location
    if include_assembled:
        params.append(assy_category) # root_item.category
    if desired_amount:
        params.append(desired_amount)
    params.append(stock_site)
    params.append(kit_patterns)
    params.append(assembly_id)

    # ----------------------------
    # 4. Additions to Query to Allow for Including Assembled QTY
    # ----------------------------


    # this multiplies the amount of each assembly already assembled by the amount of the item in its BOM
    # in order to get the amount of each item that has already been put into a built assembly
    assembled_join = """
        LEFT JOIN (
            SELECT
                fb.component_item_id,
                SUM(parent_inv.totalavailable * fb.total_quantity) AS totalavailable
            FROM flattened_bom fb

            JOIN items root_item
            ON root_item.id = fb.root_item_id

            JOIN (
                SELECT waspnumber, SUM(totalavailable) AS totalavailable
                FROM items
                GROUP BY waspnumber
            ) parent_inv
                ON parent_inv.waspnumber = root_item.waspnumber

            GROUP BY fb.component_item_id
        ) assembled
            ON assembled.component_item_id = comp_master.id
    """

    group_by_parts = [
        'parent.waspnumber',
        'comp_master.waspnumber',
        'comp_master.description',
        'b.quantity',
        'comp_master.manufacturer',
        'comp_master.category',
        'inv.totalavailable'
    ]

    group_by_parts.append('assembled.totalavailable')
    if include_on_order:
        group_by_parts.append('comp_master.onorder')
    if include_inspection:
        group_by_parts.append('inspection.totalavailable')
    if include_kitted:
        group_by_parts.append('kit.totalavailable')
    if include_cost:
        group_by_parts.append('comp_master.cost')
    

    # ----------------------------
    # 5. Final query
    # ----------------------------
    query = f"""
        {cte}

        SELECT
            {",\n            ".join(select_parts)}

        FROM bom b

        JOIN items parent
            ON parent.id = b.parent_item_id

        JOIN items comp_master
            ON comp_master.id = b.component_item_id

        LEFT JOIN (
            SELECT waspnumber, SUM(totalavailable) AS totalavailable, MAX(onorder) as onorder
            FROM items
            WHERE sitename = ANY(%s)
            GROUP BY waspnumber
        ) inv
            ON inv.waspnumber = comp_master.waspnumber

        LEFT JOIN (
            SELECT waspnumber, SUM(totalavailable) AS totalavailable
            FROM items
            WHERE sitename = 'Lab'
              AND locationcode = 'Inspection'
            GROUP BY waspnumber
        ) inspection
            ON inspection.waspnumber = comp_master.waspnumber

        LEFT JOIN (
            SELECT waspnumber, SUM(totalavailable) AS totalavailable
            FROM items
            WHERE locationcode LIKE ANY(%s)
            GROUP BY waspnumber
        ) kit
            ON kit.waspnumber = comp_master.waspnumber

        {assembled_join}

        WHERE parent.id = %s

        GROUP BY {", ".join(group_by_parts)}

        ORDER BY comp_master.waspnumber;
    """

    return query, params

# builds the output file name
def build_output_filename(
    assembly_num,
    contract,
    include_cost=False,
    include_inspection=False,
    include_on_order=False,
    include_kitted=False,
    desired_amount=None,
    include_assembled=False
):
    parts = [f"{assembly_num} Report for {contract}", "Including"]

    # flags
    parts.append("Cost" if include_cost else "No Cost")

    if include_inspection:
        parts.append("Inspection")

    if include_on_order:
        parts.append("On-Order")

    if include_kitted:
        parts.append("Kitted")

    if desired_amount:
        parts.append("Desired Amount")
    
    if include_assembled:
        parts.append("Assembled")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    flags = " ".join(parts)
    filename = f" {timestamp} " + flags + ".xlsx"

    return flags, filename


# this function is to generate the report in a spreadsheet for the user to review
# uses the helper functions in order to generate the query and filename
# this function handles the actual output to a spreadsheet 
def create_report(
    assembly_num, 
    contract, 
    output_directory, 
    include_inspection=False, 
    include_on_order=False, 
    include_kitted=False, 
    include_cost=False, 
    desired_amount=None,
    list_of_contracts=None,
    include_assembled=False,
    preset_name=None
):

    # depending on the contract, the site that you can pull parts from changes
    try:
        conn = create_db_conn()
        cursor = conn.cursor()

        # # Need to get all items in BOM for assembly, their quantities in the BOM, their cost, and the amount of each item available in the appropriate site
        # # then need to write result to a spreadsheet (csv/xlsx)
        cursor.execute("""SELECT id 
                        FROM items 
                        WHERE WASPNumber = %s
                        ORDER BY id DESC
                        LIMIT 1
                        """, (assembly_num,))
        assembly_id = cursor.fetchone()[0] 

        # building the report query and the params for the query execution
        get_report, params = build_report_query(assembly_id=assembly_id,
                                                contract=contract,
                                                include_cost=include_cost,
                                                include_inspection=include_inspection,
                                                include_on_order=include_on_order,
                                                include_kitted=include_kitted,
                                                desired_amount=desired_amount,
                                                include_assembled=include_assembled)
        
        # building the output filename and the flags for the in-report title
        report_title_flags, file_name=build_output_filename(assembly_num=assembly_num,
                                        contract=contract,
                                        include_cost=include_cost,
                                        include_inspection=include_inspection,
                                        include_on_order=include_on_order,
                                        include_kitted=include_kitted,
                                        desired_amount=desired_amount,
                                        include_assembled=include_assembled)
        
        # if a preset is actually selected, then use it as the file name
        if preset_name:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            file_name = f" {timestamp} " + preset_name + ".xlsx"
        
        # accounting for the user's chosen output directory
        if output_directory:
            full_path = os.path.join(output_directory, file_name)
        
        #execute the query if the contract is in the list of contracts
        df = None
        if contract in list_of_contracts:
            print(get_report)
            df = pd.read_sql_query(get_report, conn, params=params)
        else:
            raise ValueError("Pick a valid contract.")

        assembly_buildable = df["Buildable Amount"].min() #amount of the assembly that can be built

        # getting description of the assembly for the title page
        cursor.execute("SELECT description FROM items WHERE waspnumber = %s LIMIT 1;", (assembly_num,))
        assembly_description = cursor.fetchone()[0]

        # getting cost of the assembly for the title page if cost was chosen to be included
        if include_cost:
            assembly_cost = item.get_item_cost(assembly_num, conn)


        # output sql query to excel spreadsheet
        with pd.ExcelWriter(full_path, engine="openpyxl") as writer:
            ws_title = writer.book.create_sheet(title="Title Page")
            ws_title.cell(row=1, column=1, value=f"WASP Buildable Report {report_title_flags}")
            ws_title.cell(row=2, column=1, value=f"BOM: {assembly_num}")
            ws_title.cell(row=3, column=1, value=f"Desc: {assembly_description}")
            ws_title.cell(row=4, column=1, value=f"Buildable Units: {assembly_buildable}")

            if include_cost:
                ws_title.cell(row=5, column=1, value=f"Cost of BOM: ")
                bom_cost_cell = ws_title.cell(row=5, column=2, value=assembly_cost)
                bom_cost_cell.number_format = '"$"#,##0.00' # formatting bom cost into dollars

            ws_title.cell(row=1, column=2, value=f"Date: {datetime.now()}")
            df.to_excel(writer, index=False, sheet_name="Report")

            # highlighting cells that are short in red
            ws_report = writer.book["Report"]

            target_header = "Available-Desired Quantity"

            # trying to find available-desired quantity column
            col_idx = None
            for cell in ws_report[1]:
                if cell.value == target_header:
                    col_idx = cell.column
                    break

            # highlighting all items that are short of meeting the desired amount
            # these quantities will show up as negative
            if col_idx:
                col_letter = get_column_letter(col_idx)
                max_row = len(df) + 1

                ws_report.conditional_formatting.add(
                    f"{col_letter}2:{col_letter}{max_row}",
                    CellIsRule(
                        operator="lessThan",
                        formula=["0"],
                        fill=PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
                    )
                )
            
            target_header = "Component Cost"

            # trying to find component cost column
            col_idx = None
            for cell in ws_report[1]:
                if cell.value == target_header:
                    col_idx = cell.column
                    break

            # formatting all costs to currency format in dollars
            if col_idx:
                col_letter = get_column_letter(col_idx)
                max_row = len(df) + 1

                for row in range(2, max_row+1):
                    cell = ws_report[f"{col_letter}{row}"]
                    cell.number_format = '"$"#,##0.00'

            # autofitting all columns to largest width entry in that column
            for ws in [ws_title, ws_report]:
                for col in ws.columns:
                    col_letter = col[0].column_letter
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    ws.column_dimensions[col_letter].width = max_len + 3


        cursor.close()
        conn.close()

    except Exception as e:
        print('Failed to create report', e)
        raise ValueError(f"Report Generation Error: {e}")