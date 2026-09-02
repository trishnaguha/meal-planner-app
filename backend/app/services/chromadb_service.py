import chromadb
from app.config import settings


class ChromaDBService:
    def __init__(
        self,
        path: str | None = settings.chroma_db_path,
        collection_name: str = settings.chroma_collection_name,
    ):
        if path is None:
            self._client = chromadb.Client()
        else:
            self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_meals(self, meals: list[dict]) -> None:
        self._collection.add(
            ids=[m["id"] for m in meals],
            documents=[m["text"] for m in meals],
            metadatas=[m["metadata"] for m in meals],
        )

    def query_meals(self, query_text: str, n_results: int = 10) -> list[dict]:
        results = self._collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )
        output = []
        for i in range(len(results["ids"][0])):
            output.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                }
            )
        return output

    def get_all_meals(self) -> list[dict]:
        results = self._collection.get()
        output = []
        for i in range(len(results["ids"])):
            output.append(
                {
                    "id": results["ids"][i],
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i],
                }
            )
        return output

    def meal_exists(self, dish_name: str) -> bool:
        results = self._collection.get(where={"dish": dish_name})
        return len(results["ids"]) > 0

    def get_collection_count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection.name,
            metadata={"hnsw:space": "cosine"},
        )


chroma_service = ChromaDBService()
