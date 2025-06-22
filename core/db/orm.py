"""
Erweiterte Paketdatenbank mit Metadaten und Joint Areal Network Heuristik
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from dataclasses import dataclass, asdict
import networkx as nx


@dataclass
class PackageMetadata:
    """Struktur für erweiterte Paket-Metadaten"""
    github_url: Optional[str] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    last_commit: Optional[str] = None
    language: Optional[str] = None
    tags: List[str] = None
    dependencies: List[str] = None
    dependents: List[str] = None
    license: Optional[str] = None
    maintainers: List[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    download_count: Optional[int] = None
    vulnerability_score: Optional[float] = None
    quality_score: Optional[float] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
        if self.dependents is None:
            self.dependents = []
        if self.maintainers is None:
            self.maintainers = []


class JointArealNetwork:
    """
    Joint Areal Network (JAN) - Heuristik für Paket-Beziehungen
    Analysiert die Verbindungen zwischen Paketen basierend auf:
    - Abhängigkeiten
    - Gemeinsame Maintainer
    - Ähnliche Tags/Kategorien
    - GitHub-Aktivität
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        
    def build_network(self):
        """Erstellt das Netzwerk-Graph aus der Paketdatenbank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Lade alle Pakete mit Metadaten
        cursor.execute("SELECT name, metadata FROM packages")
        packages = cursor.fetchall()
        
        for name, metadata_json in packages:
            if metadata_json:
                metadata = json.loads(metadata_json)
                self.graph.add_node(name, **metadata)
                
                # Füge Abhängigkeits-Kanten hinzu
                if 'dependencies' in metadata:
                    for dep in metadata['dependencies']:
                        self.graph.add_edge(name, dep, relation='dependency', weight=1.0)
                
                # Füge Maintainer-Verbindungen hinzu
                if 'maintainers' in metadata:
                    for other_name, other_metadata_json in packages:
                        if other_name != name and other_metadata_json:
                            other_metadata = json.loads(other_metadata_json)
                            if 'maintainers' in other_metadata:
                                shared_maintainers = set(metadata['maintainers']) & set(other_metadata['maintainers'])
                                if shared_maintainers:
                                    weight = len(shared_maintainers) / max(len(metadata['maintainers']), len(other_metadata['maintainers']))
                                    self.graph.add_edge(name, other_name, relation='shared_maintainer', weight=weight)
        
        conn.close()
    
    def calculate_similarity_score(self, pkg1: str, pkg2: str) -> float:
        """Berechnet Ähnlichkeitsscore zwischen zwei Paketen"""
        if not self.graph.has_node(pkg1) or not self.graph.has_node(pkg2):
            return 0.0
        
        pkg1_data = self.graph.nodes[pkg1]
        pkg2_data = self.graph.nodes[pkg2]
        
        score = 0.0
        
        # Tag-Ähnlichkeit
        tags1 = set(pkg1_data.get('tags', []))
        tags2 = set(pkg2_data.get('tags', []))
        if tags1 or tags2:
            tag_similarity = len(tags1 & tags2) / len(tags1 | tags2) if (tags1 | tags2) else 0
            score += tag_similarity * 0.3
        
        # Sprach-Ähnlichkeit
        if pkg1_data.get('language') == pkg2_data.get('language') and pkg1_data.get('language'):
            score += 0.2
        
        # Maintainer-Ähnlichkeit
        maint1 = set(pkg1_data.get('maintainers', []))
        maint2 = set(pkg2_data.get('maintainers', []))
        if maint1 or maint2:
            maint_similarity = len(maint1 & maint2) / len(maint1 | maint2) if (maint1 | maint2) else 0
            score += maint_similarity * 0.3
        
        # GitHub-Stars Ähnlichkeit (normalisiert)
        stars1 = pkg1_data.get('stars', 0)
        stars2 = pkg2_data.get('stars', 0)
        if stars1 > 0 and stars2 > 0:
            star_similarity = 1 - abs(stars1 - stars2) / max(stars1, stars2)
            score += star_similarity * 0.2
        
        return min(score, 1.0)
    
    def get_recommendations(self, package_name: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Gibt empfohlene ähnliche Pakete zurück"""
        if not self.graph.has_node(package_name):
            return []
        
        recommendations = []
        
        for other_pkg in self.graph.nodes():
            if other_pkg != package_name:
                similarity = self.calculate_similarity_score(package_name, other_pkg)
                if similarity > 0.1:  # Minimum-Schwellenwert
                    recommendations.append((other_pkg, similarity))
        
        # Sortiere nach Ähnlichkeit (absteigend)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:limit]
    
    def detect_communities(self) -> Dict[int, List[str]]:
        """Erkennt Communities/Cluster im Paket-Netzwerk"""
        # Konvertiere zu ungerichtetem Graph für Community-Erkennung
        undirected = self.graph.to_undirected()
        
        # Verwende Louvain-Algorithmus für Community-Erkennung
        communities = nx.community.louvain_communities(undirected)
        
        return {i: list(community) for i, community in enumerate(communities)}


