# RAG evaluation (old version: have issues)
from openai import OpenAI
from dotenv import load_dotenv

from langsmith import Client            # langsmith: 存储有参考数据集, 包括 问题 + 标准答案
from qdrant_client import QdrantClient

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

# ragas: RAG 评估框架
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import IDBasedContextPrecision, IDBasedContextRecall, Faithfulness, ResponseRelevancy

from api.agents.retrieval_generation import rag_pipeline


load_dotenv()
ls_client = Client()
openai_client = OpenAI()
qdrant_client = QdrantClient(url="http://localhost:6333/")

ragas_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4.1-mini"))
ragas_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))


# 评估函数
async def ragas_faithfulness(run, example):
    """Faithfulness 忠实度评估: 生成的回答有没有瞎编 (是否基于检索到的上下文)"""
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        retrieved_contexts=run["retrieved_context"]
    )
    scorer = Faithfulness(llm=ragas_llm)

    return await scorer.single_turn_ascore(sample)

async def ragas_response_relevancy(run, example):
    """Response Relevancy 回答相关性评估: 回答跟问题相关吗"""
    sample = SingleTurnSample(
        user_input=run["question"],
        response=run["answer"],
        retrieved_contexts=run["retrieved_context"]
    )
    scorer = ResponseRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)
    
    return await scorer.single_turn_ascore(sample)

async def ragas_context_precision_id_based(run, example):
    """Context Precision 上下文精确率评估: 检索出来的 5 个商品里，有多少个是真正有用的 (与标准答案对比)"""
    sample = SingleTurnSample(
        retrieved_context_ids=run["retrieved_context_ids"],
        reference_context_ids=example["reference_context_ids"]
    )
    scorer = IDBasedContextPrecision()
    
    return await scorer.single_turn_ascore(sample)

async def ragas_context_recall_id_based(run, example):
    """Context Recall 上下文召回率评估: 标准答案里需要的 5 个商品，检索系统找回了多少个"""
    sample = SingleTurnSample(
        retrieved_context_ids=run["retrieved_context_ids"],
        reference_context_ids=example["reference_context_ids"]
    )
    scorer = IDBasedContextRecall()

    return await scorer.single_turn_ascore(sample)


# langsmith 对参考数据集执行评估
results = ls_client.evaluate(
    lambda x: rag_pipeline(x["question"], qdrant_client),
    data="rag-evaluation-dataset",
    evaluators=[
        ragas_faithfulness,
        ragas_response_relevancy,
        ragas_context_precision_id_based,
        ragas_context_recall_id_based
    ],
    experiment_prefix="retriever",      
    max_concurrency=10,
)
