from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Union

from google.cloud import firestore_v1 as firestore
from pydantic import BaseModel


class FirestoreDocumentModel(ABC):
    @abstractmethod
    def dump(self) -> str:
        pass

    @abstractmethod
    def get_doc_id(self) -> str:
        pass

    @abstractmethod
    def get_attributes(self) -> Dict[str, Any]:
        pass

class LiveMatchInfo(BaseModel):
    match_id: int = 0
    radiant_team_name: str = ""
    dire_team_name: str = ""


class LiveMatches(BaseModel, FirestoreDocumentModel):
    matches: List[LiveMatchInfo] = []

    def dump(self) -> str:
        return self.model_dump_json()

    @staticmethod
    def get_doc_id() -> str:
        return "0"

    def get_attributes(self) -> Dict[str, Any]:
        return self.model_dump()


class GsiEvent(BaseModel, FirestoreDocumentModel):
    token: str = ""
    match_id: int = 0
    timestamp: int = 0
    clock_time: int = 0
    game_time: int = 0
    match_data: str = ""

    def dump(self) -> str:
        return self.model_dump_json()

    def get_doc_id(self) -> str:
        return self.token

    def get_attributes(self) -> Dict[str, Any]:
        return self.model_dump()


COLLECTION_MODEL_MAP = {
    "gsi-events": GsiEvent,
    "live-matches": LiveMatches
}


class FirestoreDb:
    client = None

    class Client:
        def __init__(
            self,
            project_id: str = "",
            database_name: str = "",
            ttl_sec: int = 3600,
            *args,
            **kwargs
        ):
            self.project_id = project_id
            self.database_name = database_name
            self.ttl_sec = ttl_sec
            self.fs_client = firestore.Client(
                project=self.project_id,
                database=self.database_name
            )

        # Saving a list of documents by writing them in a batch
        def save_documents(self, docs: List[FirestoreDocumentModel], collection_name: str) -> bool:
            if not (self.project_id and collection_name):
                return False

            expire_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_sec)

            batch = self.fs_client.batch()

            for doc in docs:
                doc_id = doc.get_doc_id()
                document_ref = self.fs_client.collection(collection_name).document(
                    doc_id
                )
                document_attributes: Dict[str, Any] = doc.get_attributes()

                # Add TTL field
                document_attributes["expireAt"] = expire_at

                batch.set(document_ref, document_attributes, merge=True)

            try:
                batch.commit()
                res = True
            except Exception:
                res = False

            return res

        # Querying a single document by its document ID in Firestore
        def query_document(
            self,
            document_id: str,
            collection_name: str
        ) -> Union[BaseModel, None]:
            assert collection_name

            document_ref = self.fs_client.collection(collection_name).document(
                str(document_id)
            )
            document = document_ref.get()

            if document.exists:
                # Get the corresponding model class for the collection
                model_class = COLLECTION_MODEL_MAP.get(collection_name)
                if model_class:
                    doc_dict = document.to_dict()
                    return model_class(**doc_dict) if doc_dict else None

            return None

    def __new__(
        cls,
        project_id: str = "",
        database_name: str = "",
        ttl_sec: int = 3600,
        *args,
        **kwargs
    ):
        if not cls.client:
            cls.client = cls.Client(
                project_id,
                database_name,
                ttl_sec,
                *args,
                **kwargs
            )

        return cls.client

#
# from abc import ABC, abstractmethod
# from datetime import datetime, timedelta, timezone
# from typing import Any, Dict, List, Union
#
# from google.cloud import firestore
# from pydantic import BaseModel
#
#
# class FirestoreDocumentModel(ABC):
#     @abstractmethod
#     def dump(self) -> str:
#         pass
#
#     @abstractmethod
#     def get_doc_id(self) -> str:
#         pass
#
#     @abstractmethod
#     def get_attributes(self) -> Dict[str, Any]:
#         pass
#
#
# class LiveMatchInfo(BaseModel):
#     match_id: int = 0
#     radiant_team_name: str = ""
#     dire_team_name: str = ""
#
#
# class LiveMatches(BaseModel, FirestoreDocumentModel):
#     matches: List[LiveMatchInfo] = []
#
#     def dump(self) -> str:
#         return self.model_dump_json()
#
#     @staticmethod
#     def get_doc_id() -> str:
#         return "0"
#
#     def get_attributes(self) -> Dict[str, Any]:
#         return self.model_dump()
#
#
# class GsiEvent(BaseModel, FirestoreDocumentModel):
#     token: str = ""
#     match_id: int = 0
#     timestamp: int = 0
#     clock_time: int = 0
#     game_time: int = 0
#     match_data: str = ""
#
#     def dump(self) -> str:
#         return self.model_dump_json()
#
#     def get_doc_id(self) -> str:
#         return self.token
#
#     def get_attributes(self) -> Dict[str, Any]:
#         return self.model_dump()
#
#
# COLLECTION_MODEL_MAP = {
#     "gsi-events": GsiEvent,
#     "live-matches": LiveMatches
# }
#
#
# class FirestoreDb:
#     client = None
#
#     class Client:
#         def __init__(
#             self,
#             project_id: str = "",
#             collection_name: str = "",
#             database_name: str = "",
#             ttl_sec: int = 3600,
#             *args,
#             **kwargs
#         ):
#             self.project_id = project_id
#             self.database_name = database_name
#             self.collection_name = collection_name
#             self.ttl_sec = ttl_sec
#             # Do not initialize the Firestore client here to avoid pickle issues
#
#         # Lazily initialize Firestore client within methods
#         def _get_fs_client(self):
#             if not hasattr(self, '_fs_client'):
#                 self._fs_client = firestore.Client(
#                     project=self.project_id,
#                     database=self.database_name
#                 )
#             return self._fs_client
#
#         def save_documents(self, docs: List[BaseModel]) -> bool:
#             if not (self.project_id and self.collection_name):
#                 return False
#
#             expire_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_sec)
#
#             batch = self._get_fs_client().batch()
#
#             for doc in docs:
#                 doc_id = doc.get_doc_id()
#                 document_ref = self._get_fs_client().collection(self.collection_name).document(
#                     doc_id
#                 )
#                 document_attributes: Dict[str, Any] = doc.get_attributes()
#
#                 document_attributes["expireAt"] = expire_at
#
#                 batch.set(document_ref, document_attributes, merge=True)
#
#             try:
#                 batch.commit()
#                 res = True
#             except Exception:
#                 res = False
#
#             return res
#
#         def query_document(
#             self,
#             document_id: str,
#             collection_name: str = ""
#         ) -> Union[BaseModel, None]:
#             if not collection_name:
#                 collection_name = self.collection_name
#
#             assert collection_name
#
#             document_ref = self._get_fs_client().collection(collection_name).document(
#                 str(document_id)
#             )
#             document = document_ref.get()
#
#             if document.exists:
#                 model_class = COLLECTION_MODEL_MAP.get(collection_name)
#                 if model_class:
#                     return model_class(**document.to_dict())
#
#             return None
#
#     def __new__(
#         cls,
#         project_id: str = "",
#         collection_name: str = "",
#         database_name: str = "",
#         ttl_sec: int = 3600,
#         *args,
#         **kwargs
#     ):
#         if not cls.client:
#             cls.client = cls.Client(
#                 project_id,
#                 collection_name,
#                 database_name,
#                 ttl_sec,
#                 *args,
#                 **kwargs
#             )
#
#         return cls.client
