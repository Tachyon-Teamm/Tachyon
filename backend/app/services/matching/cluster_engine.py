from typing import Dict, List, Set, Tuple, Any, Optional
import uuid

class DSU:
    """
    Disjoint Set Union (Union-Find) with path compression and rank optimization.
    """
    def __init__(self):
        self.parent: Dict[int, int] = {}
        self.rank: Dict[int, int] = {}

    def find(self, item: int) -> int:
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0
            return item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, x: int, y: int) -> int:
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return root_x

        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
            return root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
            return root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
            return root_x

class ClusterEngine:
    """
    Coherence-Gated Graph Transitive Closure Clustering Engine.
    Groups pairwise candidate matches into multi-material families
    while preventing 'transitive chaining explosion' through density checks.
    """

    @classmethod
    def form_clusters(
        cls,
        candidate_edges: List[Dict[str, Any]],
        min_score: float = 0.70,
        min_density: float = 0.60
    ) -> Dict[str, Any]:
        """
        Input candidate_edges: list of dicts with keys:
            'material_a_id', 'material_b_id', 'composite_score', 'is_vetoed'
        Returns:
            {
                'material_to_cluster': Dict[int, str],
                'clusters': Dict[str, List[int]],
                'total_clusters': int
            }
        """
        dsu = DSU()
        nodes: Set[int] = set()
        adj: Dict[int, Set[int]] = {}
        edge_scores: Dict[Tuple[int, int], float] = {}

        # 1. Filter valid unvetoed edges above threshold
        valid_edges = []
        for edge in candidate_edges:
            if edge.get("is_vetoed", False):
                continue
            score = edge.get("composite_score", 0.0)
            if score >= min_score:
                u = edge["material_a_id"]
                v = edge["material_b_id"]
                valid_edges.append((u, v, score))
                nodes.add(u)
                nodes.add(v)
                if u not in adj: adj[u] = set()
                if v not in adj: adj[v] = set()
                adj[u].add(v)
                adj[v].add(u)
                edge_scores[(min(u, v), max(u, v))] = score

        # Sort edges by score descending (Kruskal-like highest-confidence first)
        valid_edges.sort(key=lambda x: x[2], reverse=True)

        # 2. Add edges with anti-chaining coherence safeguard
        for u, v, score in valid_edges:
            root_u = dsu.find(u)
            root_v = dsu.find(v)
            if root_u == root_v:
                continue

            # Calculate prospective component membership
            comp_u = [n for n in nodes if dsu.find(n) == root_u]
            comp_v = [n for n in nodes if dsu.find(n) == root_v]
            merged_size = len(comp_u) + len(comp_v)

            # For components > 2 items, verify graph edge density before merging
            if merged_size > 2:
                # Count actual edges between comp_u and comp_v
                potential_edges = (merged_size * (merged_size - 1)) / 2
                actual_edges = 0
                all_nodes = comp_u + comp_v
                for i in range(len(all_nodes)):
                    for j in range(i + 1, len(all_nodes)):
                        pair = (min(all_nodes[i], all_nodes[j]), max(all_nodes[i], all_nodes[j]))
                        if pair in edge_scores:
                            actual_edges += 1

                density = actual_edges / potential_edges if potential_edges > 0 else 1.0
                if density < min_density:
                    # Reject merge to prevent transitive chain collapse (A~B and B~C but A!=C)
                    continue

            dsu.union(u, v)

        # 3. Assemble clusters
        clusters_by_root: Dict[int, List[int]] = {}
        for n in nodes:
            r = dsu.find(n)
            if r not in clusters_by_root:
                clusters_by_root[r] = []
            clusters_by_root[r].append(n)

        material_to_cluster: Dict[int, str] = {}
        named_clusters: Dict[str, List[int]] = {}

        for root, member_ids in clusters_by_root.items():
            cluster_uuid = f"cluster_{uuid.uuid4().hex[:8]}"
            named_clusters[cluster_uuid] = member_ids
            for mid in member_ids:
                material_to_cluster[mid] = cluster_uuid

        return {
            "material_to_cluster": material_to_cluster,
            "clusters": named_clusters,
            "total_clusters": len(named_clusters)
        }
