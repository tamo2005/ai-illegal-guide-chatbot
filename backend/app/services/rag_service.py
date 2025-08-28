import json
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.vectorstores import Qdrant
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue

from app.config.settings import settings

class RAGService:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in the environment variables.")

        # 1. Initialize Google's LLM and Embedding models
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=settings.GOOGLE_API_KEY, convert_system_message_to_human=True)
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=settings.GOOGLE_API_KEY)
        
        # 2. Initialize Qdrant Client for vector database
        self.qdrant_client = QdrantClient(":memory:") # Using in-memory for hackathon simplicity
        self.collection_name = "knowledge_base_collection"
        
        # 3. Load data and build the vector store upon initialization
        self._load_and_build_vector_store()

        # 4. Create the prompt template and the final chain
        self._create_llm_chain()

    def _load_and_build_vector_store(self):
        # Create Qdrant collection if it doesn't exist
        self.qdrant_client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE), # 768 is the dimension for Google's embedding model
        )

        # Load data from our JSON knowledge base
        with open('app/data/sources/hacks.json', 'r', encoding='utf-8') as f:
            self.knowledge_base = json.load(f)

        # Prepare documents and metadata for embedding
        contents = [item['content'] for item in self.knowledge_base]
        
        # Add embeddings to the collection
        self.qdrant_client.add(
            collection_name=self.collection_name,
            documents=contents,
            metadatas=self.knowledge_base,
            ids=list(range(len(self.knowledge_base))) # Simple sequential IDs
        )
        print("Knowledge base loaded and indexed in Qdrant successfully.")

    def _create_llm_chain(self):
        # This prompt is engineered to make the AI behave exactly as we want.
        prompt_template = """
        You are an AI assistant named 'Jugaad Navigator', designed to help users navigate administrative challenges in India.
        Your tone should be helpful, empathetic, but also cautious and responsible.
        You MUST follow these rules:
        1. Base your answer ONLY on the information provided in the 'CONTEXT' section. Do not use any external knowledge.
        2. Start your response by directly addressing the user's question.
        3. After the main answer, you MUST include a "Risk Assessment" section. This section must contain the 'Risk Level' exactly as provided in the context.
        4. If the provided context is not relevant to the question, you must reply: "I'm sorry, I don't have specific information on that topic. My expertise is in common workarounds for administrative tasks in India."

        CONTEXT:
        {context}

        USER'S QUESTION:
        {question}

        YOUR RESPONSE:
        """
        prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        self.chain = LLMChain(llm=self.llm, prompt=prompt)

    def ask(self, query_text: str, location: str = None):
        # Embed the user's query to find similar documents
        query_embedding = self.embeddings.embed_query(query_text)

        # Search the vector database for relevant context
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=1 # We only need the single most relevant piece of context
        )

        if not search_results:
            return {"answer": "I couldn't find any relevant information.", "confidence": 0.0, "risk": {}, "sources": []}

        # Extract the best result
        best_result = search_results[0]
        context_data = best_result.payload
        context_text = context_data['content']

        # Run the LLM chain with the retrieved context
        response = self.chain.invoke({
            "context": context_text,
            "question": query_text
        })
        
        # Prepare final structured output
        final_response = {
            "answer": response['text'],
            "confidence": best_result.score,
            "risk": {"overall_risk": context_data.get('risk_level', 'unknown')},
            "sources": [context_data]
        }
        return final_response

# Create a single instance of the service to be used across the app
rag_service = RAGService()