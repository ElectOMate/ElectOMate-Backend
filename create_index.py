from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from dotenv import load_dotenv
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    AzureOpenAIModelName,
    SearchField,
    SearchFieldDataType,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmMetric,
    HnswParameters,
    VectorSearch,
    VectorSearchProfile,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer,
    BM25SimilarityAlgorithm,
    SplitSkill,
    SplitSkillLanguage,
    TextSplitMode,
    MergeSkill,
    OcrSkill,
    OcrLineEnding,
    OcrSkillLanguage,
    AzureOpenAIEmbeddingSkill,
    SearchIndexer,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    FieldMapping,
    IndexProjectionMode,
    SearchIndexerIndexProjectionSelector,  
    SearchIndexerIndexProjection,  
    SearchIndexerIndexProjectionsParameters, 
    SearchIndexerSkillset,
    LexicalAnalyzerName,
    IndexingParameters,
    IndexingParametersConfiguration,
    BlobIndexerDataToExtract,
    BlobIndexerImageAction,
    BlobIndexerParsingMode
)
import os
import time

index_name = "ghana-index"
datasource_name = "ghana-data"
container_name = "ghana-files"
skillset_name = "ghana-skillset"
indexer_name = "ghana-indexer"

def create_or_update_sample_index(search_index_client: SearchIndexClient):
    # Create a search index  
    fields = [  
        SearchField(name="parent_id", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),  
        SearchField(name="title", type=SearchFieldDataType.String, filterable=True, sortable=True),  
        SearchField(name="chunk_id", type=SearchFieldDataType.String, key=True, sortable=True, analyzer_name=LexicalAnalyzerName.KEYWORD),  
        SearchField(name="chunk", type=SearchFieldDataType.String, searchable=True, sortable=False, filterable=False, facetable=False),  
        SearchField(name="vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), searchable=True, stored=False, hidden=True, vector_search_dimensions=3072, vector_search_profile_name="hnswProfile"),  
    ]  
    
    # Configure the vector search configuration  
    vector_search = VectorSearch(  
        algorithms=[  
            HnswAlgorithmConfiguration(  
                name="hnsw",
                parameters=HnswParameters(
                    metric=VectorSearchAlgorithmMetric.COSINE,
                    m=4,
                    ef_construction=400,
                    ef_search=500
                )
            )
        ],  
        profiles=[  
            VectorSearchProfile(  
                name="hnswProfile",  
                algorithm_configuration_name="hnsw",  
                vectorizer_name="openai-vectorizer",  
            )
        ],  
        vectorizers=[  
            AzureOpenAIVectorizer(
                vectorizer_name="openai-vectorizer",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    model_name=AzureOpenAIModelName.TEXT_EMBEDDING3_LARGE,
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    deployment_name=AzureOpenAIModelName.TEXT_EMBEDDING3_LARGE
                )
            )
        ]
    )  
    
    semantic_config = SemanticConfiguration(  
        name="semanticConfig",  
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="chunk")]  
        ),  
    )  
    
    # Create the semantic settings with the configuration  
    semantic_search = SemanticSearch(default_configuration_name="semanticConfig", configurations=[semantic_config])

    # Create the search index with the semantic settings  
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search, semantic_search=semantic_search, similarity=BM25SimilarityAlgorithm())  
    search_index_client.create_or_update_index(index)  
    
def create_or_update_datasource(search_indexer_client: SearchIndexerClient):
    storage_resource_id = os.environ["AZURE_STORAGE_ID"]
    data_source = SearchIndexerDataSourceConnection(
        name=datasource_name,
        type="azureblob",
        connection_string=f"ResourceId={storage_resource_id};",
        container=SearchIndexerDataContainer(name=container_name))
    search_indexer_client.create_or_update_data_source_connection(data_source)

