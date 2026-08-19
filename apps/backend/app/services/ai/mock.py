import math
from typing import AsyncGenerator, Dict, List, Optional
from app.services.ai.base import BaseEmbeddingProvider, BaseLLMProvider, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for unit & integration tests."""

    def __init__(self, default_response: str = "This is a grounded academic response based on course material."):
        self.default_response = default_response

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        return LLMResponse(
            content=self.default_response,
            input_tokens=15,
            output_tokens=10
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        words = self.default_response.split(" ")
        for word in words:
            yield word + " "

    async def generate_structured(
        self,
        prompt: str,
        response_schema: dict,
        system_prompt: Optional[str] = None
    ) -> dict:
        return {"status": "success", "mock_data": True}


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic Mock Embedding Provider producing 768-dimensional normalized pseudo vectors."""

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    async def embed_text(self, text: str) -> List[float]:
        # Generate deterministic vector based on text hash
        seed = sum(ord(c) for c in text) if text else 1
        raw_vec = [math.sin(seed + i) for i in range(self.dimension)]
        norm = math.sqrt(sum(x * x for x in raw_vec)) or 1.0
        return [x / norm for x in raw_vec]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_text(t) for t in texts]
