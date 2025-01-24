import weaviate
from weaviate.connect import ConnectionParams, ProtocolParams
import weaviate.classes as wcs

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from typing import Any, Callable
from pydantic_core import core_schema

import logging

logging.basicConfig(level=logging.DEBUG,  # Set to DEBUG to capture all logs
                    format='%(asctime)s - %(levelname)s - %(message)s')

# TODO: Make async???
class WeaviateClientManager:
    def __init__(self, http_host: str, grcp_host: str, user_api_key: str, openai_api_key: str):
        """
        Initialize the WeaviateClientManager with the URL and optional authentication credentials.

        :param url: The URL of the Weaviate instance.
        :param auth_client_secret: Authentication credentials as a dictionary.
        """
        self.http_host = http_host
        self.grcp_host = grcp_host
        self.user_api_key = user_api_key
        self.openai_api_key = openai_api_key
        self.client = None

    def _connect(self):
        """
        Establish a new Weaviate client connection.
        """
        logging.info("Attempting to establish a Weaviate client connection.")
        try:
            logging.debug(f"HTTP Host: {self.http_host}, GRPC Host: {self.grcp_host}")
            logging.debug("Initializing Weaviate client with provided connection parameters and authentication.")
            self.client = weaviate.WeaviateClient(
                connection_params=ConnectionParams(
                    http=ProtocolParams(
                        host=self.http_host,
                        port=80,
                        secure=False
                    ),
                    grpc=ProtocolParams(
                        host=self.grcp_host,
                        port=50051,
                        secure=False
                    )
                ),
                additional_headers={
                    "X-Azure-Api-Key": self.openai_api_key,
                },
                auth_client_secret=wcs.init.Auth.api_key(api_key=self.user_api_key),
            )
            logging.debug("Attempting to connect the Weaviate client.")
            self.client.connect()
            logging.info("Weaviate client connection established successfully.")
        except Exception as e:
            logging.error(f"Failed to connect to Weaviate: {e}")
            self.client = None

    def get_client(self):
        """
        Return the Weaviate client. Establish a connection if it is non-existent or closed.

        :return: Weaviate client instance.
        """
        if self.client is None or not self._is_connection_alive():
            logging.info("Client is not connected. Establishing connection...")
            self._connect()

        return self.client

    def _is_connection_alive(self):
        """
        Check if the connection to the Weaviate instance is alive.

        :return: True if the connection is alive, False otherwise.
        """
        try:
            if self.client is not None:
                self.client.is_ready()
                return True
        except:
            pass
        return False

    def close_connection(self):
        """
        Close the Weaviate client connection if it exists.
        """
        if self.client is not None:
            try:
                self.client.close()
                logging.info("Weaviate client connection closed.")
            except Exception as e:
                logging.error(f"Failed to close Weaviate client connection: {e}")
            finally:
                self.client = None

    def __del__(self):
        """
        Ensure the connection is closed when the object is destroyed.
        """
        self.close_connection()
    
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Callable[[Any], core_schema.CoreSchema]) -> core_schema.CoreSchema:
        """
        Return a Pydantic core schema for the AzureOpenAIClientManager class.
        This allows Pydantic v2 to treat this class as a pydantic-compatible type,
        enabling validation and schema generation.
        """
        return core_schema.model_schema(
            cls,
            schema=core_schema.model_fields_schema(
                fields={
                    'http_host': core_schema.model_field(core_schema.str_schema()),
                    'grcp_host': core_schema.model_field(core_schema.str_schema()),
                    'user_api_key': core_schema.model_field(core_schema.str_schema())
                }   
            )
        )


