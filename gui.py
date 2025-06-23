import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from datetime import datetime
from base_package import BasePackage  # Deine neue Klasse!
import os

class PackageGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Alien Package Manager 2.0")
        self.packages = []  # Liste der BasePackage-Objekte
        self.filepath = None

        # Eingabefelder
        self.name_var = tk.StringVar()
        self.version_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.build_system_var = tk.StringVar()

        self.build_gui()

    def build_gui(self):
        row = 0
        tk.Label(self.master, text="Name").grid(row=row, column=0, sticky="e")
        tk.Entry(self.master, textvariable=self.name_var).grid(row=row, column=1)
        row += 1

        tk.Label(self.master, text="Version").grid(row=row, column=0, sticky="e")
        tk.Entry(self.master, textvariable=self.version_var).grid(row=row, column=1)
        row += 1

        tk.Label(self.master, text="Source").grid(row=row, column=0, sticky="e")
        tk.Entry(self.master, textvariable=self.source_var).grid(row=row, column=1)
        row += 1

        tk.Label(self.master, text="Build-System").grid(row=row, column=0, sticky="e")
        tk.Entry(self.master, textvariable=self.build_system_var).grid(row=row, column=1)
        row += 1

        tk.Button(self.master, text="Datei wählen", command=self.choose_file).grid(row=row, column=0, columnspan=2, pady=2)
        row += 1

        tk.Button(self.master, text="Metadatum hinzufügen", command=self.add_metadata).grid(row=row, column=0, columnspan=2, pady=2)
        row += 1

        tk.Button(self.master, text="Paket hinzufügen", command=self.add_package).grid(row=row, column=0, columnspan=2, pady=2)
        row += 1

        tk.Button(self.master, text="Pakete anzeigen", command=self.show_packages).grid(row=row, column=0, columnspan=2, pady=2)
        row += 1

        tk.Button(self.master, text="Pakete exportieren (JSON)", command=self.export_json).grid(row=row, column=0, columnspan=2, pady=2)
        row += 1

        tk.Button(self.master, text="Pakete exportieren (CSV)", command=self.export_csv).grid(row=row, column=0, columnspan=2, pady=2)

    def choose_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.filepath = Path(path)
            messagebox.showinfo("Datei gewählt", f"Datei: {os.path.basename(path)}")

    def add_metadata(self):
        key = simpledialog.askstring("Metadatum", "Metadaten-Schlüssel:")
        if not key:
            return
        value = simpledialog.askstring("Metadatum", f"Wert für '{key}':")
        if not hasattr(self, 'temp_metadata'):
            self.temp_metadata = {}
        self.temp_metadata[key] = value
        messagebox.showinfo("Metadatum", f"Metadatum '{key}: {value}' gespeichert.")

    def add_package(self):
        name = self.name_var.get().strip()
        version = self.version_var.get().strip()
        source = self.source_var.get().strip()
        build_system = self.build_system_var.get().strip() or None

        if not name or not version or not source:
            messagebox.showerror("Fehler", "Bitte Name, Version und Source angeben!")
            return

        pkg = BasePackage(
            name=name,
            version=version,
            source=source,
            filepath=self.filepath,
            build_system=build_system,
            timestamp=datetime.utcnow()
        )

        # Metadaten übernehmen, falls vorhanden
        if hasattr(self, 'temp_metadata'):
            for k, v in self.temp_metadata.items():
                pkg.set_metadata(k, v)
            self.temp_metadata = {}

        # Hashes berechnen, falls Datei gewählt
        if pkg.filepath and pkg.filepath.is_file():
            pkg.calculate_all_hashes()
            info = f"SHA256: {pkg.sha256}\nSHA1: {pkg.sha1}\nMD5: {pkg.md5}"
        else:
            info = "Keine Datei gewählt oder Datei existiert nicht."

        self.packages.append(pkg)
        self.filepath = None  # Reset für nächstes Paket

        messagebox.showinfo("Erfolg", f"Paket '{name}' gespeichert.\n{info}")

    def show_packages(self):
        if not self.packages:
            messagebox.showinfo("Pakete", "Keine Pakete vorhanden.")
            return
        msg = ""
        for p in self.packages:
            msg += f"{p.name} {p.version} {p.source} {p.build_system or '-'} {p.timestamp.strftime('%Y-%m-%d')}\n"
        messagebox.showinfo("Pakete", msg)

    def export_json(self):
        if not self.packages:
            messagebox.showerror("Fehler", "Keine Pakete zum Exportieren!")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Dateien", "*.json")])
        if path:
            BasePackage.export_to_json(self.packages, Path(path))
            messagebox.showinfo("Export", f"Pakete als JSON gespeichert: {path}")

    def export_csv(self):
        if not self.packages:
            messagebox.showerror("Fehler", "Keine Pakete zum Exportieren!")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Dateien", "*.csv")])
        if path:
            BasePackage.export_to_csv(self.packages, Path(path))
            messagebox.showinfo("Export", f"Pakete als CSV gespeichert: {path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PackageGUI(root)
    root.mainloop()
