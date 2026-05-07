# # python imports
# from typing import List
# import numpy as np
# import asyncio

# # db imports
# from astrapy.info import CollectionDefinition
# from astrapy.data_types import DataAPIVector
# from astrapy.constants import VectorMetric
# from astrapy import DataAPIClient


# ## START
# class CustomEmbedding:
#     def __init__(self, custom_embedding_model):
#         self.model = custom_embedding_model

#     def embed_query(self, text: str) -> List[float]:
#         """Embed a single query and return as list"""
#         embedding = self.model.encode(text)
#         # Convert numpy array to list
#         if isinstance(embedding, np.ndarray):
#             return embedding.tolist()
#         return embedding

#     def embed_documents(self, texts: List[str]) -> List[List[float]]:
#         """Process documents in small batches and return as list of lists"""
#         try:
#             embeddings = self.model.encode(texts)
#             # Convert numpy array to list of lists
#             if isinstance(embeddings, np.ndarray):
#                 return embeddings.tolist()
#             return embeddings
#         except Exception as e:
#             raise Exception(f"Error embedding documents: {str(e)}")

#     async def aembed_query(self, text: str) -> List[float]:
#         loop = asyncio.get_event_loop()
#         return await loop.run_in_executor(None, self.embed_query, text)

#     async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
#         loop = asyncio.get_event_loop()
#         return await loop.run_in_executor(None, self.embed_documents, texts)

#     def __call__(self, text: str) -> List[float]:
#         """Make the class callable"""
#         return self.embed_query(text)
# ## END

# class AstraIndex:
#     """
#     Astra DB-based hierarchical vector store.
#     Stores:
#       - micro level: vectorized content
#       - meso/macro: metadata only
#     """

#     def __init__(self, token: str, api_endpoint: str, keyspace: str, model, collection_name: str="searchengine_data"):
#         self.model = model
#         self.client = DataAPIClient(token)
#         self.db = self.client.get_database_by_api_endpoint(api_endpoint, keyspace=keyspace)
#         self.embedding_dim = len(model.embed_documents("hello"))
#         self.collection_name = collection_name

#     # Create collection
#     def _create_or_get_collection(self, name: str, vectorized: bool = False):
#         try:
#             if vectorized:
#                 definition = (
#                     CollectionDefinition.builder()
#                     .set_vector_dimension(self.embedding_dim)
#                     .set_vector_metric(VectorMetric.COSINE)
#                     .build()
#                 )
#                 collection = self.db.create_collection(name, definition=definition)
#             else:
#                 collection = self.db.create_collection(name)
#             print(f"Created new collection: {name}")
#         except Exception:
#             collection = self.db.get_collection(name)
#             print(f"Using existing collection: {name}")
#         return collection

#     def build_from_documents(self, documents_all):
#         """
#         Insert all documents into Astra DB (vectorized).
#         Each document will be embedded and stored with metadata.
#         """
#         # Create or get the Astra vector collection
#         collection = self._create_or_get_collection(self.collection_name, vectorized=True)

#         print(f"Preparing {len(documents_all)} documents for insertion...")

#         # Extract all text content for vectorization
#         texts = [doc.page_content for doc in documents_all]

#         embeddings = self.model.embed_documents(texts)
#         print(f"Inserting {len(documents_all)} documents...")

#         for i, doc in enumerate(documents_all):
#             meta = doc.metadata or {}

#             record = {
#                 "doc_id": f"doc_{i}",
#                 "file_name": meta.get("file"),
#                 "file_type": meta.get("file_type"),
#                 "creation_date": meta.get("creation_date"),
#                 "last_modified_date": meta.get("last_modified_date"),
#                 "content": doc.page_content,
#                 "$vector": embeddings[i],
#             }

#             collection.insert_one(record)
#         print("All documents inserted successfully.")

#     # Search: vector-based retrieval
#     def search_content(self, query: str, top_k: int = 5):
#         emb = self.model.embed_documents(query)
#         collection = self.db.get_collection(self.collection_name)

#         results = collection.find(
#             filter={}, # optional filter
#             sort={"$vector": DataAPIVector(emb)}, # vector search
#             limit=top_k,
#             projection={"file_name": True, "content": True},
#             include_similarity=True # ensures $similarity is added by Astra
#         )
#         return list(results)

#     def search_content_threshold(self, query: str, top_k: int = 5, min_similarity: float = 0.7):
#         """
#         Search with minimum similarity threshold

#         Args:
#             query: Search query
#             top_k: Maximum number of results
#             min_similarity: Minimum similarity score (0.0 to 1.0)
#         """
#         emb = self.model.embed_documents(query)
#         collection = self.db.get_collection(self.collection_name)

#         # Get results with similarity
#         results = collection.find(
#             filter={},
#             sort={"$vector": DataAPIVector(emb)},
#             limit=top_k,
#             projection={"file_name": True, "content": True},
#             include_similarity=True
#         )

#         # Filter by similarity threshold
#         filtered_results = [
#             doc for doc in results
#             if doc.get("$similarity", 0) >= min_similarity
#         ]

#         return filtered_results