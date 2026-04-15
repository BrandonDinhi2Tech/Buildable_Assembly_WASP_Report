import item
import assembly
import location
import report_gen
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import datetime

class BuildableAssemblyWaspReportGenerator:
    def __init__(self, root):
        self.root = root
        self.root.minsize(800, 600)
        self.root.title("Buildable Assembly WASP Report Generator")
        mainframe = ttk.Frame(root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=("N", "W", "E", "S"))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # row 0
        tk.Label(mainframe, text="Assembly:").grid(row=0, column=0, sticky="e")
        self.assembly_combobox = ttk.Combobox(mainframe, width=120, state="readonly")
        # populate the combobox with the list of assemblies and their descriptions
        try:
            assembly_list = assembly.get_assy_wasp_and_desc()
            display_values = [
                f"{a['waspnumber']} - {a['description']}"
            for a in assembly_list
            ]
        except Exception as e:
            messagebox.showerror("Failed getting assembly list", str(e))
        self.assembly_combobox['values'] = display_values
        if assembly_list:
            self.assembly_combobox.current(0)
        self.assembly_combobox.grid(row=0, column=1, columnspan=2)
        
if __name__ == "__main__":
    root = tk.Tk()
    app = BuildableAssemblyWaspReportGenerator(root)
    root.mainloop()
    # location.update_location_table()
    # item.entire_inventory_api_call('item_list.csv')
    # item.inventory_to_database('item_list.csv')
    # assembly.update_bom_table()
    # report_gen.create_report('800002', 'RGI35', include_cost=True, include_inspection=True, include_on_order=True, desired_amount=50)