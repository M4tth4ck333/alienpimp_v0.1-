# tui.py
import cmd2
from pathlib import Path
from core import AlienManager, BasePackage

class AlienShell(cmd2.Cmd):
    intro = "Willkommen im AlienManager Shell! Tippe 'help' für Befehle.\n"
    prompt = "(alien) "

    def __init__(self):
        super().__init__()
        self.manager = AlienManager()

    def do_list(self, arg):
        "Listet alle Pakete"
        packages = self.manager.list_packages()
        if not packages:
            self.poutput("Keine Pakete vorhanden.")
            return
        for name in packages:
            pkg = self.manager.get_package(name)
            self.poutput(f"{pkg.name} - {pkg.version} - {pkg.source} - {pkg.timestamp} - SHA256: {pkg.sha256}")

    def do_add(self, arg):
        "Fügt ein neues Paket hinzu: add <name> <version> <source> [<filepath>]"
        parts = arg.split()
        if len(parts) < 3:
            self.perror("Benutzung: add <name> <version> <source> [<filepath>]")
            return
        name, version, source = parts[:3]
        filepath = Path(parts[3]) if len(parts) >= 4 else None
        pkg = BasePackage(name, version, source, filepath)
        self.manager.add_package(pkg)
        self.poutput(f"Paket {name} hinzugefügt.")

    def do_build(self, arg):
        "Baue alle Pakete"
        self.manager.build_all()
        self.poutput("Builds abgeschlossen.")

    def do_exit(self, arg):
        "Beendet die Shell"
        return True

    def do_EOF(self, arg):
        return True

if __name__ == "__main__":
    shell = AlienShell()
    shell.cmdloop()
