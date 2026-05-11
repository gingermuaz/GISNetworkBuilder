import tkinter as tk
from tkinter import ttk, colorchooser


class DynamicEditorPopup(tk.Toplevel):
    def __init__(self, parent, item, item_type, on_save_callback, on_delete_callback):
        super().__init__(parent)
        self.item = item
        self.item_type = item_type
        self.on_save_callback = on_save_callback
        self.on_delete_callback = on_delete_callback

        self.title(f"Edit {item_type} Data")
        self.geometry("320x500")
        self.attributes('-topmost', True)
        self.grab_set()

        self.entries = {}
        self.row_counter = 0

        self._build_ui()
        self._populate_existing_data()

    def _build_ui(self):
        self.canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="🎨 Pick Custom Color", command=self._pick_color, bg="#f0f8ff").pack(side="top",
                                                                                                      pady=5, fill="x")
        tk.Button(btn_frame, text="+ Add Field", command=self._add_blank_field, bg="lightyellow", width=20).pack(
            side="top", pady=5)
        tk.Button(btn_frame, text="Save Data", command=self._save_changes, bg="lightgreen", width=20).pack(side="top",
                                                                                                           pady=5)
        tk.Button(btn_frame, text="🗑️ Delete Shape", command=self._delete_item, bg="#ffcccc", width=20).pack(side="top",
                                                                                                             pady=5)

    def _pick_color(self):
        color_code = colorchooser.askcolor(title="Choose Shape Color")[1]
        if color_code:
            self.item['custom_color'] = color_code

    def _add_field_row(self, key, val):
        key_ent = tk.Entry(self.scrollable_frame, width=12, font=("Arial", 9, "bold"))
        key_ent.insert(0, key)
        key_ent.grid(row=self.row_counter, column=0, padx=5, pady=2, sticky="e")

        # --- NEW: DROPDOWN LOGIC ---
        if self.item_type == "Point" and key == "Asset":
            # Preset Council Assets
            val_ent = ttk.Combobox(self.scrollable_frame, width=15,
                                   values=["Streetlight", "Pothole", "Traffic Sign", "Bench", "Drain", "Other"])
            val_ent.set(str(val))
        elif self.item_type == "Line" and key == "Class":
            # Preset Road Classes
            val_ent = ttk.Combobox(self.scrollable_frame, width=15,
                                   values=["A-Road", "B-Road", "C-Road", "Unclassified", "Footpath"])
            val_ent.set(str(val))
        else:
            # Standard Text Box for everything else
            val_ent = tk.Entry(self.scrollable_frame, width=18)
            val_ent.insert(0, str(val))

        val_ent.grid(row=self.row_counter, column=1, padx=5, pady=2)

        self.entries[key_ent] = val_ent
        self.row_counter += 1

    def _populate_existing_data(self):
        for k, v in self.item['attributes'].items():
            self._add_field_row(k, v)

    def _add_blank_field(self):
        self._add_field_row("New_Field", "")

    def _save_changes(self):
        new_attrs = {}
        for k_ent, v_ent in self.entries.items():
            key_text = k_ent.get().strip()
            if key_text:
                new_attrs[key_text] = v_ent.get().strip()
        self.item['attributes'] = new_attrs
        self.on_save_callback()
        self.destroy()

    def _delete_item(self):
        self.on_delete_callback(self.item, self.item_type)
        self.destroy()