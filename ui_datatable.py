import tkinter as tk
from tkinter import ttk


class AttributeTableWindow(tk.Toplevel):
    """A floating window that displays all network data in a spreadsheet format."""

    def __init__(self, parent, nodes, edges, polygons, pan_callback):
        super().__init__(parent)
        self.title("Attribute Table")
        self.geometry("800x300")
        self.attributes('-topmost', True)  # Keep it above the main window

        self.nodes = nodes
        self.edges = edges
        self.polygons = polygons
        self.pan_callback = pan_callback  # The function to move the map

        # Create tabs for Points, Lines, and Polygons
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_points = ttk.Frame(self.notebook)
        self.tab_lines = ttk.Frame(self.notebook)
        self.tab_polygons = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_points, text=f"Points ({len(nodes)})")
        self.notebook.add(self.tab_lines, text=f"Lines ({len(edges)})")
        self.notebook.add(self.tab_polygons, text=f"Polygons ({len(polygons)})")

        # Build the spreadsheets
        self._build_tree(self.tab_points, self.nodes, "NodeID")
        self._build_tree(self.tab_lines, self.edges, "EdgeID")
        self._build_tree(self.tab_polygons, self.polygons, "PolygonID")

    def _build_tree(self, parent_frame, data_list, id_col_name):
        if not data_list:
            tk.Label(parent_frame, text="No data available.", font=("Arial", 10, "italic")).pack(pady=20)
            return

        # 1. Dynamically figure out what columns we need based on the data
        columns = [id_col_name]
        for item in data_list:
            for key in item['attributes'].keys():
                if key not in columns:
                    columns.append(key)

        # 2. Create the Treeview (Spreadsheet)
        tree = ttk.Treeview(parent_frame, columns=columns, show="headings")

        # Add Scrollbars
        vsb = ttk.Scrollbar(parent_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(parent_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout for the table and scrollbars
        tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')

        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(0, weight=1)

        # 3. Format the Headers
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")

        # 4. Insert the Data Rows
        for index, item in enumerate(data_list):
            row_data = [item.get(id_col_name, index + 1)]
            for col in columns[1:]:
                row_data.append(item['attributes'].get(col, ""))

            # Use the index as the 'iid' so we know which item was clicked later
            tree.insert("", tk.END, iid=str(index), values=row_data)

        # 5. Bind Double-Click to pan the map
        tree.bind("<Double-1>", lambda event: self._on_row_click(event, tree, data_list))

    def _on_row_click(self, event, tree, data_list):
        selected_item = tree.selection()
        if selected_item:
            index = int(selected_item[0])  # Get the index we stored
            geom = data_list[index]['geometry']
            self.pan_callback(geom)  # Tell the main app to move the camera!