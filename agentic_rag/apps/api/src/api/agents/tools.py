from openai import OpenAI
from dotenv import load_dotenv

from langsmith import traceable, get_current_run_tree     # langsmith 可观测平台: 追踪有 @traceable 标签的函数

from qdrant_client import QdrantClient
from qdrant_client.models import Document, Prefetch, FusionQuery
from qdrant_client.models import MatchAny, FieldCondition, Filter


load_dotenv()
openai_client = OpenAI()
qdrant_client = QdrantClient(url="http://qdrant:6333/")


# embedding 处理函数 
@traceable(
    name="embed_query",
    run_type="embedding",
    metadata={"ls_provider": "openai", "ls_model_name": "text-embedding-3-small"}
)
def get_embedding(text, model="text-embedding-3-small"):
    response = openai_client.embeddings.create(
        input=text,
        model=model,
    )

    # langsmith 监控 tokens 消耗情况
    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"]={
            "input_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return response.data[0].embedding


### Items Description Retrieval Tool ###
@traceable(
    name="retrieve_data",
    run_type="retriever"
)
def retrieve_items_data(query, k=5):

    query_embedding = get_embedding(query)
    
    results = qdrant_client.query_points(
        collection_name="Amazon-items-collection-01-hybrid-search",

        # 混合检索 hybrid search
        prefetch=[
            Prefetch(                   # Embedding 语义检索
                query=query_embedding,
                using="text-embedding-3-small",
                limit=20
            ),
            Prefetch(                   # BM25 关键词检索
                query=Document(
                    text=query,
                    model="qdrant/bm25"
                ),
                using="bm25",
                limit=20
            )
        ],
        query=FusionQuery(fusion="rrf"),    # 把两个排序融合
        limit=k,
    )

    retrieved_context_ids = []
    retrieved_context = []
    retrieved_context_ratings = []
    similarity_scores = []
    
    for result in results.points:
        retrieved_context_ids.append(result.payload["parent_asin"])
        retrieved_context.append(result.payload["description"])
        retrieved_context_ratings.append(result.payload["average_rating"])
        similarity_scores.append(result.score)

    return {
        "retrieved_context_ids": retrieved_context_ids,
        "retrieved_context": retrieved_context,
        "retrieved_context_ratings": retrieved_context_ratings,
        "similarity_scores": similarity_scores,
    }


@traceable(
    name="format_retrieved_context",
    run_type="prompt"
)
def process_items_context(context):
    formatted_context=""

    for id, chunk, rating in zip(
        context["retrieved_context_ids"], 
        context["retrieved_context"], 
        context["retrieved_context_ratings"]
    ):
        formatted_context += f"- ID: {id}, rating: {rating}, description: {chunk}\n"

    return formatted_context


# RAG 商品信息检索工具
# RAG 流程封装为工具函数，供 Agent 调用
def get_formatted_items_context(query: str, top_k: int = 5) -> str:

    """Get the top k context,each representing an inventory item for a given query.

    Args:
        query: The query to get the top k context for
        top_k: The number of context chunks to retrieve, works best with 5 or more
    
    Returns:
        A string of the top k context chunks with IDs and average ratings prepending each chunk, each representing an inventory item for a given query.
    """
    
    context = retrieve_items_data(query, top_k)
    formatted_context = process_items_context(context)

    return formatted_context


### Items Reviews Retrieval Tool ###
@traceable(
    name="retrieve_reviews_data",
    run_type="retriever"
)
def retrieve_reviews_data(query, item_list,k=5):

    query_embedding = get_embedding(query)
    
    results = qdrant_client.query_points(
        collection_name="Amazon-items-collection-01-reviews",
        prefetch=[
            Prefetch(
                query=query_embedding,
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="parent_asin",
                            match=MatchAny(
                                any=item_list
                            )
                        )
                    ]
                ),
                limit=20
            )
        ],
        query=FusionQuery(fusion="rrf"),
        limit=k
    )

    retrieved_context_ids = []
    retrieved_context = []
    similarity_scores = []
    
    for result in results.points:
        retrieved_context_ids.append(result.payload["parent_asin"])
        retrieved_context.append(result.payload["text"])
        similarity_scores.append(result.score)

    return {
        "retrieved_context_ids": retrieved_context_ids,
        "retrieved_context": retrieved_context,
        "similarity_scores": similarity_scores,
    }


@traceable(
    name="format_retrieved_reviews_context",
    run_type="prompt"
)
def process_reviews_context(context):
    formatted_context=""

    for id, chunk in zip(
        context["retrieved_context_ids"], 
        context["retrieved_context"], 
    ):
        formatted_context += f"- ID: {id}, review: {chunk}\n"

    return formatted_context


# RAG 商品评论检索工具
# RAG 流程封装为工具函数，供 Agent 调用
def get_formatted_reviews_context(query: str, item_list: list, top_k: int = 15) -> str:

    """Get the top k reviews matching a query for a List of prefiltered items.

    Args:
        query: The query to get the top k reviews for
        item_list: The list of item IDs to prefilter for before running the query
        top_k: The number of reviews to retrieve, this should be at least 2e if multiple items are prefiltered

    Returns:
        A string of the top k context chunks with IDs prepending each chunk, each representing a review for a given inventory item for a given query.
    """
    
    context = retrieve_reviews_data(query, item_list, top_k)
    formatted_context = process_reviews_context(context)

    return formatted_context