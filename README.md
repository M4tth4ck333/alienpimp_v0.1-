# 👽 AlienPimp – Modularer Paketmanager & Mutationsmaschine

AlienPimp ist dein galaktischer Begleiter zum Verwalten, Modulieren und Konvertieren von Softwarepaketen  
(.deb, .rpm, src, Python-Setups & venvs) – per CLI, GUI oder Webinterface.  

---

## 🚀 Features

- Paketkonvertierung zwischen `.deb`, `.rpm`, `.src` und mehr  
- Automatisierte Python-Setup- und virtuelle Umgebungs-Erstellung  
- SQLite-basierte Paketdatenbank mit Hash-Verifikation  
- Modular erweiterbar für WiFi, OSINT & mehr  
- Bedienbar als CLI-Tool, Tkinter-GUI oder Webservice  
- Webhosting-ready für Apache mit mod_wsgi  
- Containerisierbar via Docker

---

## 🖥 Deployment auf Apache

AlienPimp läuft bequem als WSGI-App auf Apache mit `mod_wsgi`:

1. Mod_wsgi installieren und aktivieren  
2. AlienPimp als Python WSGI-App einrichten (`alienpimp.wsgi`)  
3. Apache-Site konfigurieren mit `WSGIScriptAlias`  
4. Paket-Repositories per Apache statisch hosten  
5. Alternativ REST-API via Flask/FastAPI erweitern  

---

## ⚡ CLI-Beispiele

```bash
alienpimp convert foo.deb --to rpm
alienpimp generate setup myproject/
alienpimp venv create myproject --hash

🧩 Verzeichnisstruktur

alienpimp/
├── alienpimp/          # Core-Module & Tools
├── cli/                # Command-Line Interface
├── gui/                # Tkinter GUI
├── web/                # Flask/FastAPI Web-API (optional)
├── docs/
├── Dockerfile
├── requirements.txt
└── README.md

🚀 Schnellstart

git clone https://github.com/dein-benutzername/alienpimp.git
cd alienpimp
pip install -r requirements.txt
python3 run.py

🧑‍🚀 Autor

Jan Schröder – „Der AlienPimp der Paketwelt“
⚖️ Lizenz

MIT – Mach, was du willst.

👽 Ready to pimp your packages?
Let the mutation begin!
