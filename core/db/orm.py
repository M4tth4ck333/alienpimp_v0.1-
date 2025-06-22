"""
Enhanced AlienPimpORM with Metadata and Joint Areal Network (JAN) Functionality
Extended with EtherApe-inspired network visualization capabilities
"""

import sqlite3
import json
import requests
import csv
import networkx as nx
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
import logging
from pathlib import Path
import hashlib
import time
from urllib.parse import urlparse


@dataclass
class GitHubMetadata:
    """Structure for GitHub-specific metadata"""
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


@dataclass 
class NetworkMetrics:
    """Network analysis metrics for packages"""
    centrality_betweenness: float = 0.0
    centrality_closeness: float = 0.0
    centrality_eigenvector: float = 0.0
    clustering_coefficient: float = 0.0
    degree_in: int = 0
    degree_out: int = 0
    pagerank: float = 0.0


class ExtendedAlienPimpORM:
    """
    Extended AlienPimpORM with metadata management and network analysis
    Inspired by EtherApe's network visualization concepts
    """
    
    def __init__(self, database_path: str = "alienpimp_extended.db"):
        self.database_path = database_path
        self.logger = self._setup_logging()
        self._initialize_database()
        self._graph = nx.DiGraph()  # Directed graph for package relationships
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration"""
        logger = logging.getLogger('AlienPimpORM')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _initialize_database(self):
        """Initialize the extended database structure"""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            # Main packages table (extended)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    version TEXT,
                    source TEXT,
                    description TEXT,
                    metadata JSON,
                    github_metadata JSON,
                    network_metrics JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_analyzed TIMESTAMP,
                    quality_score REAL DEFAULT 0.0,
                    popularity_score REAL DEFAULT 0.0,
                    security_score REAL DEFAULT 0.0,
                    hash_signature TEXT
                )
            ''')
            
            # Dependencies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER,
                    dependency_name TEXT NOT NULL,
                    dependency_version TEXT,
                    dependency_type TEXT DEFAULT 'runtime',
                    is_optional BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (package_id) REFERENCES packages (id),
                    UNIQUE(package_id, dependency_name)
                )
            ''')
            
            # Network relationships for Joint Areal Network
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS package_networks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_from_id INTEGER,
                    package_to_id INTEGER,
                    relation_type TEXT,
                    strength REAL DEFAULT 1.0,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (package_from_id) REFERENCES packages (id),
                    FOREIGN KEY (package_to_id) REFERENCES packages (id),
                    UNIQUE(package_from_id, package_to_id, relation_type)
                )
            ''')
            
            # Analysis history for tracking changes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER,
                    analysis_type TEXT,
                    results JSON,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (package_id) REFERENCES packages (id)
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_packages_name ON packages(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dependencies_package_id ON dependencies(package_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_networks_from_to ON package_networks(package_from_id, package_to_id)')
            
            conn.commit()
    
    def add_package(self, name: str, version: str = None, source: str = None, 
                   description: str = None, metadata: Dict = None,
                   github_url: str = None) -> int:
        """Add a new package to the database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Generate hash signature
                hash_data = f"{name}:{version}:{source}"
                hash_signature = hashlib.sha256(hash_data.encode()).hexdigest()
                
                # Fetch GitHub metadata if URL provided
                github_metadata = None
                if github_url:
                    github_metadata = self._fetch_github_metadata(github_url)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO packages 
                    (name, version, source, description, metadata, github_metadata, 
                     updated_at, hash_signature)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ''', (name, version, source, description, 
                      json.dumps(metadata or {}),
                      json.dumps(asdict(github_metadata)) if github_metadata else None,
                      hash_signature))
                
                package_id = cursor.lastrowid
                self.logger.info(f"Added package: {name} (ID: {package_id})")
                return package_id
                
        except Exception as e:
            self.logger.error(f"Error adding package {name}: {e}")
            raise
    
    def _fetch_github_metadata(self, github_url: str) -> Optional[GitHubMetadata]:
        """Fetch metadata from GitHub API"""
        try:
            # Parse GitHub URL to get owner/repo
            parsed = urlparse(github_url)
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) >= 2:
                owner, repo = path_parts[0], path_parts[1]
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                
                response = requests.get(api_url, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    
                    return GitHubMetadata(
                        github_url=github_url,
                        stars=data.get('stargazers_count', 0),
                        forks=data.get('forks_count', 0),
                        watchers=data.get('watchers_count', 0),
                        language=data.get('language'),
                        topics=data.get('topics', []),
                        license=data.get('license', {}).get('name') if data.get('license') else None,
                        open_issues=data.get('open_issues_count', 0),
                        size=data.get('size', 0),
                        created_at=data.get('created_at'),
                        updated_at=data.get('updated_at')
                    )
                    
        except Exception as e:
            self.logger.warning(f"Failed to fetch GitHub metadata for {github_url}: {e}")
            
        return None
    
    def add_dependency(self, package_id: int, dependency_name: str, 
                      dependency_version: str = None, dependency_type: str = 'runtime',
                      is_optional: bool = False):
        """Add a dependency relationship"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO dependencies 
                    (package_id, dependency_name, dependency_version, dependency_type, is_optional)
                    VALUES (?, ?, ?, ?, ?)
                ''', (package_id, dependency_name, dependency_version, dependency_type, is_optional))
                
                conn.commit()
                self.logger.info(f"Added dependency: {dependency_name} for package ID {package_id}")
                
        except Exception as e:
            self.logger.error(f"Error adding dependency: {e}")
            raise
    
    def add_network_relationship(self, package_from_id: int, package_to_id: int,
                               relation_type: str, strength: float = 1.0,
                               metadata: Dict = None):
        """Add a network relationship between packages (EtherApe-inspired)"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO package_networks 
                    (package_from_id, package_to_id, relation_type, strength, metadata, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (package_from_id, package_to_id, relation_type, strength, 
                      json.dumps(metadata or {})))
                
                conn.commit()
                
                # Update in-memory graph
                self._update_graph()
                
                self.logger.info(f"Added network relationship: {package_from_id} -> {package_to_id} ({relation_type})")
                
        except Exception as e:
            self.logger.error(f"Error adding network relationship: {e}")
            raise
    
    def _update_graph(self):
        """Update the in-memory NetworkX graph"""
        try:
            self._graph.clear()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Add nodes (packages)
                cursor.execute('SELECT id, name FROM packages')
                for package_id, name in cursor.fetchall():
                    self._graph.add_node(package_id, name=name)
                
                # Add edges (relationships)
                cursor.execute('''
                    SELECT package_from_id, package_to_id, relation_type, strength 
                    FROM package_networks
                ''')
                for from_id, to_id, rel_type, strength in cursor.fetchall():
                    self._graph.add_edge(from_id, to_id, 
                                       relation_type=rel_type, 
                                       weight=strength)
                
        except Exception as e:
            self.logger.error(f"Error updating graph: {e}")
    
    def calculate_network_metrics(self, package_id: int) -> NetworkMetrics:
        """Calculate network metrics for a package (EtherApe-inspired analysis)"""
        if self._graph.number_of_nodes() == 0:
            self._update_graph()
        
        if package_id not in self._graph:
            return NetworkMetrics()
        
        try:
            # Calculate various centrality measures
            betweenness = nx.betweenness_centrality(self._graph).get(package_id, 0.0)
            closeness = nx.closeness_centrality(self._graph).get(package_id, 0.0)
            
            # Handle eigenvector centrality (can fail on some graphs)
            try:
                eigenvector = nx.eigenvector_centrality(self._graph).get(package_id, 0.0)
            except:
                eigenvector = 0.0
            
            # Calculate PageRank
            pagerank = nx.pagerank(self._graph).get(package_id, 0.0)
            
            # Degree centralities
            in_degree = self._graph.in_degree(package_id)
            out_degree = self._graph.out_degree(package_id)
            
            # Clustering coefficient
            clustering = nx.clustering(self._graph.to_undirected()).get(package_id, 0.0)
            
            return NetworkMetrics(
                centrality_betweenness=betweenness,
                centrality_closeness=closeness,
                centrality_eigenvector=eigenvector,
                clustering_coefficient=clustering,
                degree_in=in_degree,
                degree_out=out_degree,
                pagerank=pagerank
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating network metrics for package {package_id}: {e}")
            return NetworkMetrics()
    
    def analyze_package_ecosystem(self, package_id: int) -> Dict[str, Any]:
        """Comprehensive ecosystem analysis (inspired by EtherApe's network analysis)"""
        try:
            if self._graph.number_of_nodes() == 0:
                self._update_graph()
            
            metrics = self.calculate_network_metrics(package_id)
            
            # Find communities/clusters
            undirected_graph = self._graph.to_undirected()
            try:
                communities = list(nx.community.greedy_modularity_communities(undirected_graph))
                package_community = None
                for i, community in enumerate(communities):
                    if package_id in community:
                        package_community = i
                        break
            except:
                package_community = None
            
            # Find shortest paths to important packages
            important_packages = self._get_most_important_packages(limit=10)
            shortest_paths = {}
            
            for target_id in important_packages:
                if target_id != package_id:
                    try:
                        path_length = nx.shortest_path_length(self._graph, package_id, target_id)
                        shortest_paths[target_id] = path_length
                    except nx.NetworkXNoPath:
                        continue
            
            analysis_result = {
                'package_id': package_id,
                'network_metrics': asdict(metrics),
                'community_id': package_community,
                'total_communities': len(communities) if communities else 0,
                'shortest_paths_to_important': shortest_paths,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Store analysis in history
            self._store_analysis_result(package_id, 'ecosystem_analysis', analysis_result)
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error in ecosystem analysis for package {package_id}: {e}")
            raise
    
    def _get_most_important_packages(self, limit: int = 10) -> List[int]:
        """Get most important packages based on network metrics"""
        try:
            if self._graph.number_of_nodes() == 0:
                return []
            
            pagerank_scores = nx.pagerank(self._graph)
            sorted_packages = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)
            
            return [package_id for package_id, _ in sorted_packages[:limit]]
            
        except Exception as e:
            self.logger.error(f"Error getting important packages: {e}")
            return []
    
    def _store_analysis_result(self, package_id: int, analysis_type: str, results: Dict):
        """Store analysis results in history"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO analysis_history (package_id, analysis_type, results)
                    VALUES (?, ?, ?)
                ''', (package_id, analysis_type, json.dumps(results)))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error storing analysis result: {e}")
    
    def get_package_by_name(self, name: str) -> Optional[Dict]:
        """Retrieve package information by name"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, name, version, source, description, metadata, 
                           github_metadata, network_metrics, quality_score, 
                           popularity_score, security_score
                    FROM packages WHERE name = ?
                ''', (name,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'version': row[2],
                        'source': row[3],
                        'description': row[4],
                        'metadata': json.loads(row[5]) if row[5] else {},
                        'github_metadata': json.loads(row[6]) if row[6] else None,
                        'network_metrics': json.loads(row[7]) if row[7] else None,
                        'quality_score': row[8],
                        'popularity_score': row[9],
                        'security_score': row[10]
                    }
                    
        except Exception as e:
            self.logger.error(f"Error retrieving package {name}: {e}")
            
        return None
    
    def export_network_visualization_data(self, output_format: str = 'json') -> Union[str, Dict]:
        """Export network data for visualization (EtherApe-style)"""
        try:
            if self._graph.number_of_nodes() == 0:
                self._update_graph()
            
            # Prepare nodes data
            nodes = []
            for node_id in self._graph.nodes():
                node_data = self._graph.nodes[node_id]
                metrics = self.calculate_network_metrics(node_id)
                
                nodes.append({
                    'id': node_id,
                    'name': node_data.get('name', f'Package_{node_id}'),
                    'metrics': asdict(metrics)
                })
            
            # Prepare edges data
            edges = []
            for from_id, to_id, edge_data in self._graph.edges(data=True):
                edges.append({
                    'from': from_id,
                    'to': to_id,
                    'relation_type': edge_data.get('relation_type', 'unknown'),
                    'weight': edge_data.get('weight', 1.0)
                })
            
            visualization_data = {
                'nodes': nodes,
                'edges': edges,
                'metadata': {
                    'total_nodes': len(nodes),
                    'total_edges': len(edges),
                    'export_timestamp': datetime.now().isoformat()
                }
            }
            
            if output_format.lower() == 'json':
                return json.dumps(visualization_data, indent=2)
            else:
                return visualization_data
                
        except Exception as e:
            self.logger.error(f"Error exporting visualization data: {e}")
            return {} if output_format != 'json' else '{}'
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Package statistics
                cursor.execute('SELECT COUNT(*) FROM packages')
                total_packages = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM dependencies')
                total_dependencies = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM package_networks')
                total_relationships = cursor.fetchone()[0]
                
                # Quality score statistics
                cursor.execute('SELECT AVG(quality_score), MIN(quality_score), MAX(quality_score) FROM packages')
                quality_stats = cursor.fetchone()
                
                # Network statistics
                if self._graph.number_of_nodes() == 0:
                    self._update_graph()
                
                network_stats = {}
                if self._graph.number_of_nodes() > 0:
                    network_stats = {
                        'nodes': self._graph.number_of_nodes(),
                        'edges': self._graph.number_of_edges(),
                        'density': nx.density(self._graph),
                        'is_connected': nx.is_weakly_connected(self._graph)
                    }
                
                return {
                    'packages': {
                        'total': total_packages,
                        'with_github_data': 0  # Would need additional query
                    },
                    'dependencies': {
                        'total': total_dependencies
                    },
                    'relationships': {
                        'total': total_relationships
                    },
                    'quality_scores': {
                        'average': quality_stats[0] or 0.0,
                        'minimum': quality_stats[1] or 0.0,
                        'maximum': quality_stats[2] or 0.0
                    },
                    'network': network_stats,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}


# Example usage and testing
if __name__ == "__main__":
    # Initialize ORM
    orm = ExtendedAlienPimpORM("test_alienpimp.db")
    
    # Add some test packages
    pkg1_id = orm.add_package(
        name="numpy",
        version="1.24.0", 
        source="pypi",
        description="Fundamental package for scientific computing with Python",
        github_url="https://github.com/numpy/numpy"
    )
    
    pkg2_id = orm.add_package(
        name="pandas", 
        version="2.0.0",
        source="pypi", 
        description="Powerful data structures for data analysis",
        github_url="https://github.com/pandas-dev/pandas"
    )
    
    # Add dependencies
    orm.add_dependency(pkg2_id, "numpy", ">=1.21.0")
    
    # Add network relationships
    orm.add_network_relationship(pkg2_id, pkg1_id, "depends_on", strength=0.9)
    
    # Perform analysis
    analysis = orm.analyze_package_ecosystem(pkg1_id)
    print("Ecosystem Analysis Results:")
    print(json.dumps(analysis, indent=2))
    
    # Get statistics
    stats = orm.get_statistics()
    print("\nDatabase Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Export visualization data
    viz_data = orm.export_network_visualization_data()
    print("\nVisualization Data:")
    print(viz_data[:500] + "..." if len(viz_data) > 500 else viz_data)
