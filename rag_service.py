import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
# v-- CHANGED --v
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
# ^-- CHANGED --^
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables (pulls from your .env file)
load_dotenv()
# We need to manually set this for the Google library
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# --- 1. Load and Index Documents (This runs one time) ---
def create_vector_store():
    """
    Scrapes the Python docs, splits them, and saves them to a local
    FAISS vector store.
    """
    print("Step 1/4: Loading Python docs...")
    loader = WebBaseLoader(
        web_paths=(
            "https://docs.python.org/3/tutorial/",
            "https://docs.python.org/3/library/",
            "https://docs.python.org/3/reference/"
        ),
    )
    docs = loader.load()

    print("Step 2/4: Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    print("Step 3/4: Creating vector store from chunks...")
    # v-- CHANGED --v
    # Use Google's embedding model
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    # ^-- CHANGED --^
    
    vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)

    print("Step 4/4: Saving vector store locally...")
    vectorstore.save_local("faiss_index_python_docs")
    print("--- Vector store created and saved. ---")

# --- 2. Create the Retrieval Chain (The "Brain") ---
def get_retrieval_chain():
    """
    Creates a retrieval chain that links our vector store (retriever)
    to a language model (LLM) and a prompt.
    """
    
    # v-- CHANGED --v
    # Load the local vector store using Google's embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    # ^-- CHANGED --^
    
    vectorstore = FAISS.load_local("faiss_index_python_docs", embeddings, allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever()

    # v-- CHANGED --v
    # Create the language model using Gemini Pro
    llm = ChatGoogleGenerativeAI(model="gemini-pro",
                                 temperature=0.3, 
                                 convert_system_message_to_human=True)
    # ^-- CHANGED --^
    
    # This prompt works great for Gemini as well
    prompt = ChatPromptTemplate.from_template("""
    You are an expert Python programming assistant. Your job is to answer the user's question 
    based *only* on the context provided.
    
    - If the context contains the answer, synthesize a clear and concise response.
    - If the context includes a code example, provide it.
    - If the context does not contain the answer, state clearly that you 
      don't have that information based on the provided documents.
    - Do not make up answers or use external knowledge.

    Context:
    {context}

    Question:
    {input}
    
    Answer:
    """)

    document_chain = create_stuff_documents_chain(llm, prompt)
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    return retrieval_chain

# --- 3. Main function for the Slack bot to call ---
try:
    retrieval_chain = get_retrieval_chain()
    print("Gemini retrieval chain loaded successfully.") # <-- CHANGED
except FileNotFoundError:
    print("Vector store not found. Please run this script directly to create it.")
    retrieval_chain = None
except Exception as e:
    # This will catch API key errors if your .env is wrong
    print(f"An error occurred loading the retrieval chain: {e}") 
    retrieval_chain = None


def get_answer(question: str):
    """
    Gets an answer to a question using the RAG retrieval chain.
    """
    if retrieval_chain is None:
        return "Error: The retrieval chain is not initialized. Please run `python3 rag_service.py` to build the vector store."

    print(f"Invoking Gemini chain with question: {question}") # <-- CHANGED
    start_time = time.time()
    
    response = retrieval_chain.invoke({"input": question})
    
    end_time = time.time()
    print(f"Chain invocation took {end_time - start_time:.2f} seconds.")
    
    return response["answer"]

# --- 4. Main block to create the index ---
if __name__ == "__main__":
    
    if not os.path.exists("faiss_index_python_docs"):
        print("Local vector store not found. Building it now with Google's embeddings...") # <-- CHANGED
        create_vector_store()
    else:
        print("Vector store already exists.")
    
    # Test the function
    print("\n--- Testing RAG Service with Gemini ---") # <-- CHANGED
    test_question = "How do I create a dictionary in Python?"
    print(f"Test Question: {test_question}")
    
    test_answer = get_answer(test_question)
    print(f"Test Answer: {test_answer}")