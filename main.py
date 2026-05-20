import item
import assembly
import location
import report_gen
import settings
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import ttkbootstrap
import threading
import datetime

class BuildableAssemblyWaspReportGenerator:
    list_of_contracts = ['RGI35', 'QIN05', 'QIN11', 'General', 'All']

    def __init__(self, root):
        self.root = root
        self.root.title("Buildable Assembly WASP Report Generator")
        self.root.minsize(800, 600)

        mainframe = ttk.Frame(root, padding=15)
        mainframe.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        mainframe.columnconfigure(1, weight=1)

        # attempt to make all fonts size 12, see __main__ for more font size changes (ttkbootstrap requires a different way of setting the font)
        combobox_font = tk.font.Font(family="Segoe UI",size=12)
        root.option_add("*Font", combobox_font)
 

        # Title
        title = ttk.Label(
            mainframe,
            text="Buildable Assembly WASP Report Generator",
            font=("Segoe UI", 16, "bold")
        )
        title.grid(row=0, column=0, columnspan=3, pady=(0, 15))

        # Refresh DB initially
        self.refresh_database(refresh_combobox=False)

        # ------------------ Selection Frame ------------------
        selection_frame = ttk.LabelFrame(mainframe, text="Selection", padding=10)
        selection_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        selection_frame.columnconfigure(1, weight=1)

        ttk.Label(selection_frame, text="Assembly:").grid(row=0, column=0, sticky="e")
        self.assembly_combobox = ttk.Combobox(selection_frame, width=50, state="readonly")

        try:
            self.assembly_list = assembly.get_assy_wasp_and_desc()
            display_values = [
                f"{a['waspnumber']} - {a['description']}"
                for a in self.assembly_list
            ]
        except Exception as e:
            messagebox.showerror("Failed getting assembly list", str(e))
            display_values = []
            self.assembly_list = []

        self.assembly_combobox['values'] = display_values
        if self.assembly_list:
            self.assembly_combobox.current(0)
        self.assembly_combobox.grid(row=0, column=1, sticky="ew")

        ttk.Label(selection_frame, text="Contract/GO#:").grid(row=1, column=0, sticky="e")
        self.contract_combobox = ttk.Combobox(selection_frame, width=50, state="readonly")
        self.contract_combobox['values'] = self.list_of_contracts
        if self.list_of_contracts:
            self.contract_combobox.current(0)
        self.contract_combobox.grid(row=1, column=1, sticky="ew")

        # ------------------ Options Frame ------------------
        options_frame = ttk.LabelFrame(mainframe, text="Availability Options", padding=10)
        options_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)

        self.include_inspection = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Include Inspection Quantity", variable=self.include_inspection).grid(row=0, column=0, sticky="w")

        self.include_on_order = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Include On-Order Quantity", variable=self.include_on_order).grid(row=1, column=0, sticky="w")

        self.include_kitted = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Include Kitted Quantity", variable=self.include_kitted).grid(row=2, column=0, sticky="w")

        self.include_assembled = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Include Assembled Quantity", variable=self.include_assembled).grid(row=3, column=0, sticky="w")

        # ------------------ Settings Frame ------------------
        settings_frame = ttk.LabelFrame(mainframe, text="Settings", padding=10)
        settings_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="Desired Units:").grid(row=0, column=0, sticky="e")
        self.desired_amount_entry = ttk.Entry(settings_frame, width=15, justify="right")
        self.desired_amount_entry.grid(row=0, column=1, sticky="w")

        self.include_cost = tk.BooleanVar()
        ttk.Checkbutton(settings_frame, text="Include Cost", variable=self.include_cost).grid(row=1, column=1, sticky="w")

        # ------------------ Output Frame ------------------
        output_frame = ttk.LabelFrame(mainframe, text="Output", padding=10)
        output_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=5)
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky="e")
        self.output_folder = tk.StringVar()
        self.output_folder_entry = ttk.Entry(output_frame, textvariable=self.output_folder)
        self.output_folder_entry.grid(row=0, column=1, sticky="ew")

        self.browse_output_folder_button = ttk.Button(
            output_frame,
            text="Browse",
            command=self.browse_output_folder            
        )
        self.browse_output_folder_button.grid(row=0, column=2, padx=5)

        # ------------------ Actions ------------------
        action_frame = ttk.Frame(mainframe)
        action_frame.grid(row=5, column=0, columnspan=3, pady=15)

        self.refresh_database_button = ttk.Button(
            action_frame,
            text="Refresh Database",
            command=lambda: self.refresh_database(refresh_combobox=True)            
        )
        self.refresh_database_button.grid(row=0, column=0, padx=5)

        self.generate_report_button = ttk.Button(
            action_frame,
            text="Generate Report",
            command=self.report_gen_wrapper
        )
        self.generate_report_button.grid(row=0, column=1, padx=5)

        self.last_refresh_label = ttk.Label(action_frame)
        self.last_refresh_label.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        ts = settings.database_refresh_timestamp()
        display = ts.strftime('%Y-%m-%d %H:%M:%S') if ts else "Never"
        self.last_refresh_label.config(text=f"Last refresh: {display}")

        # Apply consistent padding
        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)



    # brings up folder selection dialog
    def browse_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder.set(folder_selected)

    # refreshes database and optionally the assembly combobox as well
    def refresh_database(self, refresh_combobox):
        # progress bar popup window
        popup = tk.Toplevel(self.root)
        popup.title("Database Refresh")
        popup.geometry("300x150")
        label = ttk.Label(popup, text="Refreshing database, please wait...", font=("Segoe UI", 12))
        label.pack(pady=10)
        pb = ttk.Progressbar(popup, orient='horizontal', mode='indeterminate', length=280)
        pb.pack(pady=10)
        pb.start()

        # database refresh is done on separate thread from all of the GUI updates to avoid freezing the GUI
        def do_work():
            try:
                location.update_location_table()
                item.inventory_to_database(item.entire_inventory_api_call())
                assembly.update_bom_table()

                display_values = []
                if refresh_combobox:
                    try:
                        self.assembly_list = assembly.get_assy_wasp_and_desc()
                        display_values = [
                            f"{a['waspnumber']} - {a['description']}"
                            for a in self.assembly_list
                        ]
                    except Exception as e:
                        self.root.after(0, lambda: messagebox.showerror("Failed getting assembly list", str(e)))

                self.root.after(0, lambda: on_success(display_values))
            except Exception as e:
                self.root.after(0, lambda err=e: on_error(err))

        # this updates the GUI after the database refresh is done successfully
        def on_success(display_values):
            pb.stop()
            pb.destroy()
            if refresh_combobox:
                self.assembly_combobox['values'] = display_values
                if self.assembly_list:
                    self.assembly_combobox.current(0)
            label.config(text="Database refreshed successfully!")
            ttk.Button(popup, text="OK", command=popup.destroy).pack(pady=5)
            settings.save_refresh_timestamp()
            self.last_refresh_label.config(text=f"Last refresh: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # this pops up an error message if the database refresh fails
        def on_error(e):
            pb.stop()
            pb.destroy()
            label.config(text=f"Failed to refresh database.")
            ttk.Button(popup, text="OK", command=popup.destroy, ).pack(pady=5)

        # starts the multi-threaded database refresh
        threading.Thread(target=do_work, daemon=True).start()

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

        # make sure desired_amount is cast to int
        desired_amount = self.desired_amount_entry.get().strip()
        if desired_amount == "":
            desired_amount = None
        else:
            desired_amount = int(desired_amount)

        try:
            if desired_amount is None:
                report_gen.create_report(assembly_num=waspnumber, 
                                        contract=self.contract_combobox.get(), 
                                        include_inspection=self.include_inspection.get(), 
                                        include_cost=self.include_cost.get(),
                                        include_on_order=self.include_on_order.get(),
                                        include_kitted=self.include_kitted.get(),
                                        output_directory=output_dir,
                                        list_of_contracts=self.list_of_contracts,
                                        include_assembled=self.include_assembled.get()
                                        )
            else:
                report_gen.create_report(assembly_num=waspnumber, 
                                        contract=self.contract_combobox.get(), 
                                        include_inspection=self.include_inspection.get(), 
                                        include_cost=self.include_cost.get(), 
                                        desired_amount=desired_amount,
                                        include_on_order=self.include_on_order.get(),
                                        include_kitted=self.include_kitted.get(),
                                        output_directory=output_dir,
                                        list_of_contracts=self.list_of_contracts,
                                        include_assembled=self.include_assembled.get()
                                        )
            messagebox.showinfo(title='Generate Report', message=f"Generated report successfully at {output_dir}")
        except Exception as e:
            messagebox.showerror('Failed to generate report', str(e))

if __name__ == "__main__":
    root=ttkbootstrap.Window(themename="flatly")

    style = ttkbootstrap.Style()
    style.configure('TButton', font=('Segoe UI', 12))
    style.configure('TLabel', font=('Segoe UI', 12))
    style.configure('TCheckbutton', font=('Segoe UI', 12))
    style.configure('TLabelframe.Label', font=('Segoe UI', 10))

    app = BuildableAssemblyWaspReportGenerator(root)
    root.lift()
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)
    root.mainloop()

    # ----------------------------- unit test -------------------------------------
    # location.update_location_table()
    # item.entire_inventory_api_call('item_list.csv')
    # item.inventory_to_database('item_list.csv')
    # assembly.update_bom_table()
    # report_gen.create_report('800002', 'RGI35', include_cost=True, include_inspection=True, include_on_order=True, desired_amount=50)