class EnhancedPackageDatabase:
    """Erweiterte Paketdatenbank mit Metadaten und Netzwerk-Funktionalität"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.jan = JointArealNetwork(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialisiert die erweiterte Datenbankstruktur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Erweiterte Pakete-Tabelle (falls noch nicht vorhanden)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                version TEXT,
                source TEXT,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabelle für Paket-Beziehungen (für bessere Performance)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS package_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_from TEXT,
                package_to TEXT,
                relation_type TEXT,
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (package_from) REFERENCES packages (name),
                FOREIGN KEY (package_to) REFERENCES packages (name)
            )
        ''')
        
        # Index für bessere Performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_package_name ON packages (name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_from ON package_relations (package_from)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_to ON package_relations (package_to)')
        
        conn.commit()
        conn.close()
    
    def add_package_with_metadata(self, name: str, version: str, source: str, metadata: PackageMetadata):
        """Fügt ein Paket mit erweiterten Metadaten hinzu"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(asdict(metadata))
        
        cursor.execute('''
            INSERT OR REPLACE INTO packages (name, version, source, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, version, source, metadata_json, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Aktualisiere Beziehungen
        self._update_package_relations(name, metadata)
    
    def _update_package_relations(self, package_name: str, metadata: PackageMetadata):
        """Aktualisiert die Paket-Beziehungen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Lösche alte Beziehungen
        cursor.execute('DELETE FROM package_relations WHERE package_from = ?', (package_name,))
        
        # Füge Abhängigkeits-Beziehungen hinzu
        for dep in metadata.dependencies:
            cursor.execute('''
                INSERT INTO package_relations (package_from, package_to, relation_type, weight)
                VALUES (?, ?, ?, ?)
            ''', (package_name, dep, 'dependency', 1.0))
        
        conn.commit()
        conn.close()
    
    def enrich_metadata_from_github(self, package_name: str, github_url: str) -> PackageMetadata:
        """Reichert Metadaten aus GitHub-API an"""
        # GitHub API URL extrahieren
        if 'github.com' in github_url:
            repo_path = github_url.replace('https://github.com/', '').replace('.git', '')
            api_url = f"https://api.github.com/repos/{repo_path}"
            
            try:
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    
                    return PackageMetadata(
                        github_url=github_url,
                        stars=data.get('stargazers_count'),
                        forks=data.get('forks_count'),
                        last_commit=data.get('updated_at'),
                        language=data.get('language'),
                        description=data.get('description'),
                        homepage=data.get('homepage'),
                        license=data.get('license', {}).get('name') if data.get('license') else None
                    )
            except Exception as e:
                print(f"Fehler beim Abrufen der GitHub-Daten: {e}")
        
        return PackageMetadata(github_url=github_url)
    
    def analyze_package_ecosystem(self, package_name: str) -> Dict:
        """Analysiert das Ökosystem eines Pakets"""
        # Baue das Netzwerk auf
        self.jan.build_network()
        
        # Hole Empfehlungen
        recommendations = self.jan.get_recommendations(package_name)
        
        # Hole direkte Abhängigkeiten und Dependents
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT package_to, weight FROM package_relations 
            WHERE package_from = ? AND relation_type = 'dependency'
        ''', (package_name,))
        dependencies = cursor.fetchall()
        
        cursor.execute('''
            SELECT package_from, weight FROM package_relations 
            WHERE package_to = ? AND relation_type = 'dependency'
        ''', (package_name,))
        dependents = cursor.fetchall()
        
        conn.close()
        
        return {
            'package': package_name,
            'direct_dependencies': dependencies,
            'dependents': dependents,
            'recommendations': recommendations,
            'community_analysis': self._get_package_community(package_name)
        }
    
    def _get_package_community(self, package_name: str) -> Dict:
        """Bestimmt die Community eines Pakets"""
        communities = self.jan.detect_communities()
        
        for community_id, packages in communities.items():
            if package_name in packages:
                return {
                    'community_id': community_id,
                    'community_size': len(packages),
                    'related_packages': packages[:10]  # Top 10
                }
        
        return {'community_id': None, 'community_size': 0, 'related_packages': []}
    
    def get_trending_packages(self, days: int = 30, limit: int = 10) -> List[Dict]:
        """Findet trending Pakete basierend auf verschiedenen Metriken"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT name, metadata, updated_at FROM packages 
            WHERE updated_at > ?
            ORDER BY updated_at DESC
        ''', (cutoff_date,))
        
        recent_packages = cursor.fetchall()
        conn.close()
        
        trending = []
        for name, metadata_json, updated_at in recent_packages:
            if metadata_json:
                metadata = json.loads(metadata_json)
                
                # Berechne Trending-Score
                score = 0
                if metadata.get('stars'):
                    score += metadata['stars'] * 0.3
                if metadata.get('forks'):
                    score += metadata['forks'] * 0.2
                if metadata.get('download_count'):
                    score += metadata['download_count'] * 0.4
                if metadata.get('quality_score'):
                    score += metadata['quality_score'] * 0.1
                
                trending.append({
                    'name': name,
                    'score': score,
                    'metadata': metadata,
                    'updated_at': updated_at
                })
        
        # Sortiere nach Score
        trending.sort(key=lambda x: x['score'], reverse=True)
        return trending[:limit]


# Beispiel für die Verwendung
if __name__ == "__main__":
    # Initialisiere die erweiterte Datenbank
    db = EnhancedPackageDatabase("enhanced_packages.db")
    
    # Beispiel: Füge ein Paket mit Metadaten hinzu
    metadata = PackageMetadata(
        github_url="https://github.com/user/repo",
        stars=150,
        forks=30,
        language="Python",
        tags=["web", "framework", "api"],
        dependencies=["requests", "flask", "sqlalchemy"],
        license="MIT",
        maintainers=["user1", "user2"]
    )
    
    db.add_package_with_metadata("example-package", "1.0.0", "pypi", metadata)
    
    # Analysiere das Paket-Ökosystem
    analysis = db.analyze_package_ecosystem("example-package")
    print("Ökosystem-Analyse:", json.dumps(analysis, indent=2))
    
    # Hole trending Pakete
    trending = db.get_trending_packages(days=30, limit=5)
    print("Trending Pakete:", json.dumps(trending, indent=2))
