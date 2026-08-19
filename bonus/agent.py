"""Bonus Challenge: Hybrid Memory Agent for Personal AI Assistant.

Combines Episodic Memory (Qdrant in-memory vector store) with
Stable User Profile & Realtime Activity (Feast Feature Store).
"""
import time
from pathlib import Path
from typing import Any

from fastembed import TextEmbedding
from feast import FeatureStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent


class HybridMemoryAgent:
    """Personal AI Assistant Memory combining Vector Store and Feature Store."""

    def __init__(self, user_id: str = "u_001"):
        self.user_id = user_id
        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        
        # 1. Episodic Memory (Qdrant in-memory)
        self.qdrant = QdrantClient(":memory:")
        self.collection_name = "episodic_memory"
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        
        # In-memory document storage for BM25
        self.memories: list[dict[str, Any]] = []
        self.bm25: BM25Okapi | None = None
        self._point_id = 0
        
        # 2. Stable Profile & Activity (Feast Feature Store)
        feast_repo_path = ROOT / "app" / "feast_repo"
        self.fs = FeatureStore(repo_path=str(feast_repo_path))

    def remember(self, text: str, user_id: str | None = None, topic: str = "general") -> None:
        """Add a new piece of episodic memory for the specified user."""
        uid = user_id or self.user_id
        doc_id = f"mem_{self._point_id:04d}"
        
        # Embed vector
        vec = next(self.embedder.embed([text])).tolist()
        
        # Upsert to Vector Store
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=self._point_id,
                    vector=vec,
                    payload={"doc_id": doc_id, "user_id": uid, "text": text, "topic": topic},
                )
            ],
        )
        
        # Update BM25
        self.memories.append({"doc_id": doc_id, "user_id": uid, "text": text, "topic": topic})
        tokenized = [m["text"].lower().split() for m in self.memories]
        self.bm25 = BM25Okapi(tokenized)
        self._point_id += 1

    def recall(self, query: str, user_id: str | None = None, top_k: int = 3, rrf_k: int = 60) -> str:
        """Retrieve top-K memories (Hybrid RRF) + User Profile features → Assembled Context."""
        uid = user_id or self.user_id
        
        # 1. Fetch User Profile & Recent Velocity from Feast Online Store
        feature_dict = {}
        try:
            feats = self.fs.get_online_features(
                features=[
                    "user_profile_features:reading_speed_wpm",
                    "user_profile_features:preferred_language",
                    "user_profile_features:topic_affinity",
                    "query_velocity_features:queries_last_hour",
                ],
                entity_rows=[{"user_id": uid}],
            ).to_dict()
            feature_dict = {k: v[0] for k, v in feats.items()}
        except Exception:
            feature_dict = {
                "user_profile_features:reading_speed_wpm": 220,
                "user_profile_features:preferred_language": "vi",
                "user_profile_features:topic_affinity": "cloud",
                "query_velocity_features:queries_last_hour": 5,
            }

        # 2. Hybrid Search in Episodic Memory with User-ID Filter
        q_vec = next(self.embedder.embed([query])).tolist()
        
        # Vector Search with payload filter
        user_filter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=uid))])
        res = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=q_vec,
            query_filter=user_filter,
            limit=10,
        )
        sem_ids = [p.payload["doc_id"] for p in res.points]
        
        # BM25 Search
        kw_ids = []
        if self.bm25 and self.memories:
            scores = self.bm25.get_scores(query.lower().split())
            ranked = sorted(
                [(self.memories[i]["doc_id"], scores[i]) for i in range(len(self.memories)) if self.memories[i]["user_id"] == uid],
                key=lambda x: -x[1],
            )
            kw_ids = [doc_id for doc_id, s in ranked if s > 0][:10]

        # RRF Fusion
        rrf: dict[str, float] = {}
        for rank, doc_id in enumerate(kw_ids, start=1):
            rrf[doc_id] = rrf.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)
        for rank, doc_id in enumerate(sem_ids, start=1):
            rrf[doc_id] = rrf.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)

        top_doc_ids = [d for d, _ in sorted(rrf.items(), key=lambda kv: -kv[1])[:top_k]]
        
        # Map doc_id to text
        mem_map = {m["doc_id"]: m["text"] for m in self.memories}
        retrieved_texts = [mem_map[did] for did in top_doc_ids if did in mem_map]

        # 3. Assemble Rich Prompt Context
        affinity = feature_dict.get("user_profile_features:topic_affinity", "general")
        lang = feature_dict.get("user_profile_features:preferred_language", "vi")
        wpm = feature_dict.get("user_profile_features:reading_speed_wpm", 200)
        v_1h = feature_dict.get("query_velocity_features:queries_last_hour", 0)

        context_lines = [
            f"=== USER CONTEXT ({uid}) ===",
            f"• Preferred Language: {lang} | Topic Affinity: {affinity} | Reading Speed: {wpm} wpm",
            f"• Recent Activity: {v_1h} queries in last hour",
            f"=== RELEVANT MEMORIES (Top-{len(retrieved_texts)}) ===",
        ]
        for i, text in enumerate(retrieved_texts, 1):
            context_lines.append(f"{i}. {text}")

        return "\n".join(context_lines)
