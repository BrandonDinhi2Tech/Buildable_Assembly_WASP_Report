from db import create_db_conn
from assembly import get_assy_wasp_and_desc

# this list stores the default presets
# TODO: make a BOM for the entire i2DAS and then make a preset for it
# TODO: make more default presets
def get_specific_assembly_and_desc(assembly_id, assembly_list):
    for a in assembly_list:
        if a['waspnumber'] == assembly_id:
            return f"{a['waspnumber']} - {a['description']}"
    return assembly_id

def build_default_presets():
    assembly_list = get_assy_wasp_and_desc()
    return [
        {
            "name": "RGI35 Including Inspection, Kitted, Cost",\
            "unit_type": 'i2AX(BLK2) 616-12',
            "assembly_id": get_specific_assembly_and_desc('X61612', assembly_list),
            "contract": "RGI35",
            "include_inspection": True,
            "include_on_order": False,
            "include_kitted": True,
            "include_assembled": False,
            "include_cost" : True,
            "desired_amount": None
        },
        {
            "name": "RGI35 Major Parts Including Inspection, Kitted, Cost",
            "unit_type": 'i2AX(BLK2) 616-12',
            "assembly_id": get_specific_assembly_and_desc('A61612', assembly_list),
            "contract": "RGI35", 
            "include_inspection": True,
            "include_on_order": False,
            "include_kitted": True,
            "include_assembled": False,
            "include_cost": True,
            "desired_amount": None
        },
        {
            "name": "QIN11 Major Parts Including Inspection, Kitted, Cost",
            "unit_type": 'i2DAS 910-02',
            "assembly_id": get_specific_assembly_and_desc('A91002', assembly_list),
            "contract": "QIN11", 
            "include_inspection": True,
            "include_on_order": False,
            "include_kitted": True,
            "include_assembled": False,
            "include_cost": True,
            "desired_amount": None
        },
        {
            "name": "QIN11 Housing Including Inspection, Kitted, Cost",
            "unit_type": 'i2DAS 910-02',
            "assembly_id": get_specific_assembly_and_desc('C91002', assembly_list),
            "contract": "QIN11", 
            "include_inspection": True,
            "include_on_order": False,
            "include_kitted": True,
            "include_assembled": False,
            "include_cost": True,
            "desired_amount": None
        },
        {
            "name": "QIN11 Including Inspection, Kitted, Cost",
            "unit_type": 'i2DAS 910-02',
            "assembly_id": get_specific_assembly_and_desc('X91002', assembly_list),
            "contract": "QIN11", 
            "include_inspection": True,
            "include_on_order": False,
            "include_kitted": True,
            "include_assembled": False,
            "include_cost": True,
            "desired_amount": None
        }
    ]

def ensure_table(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS presets (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                unit_type TEXT,
                assembly_id TEXT,
                contract TEXT, 
                include_inspection BOOLEAN,
                include_on_order BOOLEAN,
                include_kitted BOOLEAN,
                include_assembled BOOLEAN,
                include_cost BOOLEAN,
                desired_amount INTEGER,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """
    )
    conn.commit()

def save_preset(name, preset: dict, conn=None):
    if conn is None:
        conn = create_db_conn()
        close_after = True
    else:
        close_after = False

    try:
        ensure_table(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
                INSERT INTO presets (
                    name, unit_type, assembly_id, contract, include_inspection, include_on_order,
                    include_kitted, include_assembled, include_cost, desired_amount
                )
                VALUES (
                    %(name)s, %(unit_type)s, %(assembly_id)s, %(contract)s, %(include_inspection)s,
                    %(include_on_order)s, %(include_kitted)s, %(include_assembled)s,
                    %(include_cost)s, %(desired_amount)s
                )
                ON CONFLICT (name) DO UPDATE SET
                    unit_type = EXCLUDED.unit_type,
                    assembly_id = EXCLUDED.assembly_id,
                    contract = EXCLUDED.contract,
                    include_inspection = EXCLUDED.include_inspection,
                    include_on_order = EXCLUDED.include_on_order,
                    include_kitted = EXCLUDED.include_kitted,
                    include_assembled = EXCLUDED.include_assembled,
                    include_cost = EXCLUDED.include_cost,
                    desired_amount = EXCLUDED.desired_amount;
            """, {"name": name, **preset}
        )
        conn.commit()

    finally:
        cursor.close()
        if close_after:
            conn.close()

def load_presets(conn=None):
    if conn is None:
        conn = create_db_conn()
        close_after = True
    else:
        close_after = False

    try:
        ensure_table(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM presets ORDER BY name;")
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()
        if close_after:
            conn.close()

def delete_preset(name, conn=None):
    if conn is None:
        conn = create_db_conn()
        close_after = True
    else:
        close_after = False

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM presets WHERE name = %s;", (name,))
        conn.commit()
    finally:
        cursor.close()
        if close_after:
            conn.close()

def create_default_presets(conn=None):
    if conn is None:
        conn = create_db_conn()
        close_after = True
    else:
        close_after = False

    try:
        ensure_table(conn)
        cursor = conn.cursor()
        for p in build_default_presets():
            cursor.execute(
                """INSERT INTO presets (
                    name, unit_type, assembly_id, contract, include_inspection, include_on_order,
                    include_kitted, include_assembled, include_cost, desired_amount
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (name) DO UPDATE SET 
                    unit_type = EXCLUDED.unit_type,
                    assembly_id = EXCLUDED.assembly_id,
                    contract = EXCLUDED.contract,
                    include_inspection = EXCLUDED.include_inspection,
                    include_on_order = EXCLUDED.include_on_order,
                    include_kitted = EXCLUDED.include_kitted,
                    include_assembled = EXCLUDED.include_assembled,
                    include_cost = EXCLUDED.include_cost,
                    desired_amount = EXCLUDED.desired_amount;
            """, (
                p['name'],
                p['unit_type'],
                p['assembly_id'],
                p['contract'],
                p['include_inspection'],
                p['include_on_order'],
                p['include_kitted'],
                p['include_assembled'],
                p['include_cost'],
                p['desired_amount']
            ))
            conn.commit()
    finally:
        cursor.close()
        if close_after:
            conn.close()

