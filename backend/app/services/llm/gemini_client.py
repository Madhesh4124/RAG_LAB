"""Gemini LLM Client."""

import os
from typing import Any, Dict, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.chunking.base import Chunk

load_dotenv(override=True)

class GeminiClient:
    """Gemini Client using LangChain's ChatGoogleGenerativeAI."""

    def __init__(self, model: str = "gemini-2.5-flash", temperature: float = 0.2):
        self.provider = "google"
        self.model_name = model
        self.temperature = temperature
        
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            import logging
            logging.warning(
                "Neither GEMINI_API_KEY nor GOOGLE_API_KEY is set. "
                "LLM features will be unavailable."
            )
            self.llm = None
            return
            
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=api_key
        )

    def generate(self, query: str, chunks: List[Chunk]) -> str:
        """Generate response based on query and context chunks."""
        if not self.llm:
            raise RuntimeError(
                "LLM client not initialized. GEMINI_API_KEY/GOOGLE_API_KEY is missing."
            )
            
        chunks_text = "\n---\n".join([chunk.text for chunk in chunks])
        prompt = f"Answer based on context: {chunks_text}\n\nQuestion: {query}"
        
        response = self.llm.invoke(prompt)
        # LangChain's AIMessage object has a .content string
        return response.content

    def generate_with_memory(self, query: str, chunks: List[Chunk], context: str) -> str:
        """Generate response based on query, context chunks, and conversation history."""
        if not self.llm:
            raise RuntimeError(
                "LLM client not initialized. GEMINI_API_KEY/GOOGLE_API_KEY is missing."
            )
            
        chunks_text = "\n---\n".join([chunk.text for chunk in chunks])
        prompt = f"Conversation History:\n{context}\n\nAnswer based on context: {chunks_text}\n\nQuestion: {query}"
        
        response = self.llm.invoke(prompt)
        return response.content

    def get_config(self) -> Dict[str, Any]:
        """Return the client configuration."""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "temperature": self.temperature,
        }
