# gui.py
import tkinter as tk
from tkinter import filedialog, messagebox
from orm import PackageORM
import hashlib
from pathlib import Path

class PackageGUI:
    def __init__(self, master):
        self.db = PackageORM()
        self.master = master
        self.master.title("Alien Package Manager")

        # Eingabefelder
        self.name_var = tk.StringVar()
        self.version_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.filepath = None

        self.build_gui()

    def build_gui(self):
        tk.Label(self.master, text="Name").grid(row=0, column=0)
        tk.Entry(self.master, textvariable=self.name_var).grid(row=0, column=1)

        tk.Label(self.master, text="Version").grid(row=1, column=0)
        tk.Entry(self.master, textvariable=self.version_var).grid(row=1, column=1)

        tk.Label(self.master, text="Source").grid(row=2, column=0)
        tk.Entry(self.master, textvariable=self.source_var).grid(row=2, column=1)

        tk.Button(self.master, text="Datei wählen", command=self.choose_file).grid(row=3, column=0, columnspan=2)
        tk.Button(self.master, text="Paket hinzufügen", command=self.add_package).grid(row=4, column=0, columnspan=2)
        tk.Button(self.master, text="Pakete anzeigen", command=self.show_packages).grid(row=5, column=0, columnspan=2)

    def choose_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.filepath = Path(path)

    def add_package(self):
        name = self.name_var.get()
        version = self.version_var.get()
        source = self.source_var.get()
        sha = ""
        if self.filepath and self.filepath.is_file():
            sha = self.hash_file(self.filepath)
        self.db.add_package(name, version, source, sha)
        messagebox.showinfo("Erfolg", f"Paket '{name}' wurde gespeichert.")

    def show_packages(self):
        rows = self.db.list_packages()
        msg = "\n".join(f"{n} {v} {s} {ts[:10]}" for n, v, s, ts, sha in rows)
        messagebox.showinfo("Pakete", msg or "Keine Pakete vorhanden.")

    def hash_file(self, path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

if __name__ == "__main__":
    root = tk.Tk()
    app = PackageGUI(root)
    root.mainloop()
