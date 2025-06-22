"""
Erweiterte AlienPimpORM mit Metadaten und Joint Areal Network (JAN) Funktionalität
Basiert auf: https://github.com/M4tth4ck333/alienpimp_v0.1-/blob/main/orm.py
"""

import sqlite3
import json
import requests
import csv
import networkx as nx
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import logging
from pathlib import Path


@dataclass
class GitHubMetadata:
    """Struktur für GitHub-spezifische Metadaten"""
    github_url: str
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    last_commit: Optional[str] = None
    language: Optional[str] = None
    topics: List[str] = None
    license: Optional[str] = None
    open_issues: int = 0
    size: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.topics is None:
            self.topics = []


class ExtendedAlienPimpORM:
    """
    Erweiterte AlienPimpORM mit Metadaten-Management und Netzwerk-Analyse
    """
    
    def __init__(self, database_path: str = "alienpimp_extended.db"):
        self.database_path = database_path
        self.logger = self._setup_logging()
        self._initialize_database()
        
    def _setup_logging(self) -> logging.Logger:
        """Richtet Logging ein"""
        logger = logging.getLogger('AlienPimpORM')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _initialize_database(self):
        """Initialisiert die erweiterte Datenbankstruktur"""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            # Haupttabelle für Pakete (erweitert)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    version TEXT,
                    source TEXT,
                    description TEXT,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_analyzed TIMESTAMP,
                    quality_score REAL DEFAULT 0.0,
                    popularity_score REAL DEFAULT 0.0
                )
            ''')
            
            # Abhängigkeiten-Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER,
                    dependency_name TEXT NOT NULL,
                    dependency_version TEXT,
                    dependency_type TEXT DEFAULT 'runtime',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (package_id) REFERENCES packages (id),
                    UNIQUE(package_id, dependency_name)
                )
            ''')
            
            # Netzwerk-Beziehungen für Joint Areal Network
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS package_networks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_from_id INTEGER,
                    package_to_id INTEGER,
                    relation_type TEXT,
                    strength REAL DEFAULT 1.0,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (package_from_id) REFERENCES packages (id),
                    FOREIGN KEY (package_to_id) REFERENCES packages (id),
                    UNIQUE(package_from_id, package_to_id, relation_type)
                )
            ''')
            
            # Maintainer/Authors Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS maintainers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER,
                    name TEXT NOT NULL,
                    email TEXT,
                    github_username TEXT,
                    role TEXT DEFAULT 'maintainer',
                    FOREIGN KEY (package_id) REFERENCES packages (id)
                )
            ''')
            
            # Indizes für Performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_packages_name ON packages (name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dependencies_package ON dependencies (package_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dependencies_name ON dependencies (dependency_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_networks_from ON package_networks (package_from_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_networks_to ON package_networks (package_to_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_maintainers_package ON maintainers (package_id)')
            
            conn.commit()
            self.logger.info("Datenbank initialisiert")
    
    def fetch_github_metadata(self, repo_url: str, github_token: Optional[str] = None) -> Optional[GitHubMetadata]:
        """
        Holt Metadaten von GitHub-Repository
        
        Args:
            repo_url: GitHub Repository URL
            github_token: Optional GitHub Personal Access Token für höhere Rate Limits
        
        Returns:
            GitHubMetadata oder None bei Fehler
        """
        try:
            # Extrahiere Owner/Repo aus URL
            if 'github.com' not in repo_url:
                return None
                
            parts = repo_url.replace('https://github.com/', '').replace('.git', '').split('/')
            if len(parts) < 2:
                return None
                
            owner, repo = parts[0], parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                return GitHubMetadata(
                    github_url=repo_url,
                    stars=data.get('stargazers_count', 0),
                    forks=data.get('forks_count', 0),
                    watchers=data.get('watchers_count', 0),
                    last_commit=data.get('pushed_at'),
                    language=data.get('language'),
                    topics=data.get('topics', []),
                    license=data.get('license', {}).get('name') if data.get('license') else None,
                    open_issues=data.get('open_issues_count', 0),
                    size=data.get('size', 0),
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                )
            else:
                self.logger.warning(f"GitHub API Fehler {response.status_code} für {repo_url}")
                return None
                
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der GitHub-Metadaten für {repo_url}: {e}")
            return None
    
    def add_package_with_github(self, name: str, version: str, source: str, 
                               github_url: str, dependencies: List[str] = None,
                               description: str = None, github_token: str = None) -> int:
        """
        Fügt ein Paket mit automatischer GitHub-Metadaten-Anreicherung hinzu
        
        Returns:
            Package ID
        """
        # GitHub-Metadaten abrufen
        github_metadata = self.fetch_github_metadata(github_url, github_token)
        
        # Kombiniere alle Metadaten
        metadata = {
            'github_url': github_url,
            'enriched_at': datetime.now().isoformat()
        }
        
        if github_metadata:
            metadata.update(asdict(github_metadata))
            
        # Berechne Qualitäts- und Popularitätscore
        quality_score = self._calculate_quality_score(github_metadata)
        popularity_score = self._calculate_popularity_score(github_metadata)
        
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            # Paket einfügen/aktualisieren
            cursor.execute('''
                INSERT OR REPLACE INTO packages 
                (name, version, source, description, metadata, updated_at, 
                 last_analyzed, quality_score, popularity_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, version, source, description, json.dumps(metadata),
                  datetime.now().isoformat(), datetime.now().isoformat(),
                  quality_score, popularity_score))
            
            package_id = cursor.lastrowid or cursor.execute(
                'SELECT id FROM packages WHERE name = ?', (name,)
            ).fetchone()[0]
            
            # Abhängigkeiten hinzufügen
            if dependencies:
                # Alte Abhängigkeiten entfernen
                cursor.execute('DELETE FROM dependencies WHERE package_id = ?', (package_id,))
                
                # Neue Abhängigkeiten hinzufügen
                for dep in dependencies:
                    cursor.execute('''
                        INSERT OR IGNORE INTO dependencies (package_id, dependency_name)
                        VALUES (?, ?)
                    ''', (package_id, dep))
            
            conn.commit()
            self.logger.info(f"Paket {name} mit GitHub-Metadaten hinzugefügt (ID: {package_id})")
            return package_id
    
    def _calculate_quality_score(self, github_metadata: Optional[GitHubMetadata]) -> float:
        """Berechnet einen Qualitätsscore basierend auf GitHub-Metadaten"""
        if not github_metadata:
            return 0.0
            
        score = 0.0
        
        # Stars (0-40 Punkte, logarithmisch skaliert)
        if github_metadata.stars > 0:
            score += min(40, 10 * (github_metadata.stars ** 0.3))
        
        # Forks (0-20 Punkte)
        if github_metadata.forks > 0:
            score += min(20, 5 * (github_metadata.forks ** 0.3))
        
        # Aktualität (0-20 Punkte)
        if github_metadata.last_commit:
            try:
                last_commit = datetime.fromisoformat(github_metadata.last_commit.replace('Z', '+00:00'))
                days_ago = (datetime.now().replace(tzinfo=last_commit.tzinfo) - last_commit).days
                if days_ago < 30:
                    score += 20
                elif days_ago < 90:
                    score += 15
                elif days_ago < 365:
                    score += 10
                elif days_ago < 730:
                    score += 5
            except:
                pass
        
        # Lizenz vorhanden (0-10 Punkte)
        if github_metadata.license:
            score += 10
        
        # Topics/Tags (0-10 Punkte)
        if github_metadata.topics:
            score += min(10, len(github_metadata.topics) * 2)
        
        return min(100.0, score)
    
    def _calculate_popularity_score(self, github_metadata: Optional[GitHubMetadata]) -> float:
        """Berechnet einen Popularitätsscore"""
        if not github_metadata:
            return 0.0
            
        # Einfache Gewichtung: Stars (70%) + Forks (20%) + Watchers (10%)
        score = (github_metadata.stars * 0.7 + 
                github_metadata.forks * 0.2 + 
                github_metadata.watchers * 0.1)
        
        return min(1000.0, score)  # Cap bei 1000
    
    def build_joint_areal_network(self) -> nx.DiGraph:
        """
        Erstellt ein Joint Areal Network (JAN) aus den Paketdaten
        
        Returns:
            NetworkX DiGraph mit Paketen als Knoten und Beziehungen als Kanten
        """
        graph = nx.DiGraph()
        
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            # Alle Pakete als Knoten hinzufügen
            cursor.execute('SELECT id, name, metadata, quality_score, popularity_score FROM packages')
            packages = cursor.fetchall()
            
            for pkg_id, name, metadata_json, quality, popularity in packages:
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                graph.add_node(name, 
                              id=pkg_id,
                              metadata=metadata,
                              quality_score=quality,
                              popularity_score=popularity)
            
            # Abhängigkeits-Kanten hinzufügen
            cursor.execute('''
                SELECT p1.name, p2.name, COUNT(*) as strength
                FROM dependencies d
                JOIN packages p1 ON d.package_id = p1.id
                JOIN packages p2 ON d.dependency_name = p2.name
                GROUP BY p1.name, p2.name
            ''')
            
            for pkg_from, pkg_to, strength in cursor.fetchall():
                if graph.has_node(pkg_from) and graph.has_node(pkg_to):
                    graph.add_edge(pkg_from, pkg_to, 
                                 relation='dependency', 
                                 weight=strength)
            
            # Gemeinsame Maintainer-Beziehungen
            cursor.execute('''
                SELECT p1.name, p2.name, COUNT(DISTINCT m1.name) as shared_maintainers
                FROM maintainers m1
                JOIN packages p1 ON m1.package_id = p1.id
                JOIN maintainers m2 ON m1.name = m2.name AND m1.package_id != m2.package_id
                JOIN packages p2 ON m2.package_id = p2.id
                WHERE p1.id < p2.id
                GROUP BY p1.name, p2.name
                HAVING shared_maintainers > 0
            ''')
            
            for pkg1, pkg2, shared_count in cursor.fetchall():
                if graph.has_node(pkg1) and graph.has_node(pkg2):
                    # Bidirektionale Kante für gemeinsame Maintainer
                    graph.add_edge(pkg1, pkg2, 
                                 relation='shared_maintainer', 
                                 weight=shared_count)
                    graph.add_edge(pkg2, pkg1, 
                                 relation='shared_maintainer', 
                                 weight=shared_count)
        
        self.logger.info(f"JAN-Graph erstellt: {graph.number_of_nodes()} Knoten, {graph.number_of_edges()} Kanten")
        return graph
    
    def analyze_package_ecosystem(self, package_name: str) -> Dict[str, Any]:
        """
        Führt eine umfassende Ökosystem-Analyse für ein Paket durch
        """
        graph = self.build_joint_areal_network()
        
        if package_name not in graph:
            return {'error': f'Paket {package_name} nicht gefunden'}
        
        analysis = {
            'package': package_name,
            'metadata': graph.nodes[package_name].get('metadata', {}),
            'scores': {
                'quality': graph.nodes[package_name].get('quality_score', 0),
                'popularity': graph.nodes[package_name].get('popularity_score', 0)
            }
        }
        
        # Direkte Abhängigkeiten
        dependencies = []
        dependents = []
        
        for neighbor in graph.neighbors(package_name):
            edge_data = graph[package_name][neighbor]
            if edge_data.get('relation') == 'dependency':
                dependencies.append({
                    'name': neighbor,
                    'weight': edge_data.get('weight', 1)
                })
        
        for predecessor in graph.predecessors(package_name):
            edge_data = graph[predecessor][package_name]
            if edge_data.get('relation') == 'dependency':
                dependents.append({
                    'name': predecessor,
                    'weight': edge_data.get('weight', 1)
                })
        
        analysis['dependencies'] = dependencies
        analysis['dependents'] = dependents
        
        # Ähnliche Pakete basierend auf Netzwerk-Nähe
        similar_packages = self._find_similar_packages(graph, package_name)
        analysis['similar_packages'] = similar_packages
        
        # Zentralitäts-Metriken
        if graph.number_of_nodes() > 1:
            try:
                betweenness = nx.betweenness_centrality(graph)
                closeness = nx.closeness_centrality(graph)
                pagerank = nx.pagerank(graph)
                
                analysis['centrality'] = {
                    'betweenness': betweenness.get(package_name, 0),
                    'closeness': closeness.get(package_name, 0),
                    'pagerank': pagerank.get(package_name, 0)
                }
            except:
                analysis['centrality'] = {'error': 'Konnte Zentralität nicht berechnen'}
        
        return analysis
    
    def _find_similar_packages(self, graph: nx.DiGraph, package_name: str, limit: int = 10) -> List[Dict]:
        """Findet ähnliche Pakete basierend auf Netzwerk-Eigenschaften"""
        if package_name not in graph:
            return []
        
        similar = []
        package_neighbors = set(graph.neighbors(package_name)) | set(graph.predecessors(package_name))
        package_metadata = graph.nodes[package_name].get('metadata', {})
        
        for other_pkg in graph.nodes():
            if other_pkg == package_name:
                continue
            
            # Berechne Ähnlichkeit basierend auf gemeinsamen Nachbarn
            other_neighbors = set(graph.neighbors(other_pkg)) | set(graph.predecessors(other_pkg))
            shared_neighbors = package_neighbors & other_neighbors
            
            if shared_neighbors:
                jaccard_similarity = len(shared_neighbors) / len(package_neighbors | other_neighbors)
                
                # Zusätzliche Ähnlichkeit basierend auf Metadaten
                metadata_similarity = self._calculate_metadata_similarity(
                    package_metadata, 
                    graph.nodes[other_pkg].get('metadata', {})
                )
                
                combined_similarity = (jaccard_similarity * 0.7) + (metadata_similarity * 0.3)
                
                similar.append({
                    'name': other_pkg,
                    'similarity': combined_similarity,
                    'shared_connections': len(shared_neighbors),
                    'quality_score': graph.nodes[other_pkg].get('quality_score', 0)
                })
        
        # Sortiere nach Ähnlichkeit
        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar[:limit]
    
    def _calculate_metadata_similarity(self, meta1: Dict, meta2: Dict) -> float:
        """Berechnet Ähnlichkeit basierend auf Metadaten"""
        similarity = 0.0
        
        # Sprache
        if meta1.get('language') and meta2.get('language'):
            if meta1['language'] == meta2['language']:
                similarity += 0.3
        
        # Topics/Tags
        topics1 = set(meta1.get('topics', []))
        topics2 = set(meta2.get('topics', []))
        if topics1 or topics2:
            topic_similarity = len(topics1 & topics2) / len(topics1 | topics2) if (topics1 | topics2) else 0
            similarity += topic_similarity * 0.4
        
        # Lizenz
        if meta1.get('license') and meta2.get('license'):
            if meta1['license'] == meta2['license']:
                similarity += 0.2
        
        # Stars-Ähnlichkeit (logarithmisch normalisiert)
        stars1 = meta1.get('stars', 0)
        stars2 = meta2.get('stars', 0)
        if stars1 > 0 and stars2 > 0:
            import math
            log_stars1 = math.log10(stars1 + 1)
            log_stars2 = math.log10(stars2 + 1)
            stars_similarity = 1 - abs(log_stars1 - log_stars2) / max(log_stars1, log_stars2)
            similarity += stars_similarity * 0.1
        
        return min(1.0, similarity)
    
    def export_network_analysis_to_csv(self, output_path: str):
        """Exportiert Netzwerk-Analyse als CSV"""
        graph = self.build_joint_areal_network()
        
        # Berechne Netzwerk-Metriken für alle Pakete
        betweenness = nx.betweenness_centrality(graph) if graph.number_of_nodes() > 1 else {}
        closeness = nx.closeness_centrality(graph) if graph.number_of_nodes() > 1 else {}
        pagerank = nx.pagerank(graph) if graph.number_of_nodes() > 1 else {}
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'package_name', 'quality_score', 'popularity_score',
                'dependencies_count', 'dependents_count',
                'betweenness_centrality', 'closeness_centrality', 'pagerank',
                'github_stars', 'github_forks', 'language', 'license'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for node in graph.nodes():
                node_data = graph.nodes[node]
                metadata = node_data.get('metadata', {})
                
                # Zähle Abhängigkeiten und Dependents
                deps_count = len([n for n in graph.neighbors(node) 
                                if graph[node][n].get('relation') == 'dependency'])
                dependents_count = len([n for n in graph.predecessors(node) 
                                      if graph[n][node].get('relation') == 'dependency'])
                
                writer.writerow({
                    'package_name': node,
                    'quality_score': node_data.get('quality_score', 0),
                    'popularity_score': node_data.get('popularity_score', 0),
                    'dependencies_count': deps_count,
                    'dependents_count': dependents_count,
                    'betweenness_centrality': betweenness.get(node, 0),
                    'closeness_centrality': closeness.get(node, 0),
                    'pagerank': pagerank.get(node, 0),
                    'github_stars': metadata.get('stars', 0),
                    'github_forks': metadata.get('forks', 0),
                    'language': metadata.get('language', ''),
                    'license': metadata.get('license', '')
                })
        
        self.logger.info(f"Netzwerk-Analyse exportiert nach {output_path}")
    
    def get_trending_packages(self, days: int = 30, limit: int = 20) -> List[Dict]:
        """Findet trending Pakete basierend auf verschiedenen Metriken"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT name, metadata, quality_score, popularity_score, updated_at
                FROM packages 
                WHERE updated_at > ?
                ORDER BY (quality_score * 0.4 + popularity_score * 0.6) DESC
                LIMIT ?
            ''', (cutoff_date, limit))
            
            results = []
            for name, metadata_json, quality, popularity, updated_at in cursor.fetchall():
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                results.append({
                    'name': name,
                    'quality_score': quality,
                    'popularity_score': popularity,
                    'github_stars': metadata.get('stars', 0),
                    'github_forks': metadata.get('forks', 0),
                    'language': metadata.get('language'),
                    'updated_at': updated_at,
                    'trending_score': (quality * 0.4) + (popularity * 0.6)
                })
            
            return results
    
    def export_gephi_network(self, nodes_file: str, edges_file: str):
        """Exportiert das Netzwerk für Gephi-Visualisierung"""
        graph = self.build_joint_areal_network()
        
        # Knoten exportieren
        with open(nodes_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Id', 'Label', 'Quality', 'Popularity', 'Stars', 'Language'])
            
            for node in graph.nodes():
                node_data = graph.nodes[node]
                metadata = node_data.get('metadata', {})
                
                writer.writerow([
                    node,
                    node,
                    node_data.get('quality_score', 0),
                    node_data.get('popularity_score', 0),
                    metadata.get('stars', 0),
                    metadata.get('language', '')
                ])
        
        # Kanten exportieren
        with open(edges_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Source', 'Target', 'Type', 'Weight'])
            
            for source, target in graph.edges():
                edge_data = graph[source][target]
                writer.writerow([
                    source,
                    target,
                    edge_data.get('relation', 'unknown'),
                    edge_data.get('weight', 1)
                ])
        
        self.logger.info(f"Netzwerk für Gephi exportiert: {nodes_file}, {edges_file}")


# Beispiel-Nutzung
if __name__ == "__main__":
    # Initialisiere erweiterte ORM
    orm = ExtendedAlienPimpORM("alienpimp_extended.db")
    
    # Beispiel: Füge ein Paket mit GitHub-Metadaten hinzu
    package_id = orm.add_package_with_github(
        name="requests",
        version="2.28.1",
        source="pypi",
        github_url="https://github.com/psf/requests",
        dependencies=["urllib3", "certifi", "charset-normalizer"],
        description="HTTP library for Python"
    )
    
    # Analysiere das Paket-Ökosystem
    analysis = orm.analyze_package_ecosystem("requests")
    print("Ökosystem-Analyse:")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    
    # Exportiere Netzwerk-Analyse
    orm.export_network_analysis_to_csv("network_analysis.csv")
    
    # Hole trending Pakete
    trending = orm.get_trending_packages(days=30, limit=10)
    print("\nTrending Pakete:")
    for pkg in trending:
        print(f"- {pkg['name']}: Score {pkg['trending_score']:.2f} "
              f"(★{pkg['github_stars']}, Quality: {pkg['quality_score']:.1f})")
    
    # Exportiere für Gephi
    orm.export_gephi_network("nodes.csv", "edges.csv")
