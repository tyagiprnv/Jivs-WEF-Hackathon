from sentence_transformers import SentenceTransformer
from openai import OpenAI
import chromadb
from typing import List, Dict
import os
import ast
import re

api_key = os.getenv("OPENAI_API_KEY")

class SemanticSearch:
    def __init__(self, persist_dir: str = "chroma_db"):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_collection(name="views")
    
    def find_relevant_views(self, query: str, top_k: int = 2) -> List[Dict]:
        query_embedding = self.model.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )

        relevant_views = []
        if results and results.get("metadatas") and results["metadatas"][0]:
            for i in range(len(results["ids"][0])):
                view_name = results["metadatas"][0][i].get("view_name")
                fields_str = results["metadatas"][0][i].get("fields")
                if view_name and fields_str:
                    try:
                        fields = ast.literal_eval(fields_str)
                        relevant_views.append({
                            "view_name": view_name,
                            "fields": fields
                        })
                    except (ValueError, SyntaxError) as e:
                        print(f"Error parsing fields: {e}")
        else:
            print("No relevant views found or metadata is missing.")

        return relevant_views


class JIVSChatbot:
    def __init__(self, search_system: SemanticSearch):
        self.search_system = search_system
        self.llm = OpenAI(api_key=api_key)
        self.conversation = [{"role": "system", "content": """You are a SQL expert and a helpful assistant for the JIVS system. 
                Your task is to help users find the correct view and generate a URL to access it. 
                If you are unsure about the user's query, ask clarifying questions. 
                Only generate the URL when you are confident about the correct view."""}]
    
    def generate_response(self, query: str) -> str:
        relevant_views = self.search_system.find_relevant_views(query)
        
        prompt = f"""User query: {query}
        
        Available views:
        {[v['view_name'] for v in relevant_views]}
        
        Fields in views:
        {[v['fields'] for v in relevant_views]}
        
        Determine the correct view and required parameters. 
        If you are unsure, ask clarifying questions. 
        Only generate the URL if you are confident about the correct view."""
        
        print(prompt)
        
        self.conversation.append({"role": "user", "content": prompt})
        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",  
            messages=self.conversation
        )
        response_content = response.choices[0].message.content

        self.conversation.append({"role": "assistant", "content": response_content})

        return response_content
    
    def generate_url(self, view_name: str) -> str:
        return f"https://wef2025.cloud.jivs.com/jivs/getSearchForm.do?viewName={view_name}&packageName=sap.ecc60kjl"

    def extract_view_name(self, response: str) -> str:
        match = re.search(r"\.([A-Za-z0-9]+)\.", response) 
        if match:
            return match.group(1)  
        return None


def main():
    search_system = SemanticSearch()
    chatbot = JIVSChatbot(search_system)
    
    print("Welcome to the JIVS Chatbot! Type 'exit' to quit.")
    while True:
        query = input("\nYour query: ")
        if query.lower() == "exit":
            break
        
        response = chatbot.generate_response(query)
        print("\nChatbot:", response)
        
        if "view" in response.lower() and "confident" in response.lower():
            view_name = chatbot.extract_view_name(response)
            if view_name:
                url = chatbot.generate_url(view_name)
                print("Generated URL:", url)
            else:
                print("Could not extract a valid view name from the response.")
        else:
            print("The chatbot is unsure. Please provide more details or clarify your query.")

if __name__ == "__main__":
    main()