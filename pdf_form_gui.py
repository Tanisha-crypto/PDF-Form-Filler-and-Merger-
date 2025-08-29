# pdf_form_gui.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Any, List, Tuple
from PyPDF2 import PdfReader
from simple_pdf_filler import (
    fill_and_flatten,
    _is_widget,
    _get_field_from_annot,
    _is_text,
    _is_checkbox,
    _is_choice,
    _choice_is_multiselect,
    _choice_is_combo,
    _choice_options,
    _choice_display_to_export,
)

class PDFFormGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Form Filler (Dropdowns + Flatten)")
        self.input_path = None
        # widgets: list of dicts with metadata and tk variables for saving
        self.widgets: List[Dict[str, Any]] = []
        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="Open PDF...", command=self.open_pdf).pack(side="left")
        self.file_lbl = ttk.Label(top, text="No file loaded")
        self.file_lbl.pack(side="left", padx=8)

        self.canvas = tk.Canvas(frm)
        self.scroll = ttk.Scrollbar(frm, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.form_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        self.form_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        bottom = ttk.Frame(frm)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Save Filled PDF...", command=self.save_pdf).pack(side="right")

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self.input_path = path
        self.file_lbl.config(text=path.split("/")[-1])
        self._load_fields()

    def _load_fields(self):
        for child in self.form_frame.winfo_children():
            child.destroy()
        self.widgets.clear()

        reader = PdfReader(self.input_path)
        name_counts: Dict[str, int] = {}
        row = 0

        for page in reader.pages:
            annots = page.get("/Annots") or []
            for a in annots:
                annot = a.get_object()
                if not _is_widget(annot):
                    continue
                field = _get_field_from_annot(annot)
                name = field.get("/T")
                name_str = str(name) if name else "(unnamed)"

                # Text fields
                if _is_text(field):
                    var = tk.StringVar()
                    ttk.Label(self.form_frame, text=f"{name_str}").grid(row=row, column=0, sticky="w", padx=4, pady=2)
                    ttk.Entry(self.form_frame, textvariable=var, width=40).grid(row=row, column=1, sticky="we", padx=4, pady=2)
                    self.widgets.append({"kind": "text", "name": name_str, "var": var})
                    row += 1
                    continue

                # Checkboxes
                if _is_checkbox(field):
                    idx = name_counts.get(name_str, 0) + 1
                    name_counts[name_str] = idx
                    var = tk.BooleanVar()
                    ttk.Label(self.form_frame, text=f"{name_str}__{idx}").grid(row=row, column=0, sticky="w", padx=4, pady=2)
                    ttk.Checkbutton(self.form_frame, variable=var).grid(row=row, column=1, sticky="w", padx=4, pady=2)
                    self.widgets.append({"kind": "checkbox", "name": name_str, "idx": idx, "var": var})
                    row += 1
                    continue

                # Choice (dropdown/list)
                if _is_choice(field):
                    opts: List[Tuple[str, str]] = _choice_options(field)
                    # If no options, fall back to entry
                    if not opts:
                        var = tk.StringVar()
                        ttk.Label(self.form_frame, text=f"{name_str}").grid(row=row, column=0, sticky="w", padx=4, pady=2)
                        ttk.Entry(self.form_frame, textvariable=var, width=40).grid(row=row, column=1, sticky="we", padx=4, pady=2)
                        self.widgets.append({"kind": "text", "name": name_str, "var": var})
                        row += 1
                        continue

                    display_values = [disp for _, disp in opts]
                    display_to_export = {disp: ex for ex, disp in opts}

                    if _choice_is_multiselect(field):
                        ttk.Label(self.form_frame, text=f"{name_str} (multi)").grid(row=row, column=0, sticky="w", padx=4, pady=2)
                        lb = tk.Listbox(self.form_frame, selectmode="multiple", height=min(6, max(3, len(display_values))))
                        for dv in display_values:
                            lb.insert("end", dv)
                        lb.grid(row=row, column=1, sticky="we", padx=4, pady=2)
                        self.widgets.append({
                            "kind": "choice-multi",
                            "name": name_str,
                            "listbox": lb,
                            "display_to_export": display_to_export,
                        })
                        row += 1
                    else:
                        ttk.Label(self.form_frame, text=f"{name_str}").grid(row=row, column=0, sticky="w", padx=4, pady=2)
                        var = tk.StringVar()
                        combo = ttk.Combobox(self.form_frame, textvariable=var, values=display_values, state="readonly")
                        if display_values:
                            combo.current(0)
                        combo.grid(row=row, column=1, sticky="we", padx=4, pady=2)
                        self.widgets.append({
                            "kind": "choice",
                            "name": name_str,
                            "var": var,
                            "display_to_export": display_to_export,
                        })
                        row += 1
                    continue

        if not self.widgets:
            ttk.Label(self.form_frame, text="No form fields detected.").grid(row=0, column=0, padx=4, pady=4, sticky="w")

    def save_pdf(self):
        if not self.input_path:
            messagebox.showerror("Error", "Open a PDF first.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not out_path:
            return

        data: Dict[str, Any] = {}
        for w in self.widgets:
            if w["kind"] == "text":
                data[w["name"]] = w["var"].get()
            elif w["kind"] == "checkbox":
                key = f'{w["name"]}__{w["idx"]}'
                data[key] = bool(w["var"].get())
            elif w["kind"] == "choice":
                disp = w["var"].get()
                data[w["name"]] = _choice_display_to_export(None, disp) if False else w["display_to_export"].get(disp, disp)
            elif w["kind"] == "choice-multi":
                lb = w["listbox"]
                sels = [lb.get(i) for i in lb.curselection()]
                exports = [w["display_to_export"].get(d, d) for d in sels]
                data[w["name"]] = exports

        try:
            fill_and_flatten(self.input_path, out_path, data)
            messagebox.showinfo("Success", f"Saved: {out_path}\nOpen in Chrome/Edge to verify.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    PDFFormGUI(root)
    root.mainloop()
