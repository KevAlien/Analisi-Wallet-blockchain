"""
LMStudio provider implementation
LMStudio exposes OpenAI-compatible API at localhost:1234
"""
import httpx
import json
import time
import logging
from typing import Dict, Any, Optional

from ..llm_interface import LLMInterface

logger = logging.getLogger(__name__)


class LMStudioProvider(LLMInterface):
    """
    Provider for LMStudio local LLM server

    LMStudio runs models locally and exposes OpenAI-compatible API
    Default endpoint: http://localhost:1234/v1
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model_name: str = "local-model",
        timeout: int = 120
    ):
        """
        Initialize LMStudio provider

        Args:
            base_url: LMStudio API base URL
            model_name: Model identifier
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
        """Generate response using LMStudio"""
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **kwargs
        }

        start_time = time.time()

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)
            result = response.json()

            return {
                "content": result["choices"][0]["message"]["content"],
                "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                "model": self.model_name,
                "finish_reason": result["choices"][0].get("finish_reason", "stop"),
                "latency_ms": latency_ms
            }

        except httpx.HTTPError as e:
            logger.error(f"LMStudio API error: {str(e)}")
            raise Exception(f"LMStudio API error: {str(e)}")
        except Exception as e:
            logger.error(f"LMStudio unexpected error: {str(e)}")
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

        # Use low temperature for structured output
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

            # Parse JSON
            parsed = json.loads(content)
            response["parsed_json"] = parsed

            return response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {str(e)}")
            logger.error(f"Content: {response['content']}")
            raise Exception(f"Failed to parse JSON from LLM: {str(e)}")

    def is_available(self) -> bool:
        """Check if LMStudio server is reachable"""
        try:
            response = httpx.get(f"{self.base_url}/models", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_context_window(self) -> int:
        """Get context window size"""
        # Most modern models have at least 8k context
        # This could be queried from LMStudio API in future versions
        return 8192

    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"lmstudio ({self.model_name})"

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
