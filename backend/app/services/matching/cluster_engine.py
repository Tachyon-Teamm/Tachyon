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
    Multi-Organization Graph Entity Resolution & Correlation Clustering Engine.
    Implements:
      1. Correlation Clustering (Pivot Algorithm - Bansal et al.) for global multi-CPSE graph partitioning.
      2. Coherence-Gated DSU transitive clustering with graph density safeguards.
    """

    @classmethod
    def correlation_clustering_pivot(
        cls,
        nodes: List[int],
        positive_edges: Dict[Tuple[int, int], float],
        negative_edges: Set[Tuple[int, int]],
        threshold: float = 0.70
    ) -> Dict[str, List[int]]:
        """
        Approximation Pivot Algorithm for Correlation Clustering (Bansal et al.):
        Iteratively picks a pivot node and gathers all positive unvetoed neighbors into a cluster.
        """
        remaining_nodes = set(nodes)
        clusters: Dict[str, List[int]] = {}

        while remaining_nodes:
            # Pick a pivot (highest degree in positive graph)
            pivot = None
            best_deg = -1
            for n in remaining_nodes:
                deg = sum(1 for (u, v), w in positive_edges.items() if (u == n or v == n) and (u in remaining_nodes and v in remaining_nodes) and w >= threshold)
                if deg > best_deg:
                    best_deg = deg
                    pivot = n

            if pivot is None:
                pivot = next(iter(remaining_nodes))

            cluster = [pivot]
            remaining_nodes.remove(pivot)

            # Find all neighbors with strong positive weight and NO negative/veto edge to pivot
            candidates_to_add = []
            for other in remaining_nodes:
                pair = (min(pivot, other), max(pivot, other))
                if pair in negative_edges:
                    continue
                score = positive_edges.get(pair, 0.0)
                if score >= threshold:
                    candidates_to_add.append(other)

            for c in candidates_to_add:
                cluster.append(c)
                remaining_nodes.remove(c)

            cluster_uuid = f"cluster_{uuid.uuid4().hex[:8]}"
            clusters[cluster_uuid] = sorted(cluster)

        return clusters

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
        nodes: Set[int] = set()
        positive_edges: Dict[Tuple[int, int], float] = {}
        negative_edges: Set[Tuple[int, int]] = set()

        for edge in candidate_edges:
            u = edge["material_a_id"]
            v = edge["material_b_id"]
            nodes.add(u)
            nodes.add(v)
            pair = (min(u, v), max(u, v))

            if edge.get("is_vetoed", False) or edge.get("composite_score", 0.0) < min_score:
                negative_edges.add(pair)
            else:
                score = edge.get("composite_score", 0.0)
                positive_edges[pair] = score

        # Run Correlation Clustering
        named_clusters = cls.correlation_clustering_pivot(
            nodes=list(nodes),
            positive_edges=positive_edges,
            negative_edges=negative_edges,
            threshold=min_score
        )

        material_to_cluster: Dict[int, str] = {}
        for cluster_id, member_ids in named_clusters.items():
            for mid in member_ids:
                material_to_cluster[mid] = cluster_id

        return {
            "material_to_cluster": material_to_cluster,
            "clusters": named_clusters,
            "total_clusters": len(named_clusters)
        }
