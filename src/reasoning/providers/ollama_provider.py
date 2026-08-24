"""
Ollama provider implementation
"""
import httpx
import json
import time
import logging
from typing import Dict, Any, Optional

from ..llm_interface import LLMInterface

logger = logging.getLogger(__name__)


class OllamaProvider(LLMInterface):
    """
    Provider for Ollama local LLM server

    Ollama runs models locally and exposes REST API
    Default endpoint: http://localhost:11434
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3.1:8b",
        timeout: int = 120
    ):
        """
        Initialize Ollama provider

        Args:
            base_url: Ollama API base URL
            model_name: Model identifier (e.g., llama3.1:8b, mistral:7b)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using Ollama"""
        # Ollama uses different API format than OpenAI
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"<|system|>\n{system_prompt}\n\n<|user|>\n{prompt}"

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        start_time = time.time()

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)
            result = response.json()

            return {
                "content": result["response"],
                "tokens_used": result.get("eval_count", 0) + result.get("prompt_eval_count", 0),
                "model": self.model_name,
                "finish_reason": "stop" if result.get("done") else "length",
                "latency_ms": latency_ms
            }

        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise Exception(f"Ollama API error: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama unexpected error: {str(e)}")
            raise

    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output"""
        json_instruction = f"""
RESPOND ONLY with a valid JSON object that matches this schema:

{json.dumps(schema, indent=2)}

Do not include any markdown formatting, code blocks, or explanations.
Only output the raw JSON object.
"""

        full_prompt = f"{prompt}\n\n{json_instruction}"

        response = await self.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            **kwargs
        )

        # Parse JSON from response
        try:
            content = response["content"].strip()

            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            response["parsed_json"] = parsed

            return response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {str(e)}")
            logger.error(f"Content: {response['content']}")
            raise Exception(f"Failed to parse JSON from LLM: {str(e)}")

    def is_available(self) -> bool:
        """Check if Ollama server is reachable"""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_context_window(self) -> int:
        """Get context window size"""
        # Most Ollama models have 8k+ context
        # Could be queried from model info in future
        return 8192

    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"ollama ({self.model_name})"

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
