from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List, Optional


@dataclass
class LLMResponse:
    content: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    raw_response: Optional[Dict] = None


class BaseLLMProvider(ABC):
    """Abstract interface for LLM text generation and structured outputs."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: dict,
        system_prompt: Optional[str] = None
    ) -> dict:
        pass


class BaseEmbeddingProvider(ABC):
    """Abstract interface for generating vector text embeddings."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass
