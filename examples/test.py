import os
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete
from lightrag.kg.shared_storage import initialize_pipeline_status
#########
# Uncomment the below two lines if running in a jupyter notebook to handle the async nature of rag.insert()
# import nest_asyncio
# nest_asyncio.apply()
#########

WORKING_DIR = "./dickens"

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)


async def initialize_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=gpt_4o_mini_complete,  # Use gpt_4o_mini_complete LLM model
        # llm_model_func=gpt_4o_complete  # Optionally, use a stronger model
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()

    return rag


def main():
    # Initialize RAG instance
    rag = asyncio.run(initialize_rag())

    with open("./book.txt", "r", encoding="utf-8") as f:
        rag.insert(f.read())

    # Perform naive search
    print(
        rag.query(
            "What are the top themes in this story?", param=QueryParam(mode="naive")
        )
    )

    # Perform local search
    print(
        rag.query(
            "What are the top themes in this story?", param=QueryParam(mode="local")
        )
    )

    # Perform global search
    print(
        rag.query(
            "What are the top themes in this story?", param=QueryParam(mode="global")
        )
    )

    # Perform hybrid search
    print(
        rag.query(
            "What are the top themes in this story?", param=QueryParam(mode="hybrid")
        )
    )


if __name__ == "__main__":
    main()
