import instructor
import numpy as np

from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langsmith import traceable, get_current_run_tree     # langsmith 可观测平台: 追踪有 @traceable 标签的函数

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType, PointStruct, SparseVectorParams, Document, Prefetch, FusionQuery


load_dotenv()
client = OpenAI()
qdrant_client = QdrantClient(url="http://qdrant:6333/")
instructor_client = instructor.from_openai(OpenAI())


# 数据模型 (数据结构) → 结构化输出
class RAGUsedContext(BaseModel):
    id: str = Field(description="The ID of the item used to answer the question")
    description: str = Field(description="Short description of the item used to answer the question")
 
class RAGGenerationResponse(BaseModel):
    answer: str = Field(description="The answer to the question")
    references: list[RAGUsedContext] = Field(description="List of items used to answer the question")


# RAG pipeline RAG 处理流程函数 
@traceable(
    name="embed_query",
    run_type="embedding",
    metadata={"ls_provider": "openai", "ls_model_name": "text-embedding-3-small"}
)
def get_embedding(text, model="text-embedding-3-small"):
    response = client.embeddings.create(
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


@traceable(
    name="retrieve_data",
    run_type="retriever"
)
def retrieve_data(query, qdrant_client, k=5):

    query_embedding = get_embedding(query)
    
    results = qdrant_client.query_points(
        collection_name="Amazon-items-collection-01-hybrid-search",
        prefetch=[
            Prefetch(
                query=query_embedding,
                using="text-embedding-3-small",
                limit=20
            ),
            Prefetch(
                query=Document(
                    text=query,
                    model="qdrant/bm25"
                ),
                using="bm25",
                limit=20
            )
        ],
        query=FusionQuery(fusion="rrf"),
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
def process_context(context):
    formatted_context=""

    for id, chunk, rating in zip(
        context["retrieved_context_ids"], 
        context["retrieved_context"], 
        context["retrieved_context_ratings"]
    ):
        formatted_context += f"- ID: {id}, rating: {rating}, description: {chunk}\n"

    return formatted_context


@traceable(
    name="build_prompt",
    run_type="prompt"
)
def build_prompt(preprocessed_context, question):
    prompt = f"""
You are a shopping assistant that can answer questions about the products in stock.

You will be given a question and a list of context.

Instructions:
- You need to answer the question based on the provided context only.
- Never use word context and refer to it as the available products.
- As an output you need to provide:

* The answer to the question based on the provided context.
* The list of the IDs of the chunks that were used to answer the question. Only return the ones that are used in the answer.
* Short description (1-2 sentences) of the item based on the description provided in the context.

- The short description should have the name of the item.
- The answer to the question should contain detailed information about the product and returned with detailed specification in bullet points.

Context:
{preprocessed_context}

Question:
{question}
"""

    return prompt


@traceable(
    name="generate_answer",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-4.1-mini"}
)
def generate_answer(prompt):
    response, raw_response = instructor_client.chat.completions.create_with_completion(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": prompt}],
        temperature=0,
        response_model=RAGGenerationResponse
    )

    # langsmith 监控 tokens 消耗情况
    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"]={
            "input_tokens": raw_response.usage.prompt_tokens,
            "output_tokens": raw_response.usage.completion_tokens,
            "total_tokens": raw_response.usage.total_tokens,
        }

    return response


@traceable(
    name="rag_pipeline"
)
def rag_pipeline(question, qdrant_client, top_k=5):

    retrieved_context = retrieve_data(question, qdrant_client, top_k)
    preprocessed_context = process_context(retrieved_context)
    prompt = build_prompt(preprocessed_context, question)
    answer = generate_answer(prompt)

    final_result = {
        "answer": answer.answer,
        "references": answer.references,
        "question": question,
        "retrieved_context_ids": retrieved_context["retrieved_context_ids"],
        "retrieved_context": retrieved_context["retrieved_context"],
        "similarity_scores": retrieved_context["similarity_scores"]
    }
    return final_result
    

def rag_pipeline_wrapper(question, top_k=5):
    
    result = rag_pipeline(question, qdrant_client, top_k)
    
    # 通过 LLM 查询得到的商品 ID ，再一次去数据库查详细信息
    # -- 第一次数据库查询: Embedding Similarity
    # -- 第二次数据库查询: 通过已获得的 parent_asin 商品 ID 回数据库检索详细信息
    used_context = []                                       # 存储检索数据
    dummy_vector = np.zeros(1536).tolist()
    for item in result.get("references", []):
        payload = qdrant_client.query_points(               # 向量数据库检索
            collection_name="Amazon-items-collection-01-hybrid-search",
            query=dummy_vector,
            limit=1,
            using="text-embedding-3-small",
            with_payload=True,
            query_filter=Filter(                            # 检索条件
                must=[
                    FieldCondition(
                        key="parent_asin",                  
                        match=MatchValue(value=item.id)
                    )
                ]
            )
        ).points[0].payload

        image_url = payload.get("image")                    # 检索结果
        price = payload.get("price")
        if image_url:
            used_context.append({
                "image_url": image_url,
                "price": price,
                "description": item.description
            })
    
    return {
        "answer": result["answer"],
        "used_context": used_context
    }
