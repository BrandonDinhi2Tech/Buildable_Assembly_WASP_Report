import item
import assembly
import location
import report_gen
import settings
import presets
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import socket
from pathlib import Path
import sys
import subprocess
import ttkbootstrap
import threading
import datetime

class BuildableAssemblyWaspReportGenerator:
    list_of_contracts = ['RGI35', 'QIN05', 'QIN11', 'General Stock', 'All']
    list_of_units = ['i2AX(BLK2) 616-12', 'i2DAS 910-02']

    home_dir = Path.home()
    target_folder = home_dir / "Documents" / "WASP Assembly Reports"
    target_folder.mkdir(parents=True, exist_ok=True)

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

        # ------------------ Unit Selection Frame --------------
        unit_selection_frame = ttk.LabelFrame(mainframe, text="Unit Selection", padding = 10)
        unit_selection_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        unit_selection_frame.columnconfigure(1, weight=1)

        ttk.Label(unit_selection_frame, text="Unit Type:").grid(row=0, column=0, sticky="e")
        self.unit_combobox = ttk.Combobox(unit_selection_frame, width=50, state="readonly")
        self.unit_combobox['values'] = self.list_of_units
        if self.list_of_units:
            self.unit_combobox.current(0)
        self.unit_combobox.grid(row=0, column=1, sticky="ew")

        self.unit_combobox.bind("<<ComboboxSelected>>", self.on_unit_type_changed)


        # ------------------ Selection Frame ------------------
        selection_frame = ttk.LabelFrame(mainframe, text="Selection", padding=10)
        selection_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
        selection_frame.columnconfigure(1, weight=1)

        ttk.Label(selection_frame, text="Assembly:").grid(row=0, column=0, sticky="e")
        self.assembly_combobox = ttk.Combobox(selection_frame, width=50, state="readonly")

        try:
            unit_type = self.get_unit_type()
            print(f"unit_type value: {unit_type}, type: {type(unit_type)}")
            self.assembly_list = assembly.get_assy_wasp_and_desc(unit_type)
            display_values = [
                f"{a['waspnumber']} - {a['description']}"
                for a in self.assembly_list
            ]
        except Exception as e:
            messagebox.showerror("Failed getting assembly list", str(e))
            print("Failed getting assembly list", str(e))
            display_values = []
            self.assembly_list = []

        self.assembly_combobox['values'] = display_values
        if self.assembly_list:
            self.assembly_combobox.current(0)
        self.assembly_combobox.grid(row=0, column=1, sticky="ew")

        ttk.Label(selection_frame, text="Stock Area:").grid(row=1, column=0, sticky="e")
        self.contract_combobox = ttk.Combobox(selection_frame, width=50, state="readonly")
        self.contract_combobox['values'] = self.list_of_contracts
        if self.list_of_contracts:
            self.contract_combobox.current(0)
        self.contract_combobox.grid(row=1, column=1, sticky="ew")

        # ------------------ Options Frame ------------------
        options_frame = ttk.LabelFrame(mainframe, text="Availability Options", padding=10)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)

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
        settings_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=5)
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="Desired Units:").grid(row=0, column=0, sticky="e")
        self.desired_amount_entry = ttk.Entry(settings_frame, width=15, justify="right")
        self.desired_amount_entry.grid(row=0, column=1, sticky="w")

        self.include_cost = tk.BooleanVar()
        ttk.Checkbutton(settings_frame, text="Include Cost", variable=self.include_cost).grid(row=1, column=1, sticky="w")

        # ------------------ Output Frame ------------------
        output_frame = ttk.LabelFrame(mainframe, text="Output", padding=10)
        output_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky="e")
        self.output_folder = tk.StringVar(value=self.target_folder)
        self.output_folder_entry = ttk.Entry(output_frame, textvariable=self.output_folder)
        self.output_folder_entry.grid(row=0, column=1, sticky="ew")

        self.browse_output_folder_button = ttk.Button(
            output_frame,
            text="Browse",
            command=self.browse_output_folder            
        )
        self.browse_output_folder_button.grid(row=0, column=2, padx=5)

        # ------------------ Presets ------------------
        presets_frame = ttk.LabelFrame(mainframe, text="Presets", padding=10)
        presets_frame.grid(row = 6, column=0, columnspan=3, sticky="ew", pady=5)
        presets_frame.columnconfigure(1, weight=1)

        self.preset_combobox = ttk.Combobox(presets_frame, width=30, state="readonly")
        self.preset_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ttk.Button(presets_frame, text="Load", command=self.load_preset).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(presets_frame, text="Save", command=self.save_preset).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(presets_frame, text="Delete", command=self.delete_preset).grid(row=0, column=3, sticky="ew", padx=2)

        # stretch each column to fill space evenly
        presets_frame.columnconfigure(0, weight=3)
        presets_frame.columnconfigure(1, weight=1)
        presets_frame.columnconfigure(2, weight=1)
        presets_frame.columnconfigure(3, weight=1)

        self.refresh_preset_list()

        # ------------------ Actions ------------------
        action_frame = ttk.Frame(mainframe)
        action_frame.grid(row=7, column=0, columnspan=3, pady=15)

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

    # ----------------------------------------------------------------------------------------
    # ----------------------------------------------------------------------------------------
    # ------------------------------ END OF UI -----------------------------------------------
    # ----------------------------------------------------------------------------------------
    # ----------------------------------------------------------------------------------------

    # brings up folder selection dialog
    def browse_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder.set(folder_selected)
        
    # gets the type of unit that the user wants to filter for in the assembly list
    def get_unit_type(self):
        unit_type = self.unit_combobox.get()
        unit_search_terms = ["%" + term + "%" for term in unit_type.split()]
        return unit_search_terms

    # updates the assembly combobox whenever the unit combobox is selected
    def on_unit_type_changed(self, event=None):
        try:
            unit_type = self.get_unit_type()
            self.assembly_list = assembly.get_assy_wasp_and_desc(unit_type=unit_type)
            display_values = [
                f"{a['waspnumber']} - {a['description']}"
                for a in self.assembly_list
            ]
            self.assembly_combobox['values'] = display_values
            if self.assembly_list:
                self.assembly_combobox.current(0)
            else:
                self.assembly_combobox.set('')
        except Exception as e:
            messagebox.showerror("Failed to update assembly list", str(e))

    def _can_connect_to_server(self, host='i2techinventory', port=8703, timeout=5):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    # refreshes database and optionally the assembly combobox as well
    def refresh_database(self, refresh_combobox):

        # _refresh_in_progress is False if it doesn't exist
        if getattr(self, '_refresh_in_progress', False):
            return

        self._refresh_in_progress = True
        self._refresh_id = getattr(self, '_refresh_id', 0) + 1
        refresh_id = self._refresh_id

        # disable refresh database button when refresh is in progress
        if hasattr(self, 'refresh_database_button'):
            self.refresh_database_button.config(state='disabled')

        # progress bar popup window
        popup = tk.Toplevel(self.root)
        popup.title("Database Refresh")
        popup.geometry("400x150")
        popup.transient(self.root)
        popup.grab_set()
        popup.resizable(False, False)
        label = ttk.Label(popup, text="Refreshing database, please wait...", font=("Segoe UI", 12))
        label.pack(pady=10)
        pb = ttk.Progressbar(popup, orient='horizontal', mode='indeterminate', length=280)
        pb.pack(pady=10)
        pb.start()

        def finish_refresh():
            if refresh_id != self._refresh_id:
                return
            self._refresh_in_progress = False
            if hasattr(self, 'refresh_database_button'):
                self.refresh_database_button.config(state='normal')

        # database refresh is done on separate thread from all of the GUI updates to avoid freezing the GUI
        def do_work():
            try:
                location.update_location_table()
                item.inventory_to_database(item.entire_inventory_api_call())
                assembly.update_bom_table()

                display_values = []
                if refresh_combobox:
                    try:
                        unit_type = self.get_unit_type()
                        print(f"unit_type value: {unit_type}, type: {type(unit_type)}")
                        self.assembly_list = assembly.get_assy_wasp_and_desc(unit_type)
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
            if refresh_id != self._refresh_id:
                return
            pb.stop()
            popup.grab_release()
            pb.destroy()
            if refresh_combobox:
                self.assembly_combobox['values'] = display_values
                if self.assembly_list:
                    self.assembly_combobox.current(0)
            label.config(text="Database refreshed successfully!")
            ttk.Button(popup, text="OK", command=popup.destroy).pack(pady=5)
            # update timestamp for last database refresh
            settings.save_refresh_timestamp()
            self.last_refresh_label.config(text=f"Last refresh: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            finish_refresh()

        # this pops up an error message if the database refresh fails
        def on_error(e):
            if refresh_id != self._refresh_id:
                return
            error_message = str(e) if e else "Unknown error"
            pb.stop()
            popup.grab_release()
            pb.destroy()
            label.config(text="Failed to refresh database.")
            ttk.Button(popup, text="OK", command=popup.destroy).pack(pady=5)
            messagebox.showerror("Database refresh failed", error_message)
            finish_refresh()

        def on_timeout():
            if refresh_id != self._refresh_id:
                return
            self._refresh_id += 1
            pb.stop()
            popup.grab_release()
            pb.destroy()
            label.config(text="Database refresh timed out.")
            ttk.Button(popup, text="OK", command=popup.destroy).pack(pady=5)
            messagebox.showerror("Database refresh timed out", "The refresh took too long and was aborted. Please retry when the network is stable.")
            self._refresh_in_progress = False
            if hasattr(self, 'refresh_database_button'):
                self.refresh_database_button.config(state='normal')

        try:
            can_connect = self._can_connect_to_server()
        except Exception as e:
            print("Server connectivity check failed:", e)
            can_connect = False

        if not can_connect:
            pb.stop()
            popup.grab_release()
            pb.destroy()
            label.config(text="Cannot reach WASP server.\nCheck if connected to i2Tech Inventory WiFi and retry.", justify='center', anchor='center')
            ttk.Button(popup, text="OK", command=popup.destroy).pack(pady=5)
            finish_refresh()
            return

        self.root.after(60000, on_timeout) # max time allowed for database refresh in milliseconds

        # starts the multi-threaded database refresh
        threading.Thread(target=do_work, daemon=True).start()

    # return a dictionary containing the current options selected by the user in the UI
    def _current_options(self):
        # Snapshot of all current widget values
        return {
            "unit_type":          self.unit_combobox.get(),
            "assembly_id":        self.assembly_combobox.get(),
            "contract":           self.contract_combobox.get(),
            "include_inspection": self.include_inspection.get(),
            "include_on_order":   self.include_on_order.get(),
            "include_kitted":     self.include_kitted.get(),
            "include_assembled":  self.include_assembled.get(),
            "include_cost":       self.include_cost.get(),
            "desired_amount":     int(self.desired_amount_entry.get()) if self.desired_amount_entry.get().strip() else None,
        }

    def get_active_preset_name(self):
        # Returns the preset name if the current options match it, otherwise None
        idx = self.preset_combobox.current()
        if idx == -1:
            return None
        
        p = self.preset_list[idx]
        current = self._current_options()

        if (
            p['unit_type']          == current['unit_type']          and
            p['assembly_id']        == current['assembly_id']        and
            p['contract']           == current['contract']           and
            p['include_inspection'] == current['include_inspection'] and
            p['include_on_order']   == current['include_on_order']   and
            p['include_kitted']     == current['include_kitted']     and
            p['include_assembled']  == current['include_assembled']  and
            p['include_cost']       == current['include_cost']       and
            p['desired_amount']     == current['desired_amount']
        ):
            return p['name']
        
        return None

    # handles the report generation within the UI
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
            output_dir = self.target_folder

        # make sure desired_amount is cast to int
        desired_amount = self.desired_amount_entry.get().strip()
        if desired_amount == "":
            desired_amount = None
        else:
            desired_amount = int(desired_amount)

        preset_name = self.get_active_preset_name() # get preset name if the preset is actually selected

        file_path = '' # full file path for the output used to open up the report automatically on generation
        try:
            if desired_amount is None:
                file_path = report_gen.create_report(assembly_num=waspnumber, 
                                        contract=self.contract_combobox.get(), 
                                        include_inspection=self.include_inspection.get(), 
                                        include_cost=self.include_cost.get(),
                                        include_on_order=self.include_on_order.get(),
                                        include_kitted=self.include_kitted.get(),
                                        output_directory=output_dir,
                                        list_of_contracts=self.list_of_contracts,
                                        include_assembled=self.include_assembled.get(),
                                        preset_name = preset_name
                                        )
            else:
                file_path = report_gen.create_report(assembly_num=waspnumber, 
                                        contract=self.contract_combobox.get(), 
                                        include_inspection=self.include_inspection.get(), 
                                        include_cost=self.include_cost.get(), 
                                        desired_amount=desired_amount,
                                        include_on_order=self.include_on_order.get(),
                                        include_kitted=self.include_kitted.get(),
                                        output_directory=output_dir,
                                        list_of_contracts=self.list_of_contracts,
                                        include_assembled=self.include_assembled.get(),
                                        preset_name = preset_name
                                        )

            # open up report in default spreadsheet viewer
            if os.path.exists(file_path):
                if sys.platform == "win32": # Windows
                    os.startfile(file_path)
                elif sys.platform == "darwin":  # macOS
                    subprocess.Popen(["open", file_path])
                else:  # Linux
                    subprocess.Popen(["xdg-open", file_path])
            else:
                messagebox.showerror("Error: file not found")

            messagebox.showinfo(title='Generate Report', message=f"Generated report successfully at {output_dir}")
        except Exception as e:
            messagebox.showerror('Failed to generate report', str(e))

    # wrapper for the presets.load_presets() function
    def refresh_preset_list(self):
        self.preset_list = presets.load_presets()
        self.preset_combobox['values'] = [p['name'] for p in self.preset_list]
        if self.preset_list:
            self.preset_combobox.current(0)
        else:
            self.preset_combobox.set('')

    # wrapper for the presets.save_preset() function
    def save_preset(self):
        name = tk.simpledialog.askstring("Save Preset", "Enter a name for this preset:")
        if not name:
            return
        try:
            presets.save_preset(name, self._current_options())
            self.refresh_preset_list()
            self.preset_combobox.set(name)
            messagebox.showinfo("Preset Saved", f"Preset '{name}' saved.")
        except Exception as e:
            messagebox.showerror("Error saving preset", str(e))

    # sets the options selected in the UI to the ones specified in the preset
    def load_preset(self):
        idx = self.preset_combobox.current()
        if idx == -1:
            messagebox.showwarning("No preset selected", "Please select a preset to load.")
            return
        p = self.preset_list[idx]
        self.unit_combobox.set(p['unit_type'])
        self.on_unit_type_changed() # update assembly combobox to match unit type
        self.assembly_combobox.set(p['assembly_id'])
        self.contract_combobox.set(p['contract'])
        self.include_inspection.set(p['include_inspection'])
        self.include_on_order.set(p['include_on_order'])
        self.include_kitted.set(p['include_kitted'])
        self.include_assembled.set(p['include_assembled'])
        self.include_cost.set(p['include_cost'])
        self.desired_amount_entry.delete(0, tk.END)
        if p['desired_amount'] is not None:
            self.desired_amount_entry.insert(0, str(p['desired_amount']))

    # wrapper for presets.delete_preset() function
    def delete_preset(self):
        idx = self.preset_combobox.current()
        if idx == -1:
            messagebox.showwarning("No preset selected", "Please select a preset to delete.")
            return
        name = self.preset_list[idx]['name']
        confirm = messagebox.askyesno("Delete Preset", f"Delete preset '{name}'?")
        if confirm:
            presets.delete_preset(name)
            self.refresh_preset_list()

if __name__ == "__main__":
    root=ttkbootstrap.Window(themename="flatly")

    presets.create_default_presets() # makes the default presets that every user will have on startup

    # setting font sizes across the UI
    style = ttkbootstrap.Style()
    style.configure('TButton', font=('Segoe UI', 12))
    style.configure('TLabel', font=('Segoe UI', 12))
    style.configure('TCheckbutton', font=('Segoe UI', 12))
    style.configure('TLabelframe.Label', font=('Segoe UI', 10))

    app = BuildableAssemblyWaspReportGenerator(root)

    # bring app to the front, then allow it to go to the background if the user wishes
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