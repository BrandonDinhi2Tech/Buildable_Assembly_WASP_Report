from db import create_db_conn

# this list stores the default presets
# TODO: make a BOM for the entire i2DAS and then make a preset for it
# TODO: make more default presets
DEFAULT_PRESETS = [
    {
        "name": "RGI35 Including Inspection, Kitted, Cost",
        "assembly_id": "X61612 - 616-12 i2AX(BLK2) BOM by item",
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
        "assembly_id": "A61612 - i2AX(BLK2) Gimbal Major Parts Including Housing",
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
        "assembly_id": "A91002 - Major items for i2DAS QIN05 QIN11",
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
        "assembly_id": "C91002 - Housing Items for i2DAS QIN05 QIN11",
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
        "assembly_id": "X91002 - 910-02 i2DAS BOM by item",
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
                    name, assembly_id, contract, include_inspection, include_on_order,
                    include_kitted, include_assembled, include_cost, desired_amount
                )
                VALUES (
                    %(name)s, %(assembly_id)s, %(contract)s, %(include_inspection)s,
                    %(include_on_order)s, %(include_kitted)s, %(include_assembled)s,
                    %(include_cost)s, %(desired_amount)s
                )
                ON CONFLICT (name) DO UPDATE SET
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
        for p in DEFAULT_PRESETS:
            cursor.execute(
                """INSERT INTO presets (
                    name, assembly_id, contract, include_inspection, include_on_order,
                    include_kitted, include_assembled, include_cost, desired_amount
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (name) DO NOTHING;
            """, (
                p['name'],
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

