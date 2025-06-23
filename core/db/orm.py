"""
Vollständige Integration: AlienPimp ORM + Apache + Tkinter + Jan Schroeder
Architektur für lokale KI-gestützte Paket-Analyse mit Web-Interface
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import subprocess
import webbrowser
from flask import Flask, render_template, jsonify, request
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkinter
import os
import sys

# Import your enhanced ORM
from enhanced_alienpimp_orm import ExtendedAlienPimpORM


class JanSchrodoerIntegration:
    """Integration mit Jan Schroeder lokaler KI"""
    
    def __init__(self, jan_api_url="http://localhost:1337"):
        self.jan_api_url = jan_api_url
        self.is_connected = False
        self._test_connection()
    
    def _test_connection(self):
        """Teste Verbindung zu Jan Schroeder"""
        try:
            response = requests.get(f"{self.jan_api_url}/health", timeout=5)
            self.is_connected = response.status_code == 200
        except:
            self.is_connected = False
            print("Jan Schroeder nicht verfügbar - KI-Features deaktiviert")
    
    def analyze_package_with_ai(self, package_name: str, package_metadata: dict) -> str:
        """Analysiere Paket mit Jan Schroeder KI"""
        if not self.is_connected:
            return "KI-Analyse nicht verfügbar"
        
        try:
            prompt = f"""
            Analysiere dieses Software-Paket:
            Name: {package_name}
            Metadaten: {json.dumps(package_metadata, indent=2)}
            
            Bitte bewerte:
            1. Sicherheitsrisiken
            2. Wartungsqualität  
            3. Community-Engagement
            4. Empfehlungen
            
            Antworte auf Deutsch und strukturiert.
            """
            
            response = requests.post(
                f"{self.jan_api_url}/v1/chat/completions",
                json={
                    "model": "llama3-8b-instruct",  # oder verfügbares Modell
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return "KI-Analyse fehlgeschlagen"
                
        except Exception as e:
            return f"Fehler bei KI-Analyse: {str(e)}"


class ApacheWebInterface:
    """Flask Web-Interface für Apache Integration"""
    
    def __init__(self, orm: ExtendedAlienPimpORM, jan_integration: JanSchrodoerIntegration):
        self.app = Flask(__name__)
        self.orm = orm
        self.jan = jan_integration
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask Routes"""
        
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @self.app.route('/api/packages')
        def get_packages():
            """API: Alle Pakete abrufen"""
            try:
                with sqlite3.connect(self.orm.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id, name, version, source, description, 
                               quality_score, popularity_score, security_score
                        FROM packages
                        ORDER BY popularity_score DESC
                        LIMIT 100
                    ''')
                    
                    packages = []
                    for row in cursor.fetchall():
                        packages.append({
                            'id': row[0],
                            'name': row[1],
                            'version': row[2],
                            'source': row[3],
                            'description': row[4],
                            'quality_score': row[5],
                            'popularity_score': row[6],
                            'security_score': row[7]
                        })
                    
                    return jsonify(packages)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analyze/<package_name>')
        def analyze_package_api(package_name):
            """API: Paket mit KI analysieren"""
            try:
                package = self.orm.get_package_by_name(package_name)
                if not package:
                    return jsonify({'error': 'Paket nicht gefunden'}), 404
                
                # KI-Analyse
                ai_analysis = self.jan.analyze_package_with_ai(package_name, package)
                
                # Netzwerk-Analyse
                ecosystem_analysis = self.orm.analyze_package_ecosystem(package['id'])
                
                return jsonify({
                    'package': package,
                    'ai_analysis': ai_analysis,
                    'ecosystem_analysis': ecosystem_analysis
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/network/visualization')
        def network_visualization():
            """API: Netzwerk-Visualisierungsdaten"""
            try:
                viz_data = self.orm.export_network_visualization_data(output_format='dict')
                return jsonify(viz_data)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/statistics')
        def get_statistics():
            """API: Datenbank-Statistiken"""
            try:
                stats = self.orm.get_statistics()
                return jsonify(stats)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def run(self, host='0.0.0.0', port=8080, debug=True):
        """Starte Flask Server"""
        self.app.run(host=host, port=port, debug=debug, threaded=True)


class TkinterGUI:
    """Tkinter Desktop-Interface"""
    
    def __init__(self, orm: ExtendedAlienPimpORM, jan_integration: JanSchrodoerIntegration):
        self.orm = orm
        self.jan = jan_integration
        self.root = tk.Tk()
        self.web_server_thread = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup Tkinter UI"""
        self.root.title("AlienPimp ORM - Package Analysis Suite")
        self.root.geometry("1200x800")
        
        # Hauptmenu
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="Paket importieren", command=self.import_package)
        file_menu.add_command(label="Datenbank exportieren", command=self.export_database)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit)
        
        # Server Menu
        server_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Server", menu=server_menu)
        server_menu.add_command(label="Web-Interface starten", command=self.start_web_server)
        server_menu.add_command(label="Web-Interface öffnen", command=self.open_web_interface)
        server_menu.add_separator()
        server_menu.add_command(label="Jan Schroeder Status", command=self.check_jan_status)
        
        # Hauptframe mit Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Paket-Management
        self.package_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.package_frame, text="Paket-Management")
        self._setup_package_tab()
        
        # Tab 2: Netzwerk-Analyse
        self.network_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.network_frame, text="Netzwerk-Analyse")
        self._setup_network_tab()
        
        # Tab 3: KI-Analyse
        self.ai_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ai_frame, text="KI-Analyse")
        self._setup_ai_tab()
        
        # Tab 4: Statistiken
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="Statistiken")
        self._setup_stats_tab()
        
        # Status Bar
        self.status_bar = ttk.Label(self.root, text="Bereit", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _setup_package_tab(self):
        """Setup Package Management Tab"""
        # Eingabebereich
        input_frame = ttk.LabelFrame(self.package_frame, text="Neues Paket hinzufügen")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Name
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.name_entry = ttk.Entry(input_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # Version
        ttk.Label(input_frame, text="Version:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.version_entry = ttk.Entry(input_frame, width=15)
        self.version_entry.grid(row=0, column=3, padx=5, pady=2)
        
        # GitHub URL
        ttk.Label(input_frame, text="GitHub URL:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.github_entry = ttk.Entry(input_frame, width=50)
        self.github_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=1, column=3, padx=5, pady=2)
        
        ttk.Button(button_frame, text="Hinzufügen", command=self.add_package).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Löschen", command=self.clear_form).pack(side=tk.LEFT, padx=2)
        
        # Paket-Liste
        list_frame = ttk.LabelFrame(self.package_frame, text="Installierte Pakete")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview für Pakete
        columns = ('Name', 'Version', 'Quelle', 'Qualität', 'Popularität', 'Sicherheit')
        self.package_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        for col in columns:
            self.package_tree.heading(col, text=col)
            self.package_tree.column(col, width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.package_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.package_tree.xview)
        self.package_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.package_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Double-click Event
        self.package_tree.bind('<Double-1>', self.on_package_select)
        
        # Pakete laden
        self.refresh_package_list()
    
    def _setup_network_tab(self):
        """Setup Network Analysis Tab"""
        # Matplotlib Canvas für Netzwerk-Visualisierung
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvasTkinter(self.fig, self.network_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Control Frame
        control_frame = ttk.Frame(self.network_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Netzwerk visualisieren", 
                  command=self.visualize_network).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Exportieren", 
                  command=self.export_network).pack(side=tk.LEFT, padx=5)
    
    def _setup_ai_tab(self):
        """Setup AI Analysis Tab"""
        # Package Selection
        select_frame = ttk.LabelFrame(self.ai_frame, text="Paket für KI-Analyse auswählen")
        select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.ai_package_var = tk.StringVar()
        self.ai_package_combo = ttk.Combobox(select_frame, textvariable=self.ai_package_var, 
                                           state="readonly", width=40)
        self.ai_package_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(select_frame, text="Analysieren", 
                  command=self.analyze_with_ai).pack(side=tk.LEFT, padx=5)
        
        # Results
        results_frame = ttk.LabelFrame(self.ai_frame, text="KI-Analyse Ergebnisse")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.ai_results_text = tk.Text(results_frame, wrap=tk.WORD)
        ai_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, 
                                   command=self.ai_results_text.yview)
        self.ai_results_text.configure(yscrollcommand=ai_scrollbar.set)
        
        self.ai_results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ai_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status
        ai_status_frame = ttk.Frame(self.ai_frame)
        ai_status_frame.pack(fill=tk.X, padx=5, pady=2)
        
        jan_status = "✓ Verbunden" if self.jan.is_connected else "✗ Nicht verbunden"
        self.jan_status_label = ttk.Label(ai_status_frame, text=f"Jan Schroeder: {jan_status}")
        self.jan_status_label.pack(side=tk.LEFT)
        
        self.refresh_ai_packages()
    
    def _setup_stats_tab(self):
        """Setup Statistics Tab"""
        # Stats Display
        self.stats_text = tk.Text(self.stats_frame, wrap=tk.WORD, font=('Courier', 10))
        stats_scrollbar = ttk.Scrollbar(self.stats_frame, orient=tk.VERTICAL, 
                                      command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scrollbar.set)
        
        self.stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Refresh Button
        refresh_frame = ttk.Frame(self.stats_frame)
        refresh_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(refresh_frame, text="Statistiken aktualisieren", 
                  command=self.refresh_statistics).pack(side=tk.LEFT, padx=5)
        
        self.refresh_statistics()
    
    def add_package(self):
        """Paket hinzufügen"""
        name = self.name_entry.get().strip()
        version = self.version_entry.get().strip()
        github_url = self.github_entry.get().strip()
        
        if not name:
            messagebox.showerror("Fehler", "Paketname ist erforderlich")
            return
        
        try:
            self.status_bar.config(text="Füge Paket hinzu...")
            self.root.update()
            
            package_id = self.orm.add_package(
                name=name,
                version=version or None,
                source="manual",
                github_url=github_url or None
            )
            
            self.clear_form()
            self.refresh_package_list()
            self.refresh_ai_packages()
            
            self.status_bar.config(text=f"Paket '{name}' erfolgreich hinzugefügt")
            messagebox.showinfo("Erfolg", f"Paket '{name}' wurde hinzugefügt")
            
        except Exception as e:
            self.status_bar.config(text="Fehler beim Hinzufügen")
            messagebox.showerror("Fehler", f"Fehler beim Hinzufügen: {str(e)}")
    
    def clear_form(self):
        """Formular leeren"""
        self.name_entry.delete(0, tk.END)
        self.version_entry.delete(0, tk.END)
        self.github_entry.delete(0, tk.END)
    
    def refresh_package_list(self):
        """Paket-Liste aktualisieren"""
        try:
            # Clear existing items
            for item in self.package_tree.get_children():
                self.package_tree.delete(item)
            
            # Get packages from database
            with sqlite3.connect(self.orm.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, version, source, quality_score, 
                           popularity_score, security_score
                    FROM packages
                    ORDER BY name
                ''')
                
                for row in cursor.fetchall():
                    self.package_tree.insert('', tk.END, values=row)
                    
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Pakete: {str(e)}")
    
    def refresh_ai_packages(self):
        """AI Package Combo aktualisieren"""
        try:
            with sqlite3.connect(self.orm.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM packages ORDER BY name')
                packages = [row[0] for row in cursor.fetchall()]
                
            self.ai_package_combo['values'] = packages
            
        except Exception as e:
            print(f"Fehler beim Laden der AI-Pakete: {e}")
    
    def on_package_select(self, event):
        """Package selection event"""
        selection = self.package_tree.selection()
        if selection:
            item = self.package_tree.item(selection[0])
            package_name = item['values'][0]
            messagebox.showinfo("Paket Info", f"Ausgewähltes Paket: {package_name}")
    
    def visualize_network(self):
        """Netzwerk visualisieren"""
        try:
            self.status_bar.config(text="Erstelle Netzwerk-Visualisierung...")
            self.root.update()
            
            # Get visualization data
            viz_data = self.orm.export_network_visualization_data(output_format='dict')
            
            if not viz_data.get('nodes'):
                messagebox.showwarning("Warnung", "Keine Netzwerk-Daten verfügbar")
                return
            
            # Clear previous plot
            self.ax.clear()
            
            # Create NetworkX graph for visualization
            G = nx.DiGraph()
            
            # Add nodes
            for node in viz_data['nodes']:
                G.add_node(node['id'], name=node['name'])
            
            # Add edges
            for edge in viz_data['edges']:
                G.add_edge(edge['from'], edge['to'], weight=edge['weight'])
            
            # Layout
            try:
                pos = nx.spring_layout(G, k=1, iterations=50)
            except:
                pos = nx.random_layout(G)
            
            # Draw network
            nx.draw(G, pos, ax=self.ax, 
                   with_labels=True, 
                   node_color='lightblue',
                   node_size=500,
                   font_size=8,
                   arrows=True,
                   edge_color='gray')
            
            self.ax.set_title("Package Dependency Network")
            self.canvas.draw()
            
            self.status_bar.config(text="Netzwerk-Visualisierung erstellt")
            
        except Exception as e:
            self.status_bar.config(text="Fehler bei Visualisierung")
            messagebox.showerror("Fehler", f"Visualisierungsfehler: {str(e)}")
    
    def export_network(self):
        """Netzwerk exportieren"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                viz_data = self.orm.export_network_visualization_data()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(viz_data)
                
                messagebox.showinfo("Erfolg", f"Netzwerk exportiert nach: {filename}")
                
        except Exception as e:
            messagebox.showerror("Fehler", f"Export-Fehler: {str(e)}")
    
    def analyze_with_ai(self):
        """KI-Analyse durchführen"""
        package_name = self.ai_package_var.get()
        if not package_name:
            messagebox.showwarning("Warnung", "Bitte Paket auswählen")
            return
        
        try:
            self.status_bar.config(text="Führe KI-Analyse durch...")
            self.root.update()
            
            # Get package data
            package = self.orm.get_package_by_name(package_name)
            if not package:
                messagebox.showerror("Fehler", "Paket nicht gefunden")
                return
            
            # AI Analysis
            analysis = self.jan.analyze_package_with_ai(package_name, package)
            
            # Display results
            self.ai_results_text.delete(1.0, tk.END)
            self.ai_results_text.insert(tk.END, f"KI-Analyse für '{package_name}':\n")
            self.ai_results_text.insert(tk.END, "=" * 50 + "\n\n")
            self.ai_results_text.insert(tk.END, analysis)
            
            self.status_bar.config(text="KI-Analyse abgeschlossen")
            
        except Exception as e:
            self.status_bar.config(text="Fehler bei KI-Analyse")
            messagebox.showerror("Fehler", f"KI-Analyse Fehler: {str(e)}")
    
    def refresh_statistics(self):
        """Statistiken aktualisieren"""
        try:
            stats = self.orm.get_statistics()
            
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(tk.END, "ALIENPIMP ORM - STATISTIKEN\n")
            self.stats_text.insert(tk.END, "=" * 50 + "\n\n")
            self.stats_text.insert(tk.END, json.dumps(stats, indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Statistik-Fehler: {str(e)}")
    
    def start_web_server(self):
        """Web-Server starten"""
        if self.web_server_thread and self.web_server_thread.is_alive():
            messagebox.showinfo("Info", "Web-Server läuft bereits")
            return
        
        try:
            web_interface = ApacheWebInterface(self.orm, self.jan)
            
            def run_server():
                web_interface.run(host='0.0.0.0', port=8080, debug=False)
            
            self.web_server_thread = threading.Thread(target=run_server, daemon=True)
            self.web_server_thread.start()
            
            self.status_bar.config(text="Web-Server gestartet auf Port 8080")
            messagebox.showinfo("Erfolg", "Web-Server gestartet auf http://localhost:8080")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Web-Server Fehler: {str(e)}")
    
    def open_web_interface(self):
        """Web-Interface im Browser öffnen"""
        webbrowser.open("http://localhost:8080")
    
    def check_jan_status(self):
        """Jan Schroeder Status prüfen"""
        self.jan._test_connection()
        status = "Verbunden" if self.jan.is_connected else "Nicht verbunden"
        messagebox.showinfo("Jan Schroeder Status", f"Status: {status}")
    
    def import_package(self):
        """Paket aus Datei importieren"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            # Implementation für Import
            messagebox.showinfo("Info", f"Import aus {filename} - Feature in Entwicklung")
    
    def export_database(self):
        """Datenbank exportieren"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            # Implementation für Export
            messagebox.showinfo("Info", f"Export nach {filename} - Feature in Entwicklung")
    
    def run(self):
        """GUI starten"""
        self.root.mainloop()


def main():
    """Hauptfunktion"""
    print("🚀 AlienPimp ORM Suite wird gestartet...")
    
    # Initialize components
    orm = ExtendedAlienPimpORM("alienpimp_production.db")
    jan_integration = JanSchrodoerIntegration()
    
    # Create and run GUI
    gui = TkinterGUI(orm, jan_integration)
    
    print("✅ GUI initialisiert")
    print("💡 Tipp: Starte das Web-Interface über das Server-Menü")
    print("🤖 Jan Schroeder Status:", "✅ Verbunden" if jan_integration.is_connected else "❌ Nicht verfügbar")
    
    gui.run()


if __name__ == "__main__":
    main()