def create_or_update_skillset(search_indexer_client: SearchIndexerClient):
    split_skill = SplitSkill(  
        description="Split skill to chunk documents",  
        context="/document",
        maximum_page_length=2000,  
        page_overlap_length=500,
        text_split_mode=TextSplitMode.PAGES,
        default_language_code=SplitSkillLanguage.EN,
        inputs=[  
            # InputFieldMappingEntry(name="text", source="/document/mergedText"),  
            InputFieldMappingEntry(name="text", source="/document/content")
        ],  
        outputs=[  
            OutputFieldMappingEntry(name="textItems", target_name="pages")  
        ],  
    )
    
    merge_skill = MergeSkill(
        description="Merge Skill to combine image text with document text",
        context="/document",
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/content"),
            InputFieldMappingEntry(name="itemsToInsert", source="/document/normalized_images/*/text"),
            InputFieldMappingEntry(name="offsets", source="/document/normalized_images/*/contentOffset")
        ],
        outputs=[
            OutputFieldMappingEntry(name="mergedText", target_name="mergedText")
        ],
        insert_pre_tag=" ",
        insert_post_tag=" "
    )
    
    ocr_skill = OcrSkill(
        description="Reads text from the images",
        context="/document/normalized_images/*",
        inputs=[
            InputFieldMappingEntry(name="image", source="/document/normalized_images/*")
        ],
        outputs=[
            OutputFieldMappingEntry(name="text", target_name="text")
        ],
        default_language_code=OcrSkillLanguage.EN,
        should_detect_orientation=True,
        line_ending=OcrLineEnding.SPACE
    )
    
    embedding_skill = AzureOpenAIEmbeddingSkill(
        description="Skill to generate document embeddings",
        context="/document/pages/*",
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/pages/*")
        ],
        outputs=[
            OutputFieldMappingEntry(name="embedding", target_name="vector")
        ],
        resource_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=AzureOpenAIModelName.TEXT_EMBEDDING3_LARGE,
        model_name=AzureOpenAIModelName.TEXT_EMBEDDING3_LARGE,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        dimensions=3072
    )
    
    index_projections = SearchIndexerIndexProjection(  
        selectors=[  
            SearchIndexerIndexProjectionSelector(  
                target_index_name=index_name,  
                parent_key_field_name="parent_id",  
                source_context="/document/pages/*",  
                mappings=[  
                    InputFieldMappingEntry(name="chunk", source="/document/pages/*"),  
                    InputFieldMappingEntry(name="vector", source="/document/pages/*/vector"),  
                    InputFieldMappingEntry(name="title", source="/document/title"),  
                ],  
            ),  
        ],  
        parameters=SearchIndexerIndexProjectionsParameters(  
            projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS  
        ),  
    )  
    
    skillset = SearchIndexerSkillset(  
        name=skillset_name,  
        description="Skillset to chunk documents and generating embeddings",  
        # skills=[split_skill, merge_skill, embedding_skill, ocr_skill],
        skills=[split_skill, embedding_skill],
        index_projection=index_projections,  
    )
    search_indexer_client.create_or_update_skillset(skillset)
    
def create_or_update_indexer(search_indexer_client: SearchIndexerClient):
    indexer = SearchIndexer(  
        name=indexer_name,  
        description="Indexer to index documents and generate embeddings",  
        skillset_name=skillset_name,  
        target_index_name=index_name,  
        data_source_name=datasource_name,  
        # Map the metadata_storage_name field to the title field in the index to display the PDF title in the search results  
        field_mappings=[FieldMapping(source_field_name="metadata_storage_name", target_field_name="title")],
        parameters=IndexingParameters(
            configuration=IndexingParametersConfiguration(
                data_to_extract=BlobIndexerDataToExtract.CONTENT_AND_METADATA,
                parsing_mode=BlobIndexerParsingMode.DEFAULT,
                image_action=BlobIndexerImageAction.GENERATE_NORMALIZED_IMAGES,
                query_timeout=None
            )
        )
    )  
    
    search_indexer_client.create_or_update_indexer(indexer)
    
def main():
    load_dotenv()
    credential = DefaultAzureCredential()
    credential = AzureKeyCredential(key=os.getenv("AZURE_AI_SEARCH_ADMIN_KEY"))
    search_service_name = os.environ["AZURE_AI_SEARCH_SERVICE_NAME"]
    search_url = f"https://{search_service_name}.search.windows.net"
    search_index_client = SearchIndexClient(endpoint=search_url, credential=credential)
    search_indexer_client = SearchIndexerClient(endpoint=search_url, credential=credential)
    
    print(f"Deleting all resources...")
    search_index_client.delete_index(index_name)
    search_indexer_client.delete_data_source_connection(datasource_name)
    search_indexer_client.delete_skillset(skillset_name)
    search_indexer_client.delete_skillset(indexer_name)
    
    time.sleep(60)

    print(f"Create or update sample index {index_name}...")
    create_or_update_sample_index(search_index_client)

    print(f"Create or update sample data source {datasource_name}...")
    create_or_update_datasource(search_indexer_client)

    print(f"Create or update sample skillset {skillset_name}")
    create_or_update_skillset(search_indexer_client)

    print(f"Create or update sample indexer {indexer_name}")
    create_or_update_indexer(search_indexer_client)
    
if __name__ == "__main__":
    main()