import item
import assembly
import location
import report_gen
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os

class BuildableAssemblyWaspReportGenerator:
    list_of_contracts = ['RGI35', 'QIN05', 'QIN11', 'General'] # list of contracts
    def __init__(self, root):
        self.refresh_database(refresh_combobox=False)
        self.root = root
        self.root.minsize(800, 600)
        self.root.title("Buildable Assembly WASP Report Generator")
        mainframe = ttk.Frame(root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=("N", "W", "E", "S"))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # row 0
        tk.Label(mainframe, text="Assembly:").grid(row=0, column=0, sticky="e")
        self.assembly_combobox = ttk.Combobox(mainframe, width=80, state="readonly")
        # populate the combobox with the list of assemblies and their descriptions
        try:
            self.assembly_list = assembly.get_assy_wasp_and_desc()
            display_values = [
                f"{a['waspnumber']} - {a['description']}"
            for a in self.assembly_list
            ]
        except Exception as e:
            messagebox.showerror("Failed getting assembly list", str(e))
        self.assembly_combobox['values'] = display_values
        if self.assembly_list:
            self.assembly_combobox.current(0)
        self.assembly_combobox.grid(row=0, column=1, columnspan=2)

        #row 1
        tk.Label(mainframe, text="Contract/GO#:").grid(row=1, column=0, sticky="e")
        self.contract_combobox = ttk.Combobox(mainframe, width=80, state="readonly")
        # populate the combobox with the list of contracts
        self.contract_combobox['values'] = self.list_of_contracts
        if self.list_of_contracts:
            self.contract_combobox.current(0)
        self.contract_combobox.grid(row=1, column=1, columnspan=2)

        #row 2
        tk.Label(mainframe, text="Include Inspection QTY in Available QTY?:").grid(row=2, column=0, sticky="w")
        self.include_inspection = tk.BooleanVar() # stores the boolean value returned from the inspection checkbox
        self.include_inspection_check = ttk.Checkbutton(mainframe, text='Yes/No', variable=self.include_inspection, onvalue=True, offvalue=False)
        self.include_inspection_check.grid(row=2, column=1, sticky="w")

        #row 3
        tk.Label(mainframe, text="Include On-Order QTY in Available QTY?:").grid(row=3, column=0, sticky="e")
        self.include_on_order = tk.BooleanVar() # stores the boolean value returned from the on order checkbox
        self.include_on_order_check = ttk.Checkbutton(mainframe, text='Yes/No', variable=self.include_on_order, onvalue=True, offvalue=False)
        self.include_on_order_check.grid(row=3, column=1, sticky="w")

        #row 4
        tk.Label(mainframe, text="Desired Amount of Units:").grid(row=4, column=0, sticky="e")
        self.desired_amount = tk.IntVar() # stores the desired amount
        self.desired_amount_entry = ttk.Entry(mainframe, width=20, textvariable=self.desired_amount)
        self.desired_amount_entry.grid(row=4, column=1, sticky="w")

        #row 5
        tk.Label(mainframe, text="Include Cost?:").grid(row=5, column=0, sticky="e")
        self.include_cost = tk.BooleanVar() # stores the boolean value for whether or not to include cost
        self.include_cost_check = ttk.Checkbutton(mainframe, text='Yes/No', variable=self.include_cost, onvalue=True, offvalue=False)
        self.include_cost_check.grid(row=5, column=1, sticky="w")

        #row 6
        tk.Label(mainframe, text="Output Directory:").grid(row=6, column=0, sticky="e")
        self.output_folder = tk.StringVar() # stores the output folder directory
        self.output_folder_entry = ttk.Entry(mainframe, width=65, textvariable=self.output_folder)
        self.output_folder_entry.grid(row=6, column=1, sticky="w")
        self.browse_output_folder_button = ttk.Button(mainframe, text="Browse", command=self.browse_output_folder, width=10)
        self.browse_output_folder_button.grid(row=6, column=2, padx=2)

        #row 7
        self.refresh_database_button = ttk.Button(mainframe, text="Refresh Database (connect to i2TechInventory WiFi before clicking)", command=lambda: self.refresh_database(refresh_combobox=True))
        self.refresh_database_button.grid(row=7, column=0, columnspan=3)

        #row 8
        self.generate_report_button = ttk.Button(mainframe, text="Generate Report", command=self.report_gen_wrapper)
        self.generate_report_button.grid(row=8, column=0, columnspan=3)



    def browse_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder.set(folder_selected)

    def refresh_database(self, refresh_combobox):
        try:
            location.update_location_table()
            item.entire_inventory_api_call('item_list.csv')
            item.inventory_to_database('item_list.csv')
            assembly.update_bom_table()
            
            if refresh_combobox:
                # refresh the assembly combobox with the up to date values
                try:
                    self.assembly_list = assembly.get_assy_wasp_and_desc()
                    display_values = [
                        f"{a['waspnumber']} - {a['description']}"
                    for a in self.assembly_list
                    ]
                except Exception as e:
                    messagebox.showerror("Failed getting assembly list", str(e))
                self.assembly_combobox['values'] = display_values
                if self.assembly_list:
                    self.assembly_combobox.current(0)

            messagebox.showinfo(title='Database Refresh', message='Refreshed database successfully!')
        except Exception as e:
            messagebox.showerror('Failed to refresh database', str(e))

    def report_gen_wrapper(self):
        index = self.assembly_combobox.current()
        if index == -1:
            messagebox.showerror("Error", "Please select an assembly")
            return
        else:
            waspnumber = self.assembly_list[index]['waspnumber']

        # falling back to current directory if output directory isn't chosen by user
        output_dir = self.output_folder.get()
        if not output_dir:
            output_dir = os.getcwd()

        try:
            if self.desired_amount == 0:
                report_gen.create_report(assembly_num=waspnumber, 
                                        contract=self.contract_combobox.get(), 
                                        include_inspection=self.include_inspection.get(), 
                                        include_cost=self.include_cost.get(),
                                        output_directory=output_dir)
            else:
                report_gen.create_report(assembly_num=waspnumber, 
                                        contract=self.contract_combobox.get(), 
                                        include_inspection=self.include_inspection.get(), 
                                        include_cost=self.include_cost.get(), 
                                        desired_amount=self.desired_amount.get(),
                                        output_directory=output_dir)
            messagebox.showinfo(title='Generate Report', message=f"Generated report successfully at {output_dir}!")
        except Exception as e:
            messagebox.showerror('Failed to generate report', str(e))
        

        

if __name__ == "__main__":
    root = tk.Tk()
    app = BuildableAssemblyWaspReportGenerator(root)
    root.mainloop()

    # ----------------------------- unit test -------------------------------------
    # location.update_location_table()
    # item.entire_inventory_api_call('item_list.csv')
    # item.inventory_to_database('item_list.csv')
    # assembly.update_bom_table()
    # report_gen.create_report('800002', 'RGI35', include_cost=True, include_inspection=True, include_on_order=True, desired_amount=50)