# 👽 AlienManager – Portable CLI & GUI Package Tracker

**AlienManager** ist ein portables, containerisierbares Tool zur Verwaltung und Hash-Überprüfung von Softwarepaketen. Es bietet:

- 📦 SQL-basierte Datenhaltung (SQLite)
- 🖥️ Interaktive TUI (cmd2) **und** GUI (Tkinter)
- 🔢 SHA256-Verifikation
- 🐚 Bash-kompatible CLI-Einzeiler
- 🐳 Docker-Unterstützung

---

## 🚀 Features

- ✅ `add`, `list`, `remove` – direkt über Bash oder GUI
- ✅ SHA256-Hashing für lokale Dateien
- ✅ Automatische Zeitstempel
- ✅ SQLite statt JSON/CSV
- ✅ Optionales GUI-Frontend mit Dateiauswahl
- ✅ Colorized CLI mit `colorama`
- ✅ Vollständig portabel, keine externen Server nötig

---

## 🔧 Installation

### 1. Klonen

```bash
git clone https://github.com/dein-benutzername/alienmanager.git
cd alienmanager

2. Abhängigkeiten installieren

pip install -r requirements.txt

    Oder: per venv

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

📦 CLI-Nutzung

# Paket hinzufügen (mit SHA256)
python3 cli.py add <name> <version> <quelle> /pfad/zur/datei.tar.gz

# Liste anzeigen
python3 cli.py list

# Paket löschen
python3 cli.py remove <name>

    Tipp: .bashrc erweitern

alias alien='python3 /voller/pfad/zu/cli.py'

Dann:

alien add testpkg 1.0 github /tmp/test.tar.gz
alien list

🖼️ GUI starten

python3 gui.py

🐳 Docker (optional)

docker build -t aliencli .
docker run -it --rm aliencli

🗃️ Datenhaltung

Die Daten werden standardmäßig in db.sqlite3 gespeichert.
Spalte	Beschreibung
name	Paketname
version	Versionsnummer
source	Quelle (z. B. github)
timestamp	ISO-Zeitstempel
sha256	SHA256-Hash der Datei
📁 Struktur

alienmanager/
├── cli.py         # Bash & cmd2 Entry Point
├── gui.py         # Tkinter GUI
├── orm.py         # SQLite ORM
├── db.sqlite3     # SQLite-Datenbank
├── Dockerfile     # Container Support
├── requirements.txt
└── README.md

💡 Ideen für Erweiterungen

    🔍 Paketdetailsuche (search)

    🌍 Remote-Sync (optional)

    📊 Export als Markdown oder HTML

    🧩 Plugin-System

    📦 Paket als .deb oder .AppImage

🤝 Mitwirken

Pull Requests & Vorschläge sind willkommen!
⚖️ Lizenz

MIT – Freie Nutzung für jedes Projekt.
👨‍💻 Autor

Jan Schröder

    Entwicklung & Idee: CLI-Paketmanagement mit Fokus auf Transparenz und Reproduzierbarkeit.
