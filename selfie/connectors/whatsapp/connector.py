from abc import ABC
from typing import Any, List

from selfie.connectors.base_connector import BaseConnector
from selfie.database import BaseModel
from selfie.embeddings import EmbeddingDocumentModel, DataIndex
from selfie.parsers.chat import ChatFileParser
from selfie.types.documents import DocumentDTO
from selfie.utils.data_structures import data_uri_to_dict


class WhatsAppConfiguration(BaseModel):
    files: List[str]


class WhatsAppConnector(BaseConnector, ABC):
    def __init__(self):
        super().__init__()
        self.id = "whatsapp"  # TODO: this should be static
        self.name = "WhatsApp"

    def load_document(self, configuration: dict[str, Any]) -> List[DocumentDTO]:
        config = WhatsAppConfiguration(**configuration)

        return [
            DocumentDTO(
                content=(parsed := data_uri_to_dict(data_uri))['content'],
                content_type=parsed['content_type'],
                name=parsed['name'],
                size=len(parsed['content'].encode('utf-8'))
            )
            for data_uri in config.files
        ]

    def validate_configuration(self, configuration: dict[str, Any]):
        # TODO: check if file can be read from path
        pass

    def transform_for_embedding(self, configuration: dict[str, Any], documents: List[DocumentDTO]) -> List[EmbeddingDocumentModel]:
        return [
            embeddingDocumentModel
            for document in documents
            for embeddingDocumentModel in DataIndex.map_share_gpt_data(
                ChatFileParser().parse_document(
                    document=document.content,
                    parser_type="whatsapp",
                    mask=False,
                    document_name=document.name,
                ).conversations,
                source="whatsapp",
                source_document_id=document.id
            )
        ]
