import os
from typing import AsyncGenerator, Dict, List, Optional
from app.services.ai.base import BaseEmbeddingProvider, BaseLLMProvider, LLMResponse


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini LLM provider implementation."""

    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = model_name

    def _ensure_api_key(self):
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in environment variables.")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        self._ensure_api_key()
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            
            config = {"temperature": temperature}
            if system_prompt:
                config["system_instruction"] = system_prompt

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", None) if hasattr(response, "usage_metadata") else None
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", None) if hasattr(response, "usage_metadata") else None

            return LLMResponse(
                content=response.text or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Gemini API generation failed: {str(e)}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        self._ensure_api_key()
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            config = {"temperature": temperature}
            if system_prompt:
                config["system_instruction"] = system_prompt

            response_stream = client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Gemini streaming failed: {str(e)}")

    async def generate_structured(
        self,
        prompt: str,
        response_schema: dict,
        system_prompt: Optional[str] = None
    ) -> dict:
        self._ensure_api_key()
        import json
        resp = await self.generate(prompt, system_prompt, temperature=0.1)
        try:
            return json.loads(resp.content)
        except Exception:
            raise ValueError(f"Failed to parse structured JSON response from Gemini: {resp.content}")


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini Embedding provider (text-embedding-004, 768 dimensions)."""

    def __init__(self, model_name: str = "text-embedding-004"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.dimension = 768

    def _ensure_api_key(self):
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in environment variables.")

    async def embed_text(self, text: str) -> List[float]:
        batch_res = await self.embed_batch([text])
        return batch_res[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        self._ensure_api_key()
        if not texts:
            return []
            
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            res = client.models.embed_content(
                model=self.model_name,
                contents=texts
            )
            embeddings = [e.values for e in res.embeddings]
            return embeddings
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Gemini embedding API failed: {str(e)}")