class AzureOpenAIClientManager:
    def __init__(self, api_key: str, endpoint: str, api_version: str, chat_deployement: str, embedding_deployement: str):
        """
        Initialize the AzureOpenAIClientManager with the API key and endpoint.

        :param api_key: The Azure OpenAI API key.
        :param endpoint: The Azure OpenAI endpoint.
        """
        self.api_key = api_key
        self.azure_endpoint = endpoint
        self.api_version = api_version
        self.chat_deployement = chat_deployement
        self.embedding_deployement = embedding_deployement
        self.chat_client = None
        self.embedding_client = None

    def _chat_connect(self):
        """
        Establish a new Azure OpenAI client connection.
        """
        logging.info("Attempting to establish a connection to Azure OpenAI chat client.")
        try:
            self.chat_client = AzureChatOpenAI(
                api_key=self.api_key,
                openai_api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                azure_deployment=self.chat_deployement
            )
            logging.info("Azure OpenAI chat client connection established.")
        except Exception as e:
            logging.error(f"Failed to connect to Azure OpenAI: {e}")
            self.chat_client = None
    
    def _embedding_connect(self):
        """
        Establish a new Azure OpenAI embedding client connection.
        """
        logging.info("Attempting to establish a connection to Azure OpenAI embedding client.")
        try:
            self.embedding_client = AzureOpenAIEmbeddings(
                api_key=self.api_key,
                openai_api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                azure_deployment=self.embedding_deployement
            )
            logging.info("Azure OpenAI embedding client connection established.")
        except Exception as e:
            logging.error(f"Failed to connect to Azure OpenAI: {e}")
            self.embedding_client = None

    def get_chat_client(self):
        """
        Return the Azure OpenAI client. Establish a connection if it is non-existent.

        :return: Azure OpenAI client instance.
        """
        if self.chat_client is None:
            logging.info("Chat client is not connected. Establishing connection...")
            self._chat_connect()

        return self.chat_client
    
    def get_embedding_client(self):
        """
        Return the Azure OpenAI client. Establish a connection if it is non-existent.

        :return: Azure OpenAI client instance.
        """
        if self.embedding_client is None:
            logging.info("Embedding client is not connected. Establishing connection...")
            self._embedding_connect()

        return self.embedding_client

    def close_connection(self):
        """
        Close the Azure OpenAI client connection if it exists.
        """
        if self.chat_client is not None:
            self.chat_client = None
            logging.info("Azure OpenAI chat client connection closed.")
        
        if self.embedding_client is not None:
            self.embedding_client = None
            logging.info("Azure OpenAI embedding client connection closed.")

    def __del__(self):
        """
        Ensure the connection is closed when the object is destroyed.
        """
        self.close_connection()
        
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Callable[[Any], core_schema.CoreSchema]) -> core_schema.CoreSchema:
        """
        Return a Pydantic core schema for the AzureOpenAIClientManager class.
        This allows Pydantic v2 to treat this class as a pydantic-compatible type,
        enabling validation and schema generation.
        """
        return core_schema.model_schema(
            cls,
            schema=core_schema.model_fields_schema(
                fields={
                'api_key': core_schema.model_field(core_schema.str_schema()),
                'azure_endpoint': core_schema.model_field(core_schema.str_schema()),
                'api_version': core_schema.model_field(core_schema.str_schema()),
                'chat_deployement': core_schema.model_field(core_schema.str_schema()),
                'embedding_deployement': core_schema.model_field(core_schema.str_schema())
            }
            )
        )


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    import pathlib
    envfile = pathlib.Path(__file__).resolve().parent.parent / '.env'
    load_dotenv(str(envfile))
    client = weaviate.WeaviateClient(
        connection_params=ConnectionParams(
            http=ProtocolParams(
                host=os.getenv('WEAVIATE_HTTP_HOST'),
                port=80,
                secure=False
            ),
            grpc=ProtocolParams(
                host=os.getenv('WEAVIATE_GRCP_HOST'),
                port=50051,
                secure=False
            )
        ),
        auth_client_secret=wcs.init.Auth.api_key(api_key=os.getenv('WEAVIATE_USER_API_KEY')),
    )
    client.connect()
    client.close()