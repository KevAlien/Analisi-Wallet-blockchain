"""
OpenAI provider implementation
"""
import json
import time
import logging
from typing import Dict, Any, Optional

from ..llm_interface import LLMInterface

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMInterface):
    """
    Provider for OpenAI API

    Requires API key from https://platform.openai.com/
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        timeout: int = 120
    ):
        """
        Initialize OpenAI provider

        Args:
            api_key: OpenAI API key
            model: Model identifier (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using OpenAI API"""
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

        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "content": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "model": self.model,
                "finish_reason": response.choices[0].finish_reason,
                "latency_ms": latency_ms
            }

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise Exception(f"OpenAI API error: {str(e)}")

    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON output"""
        # OpenAI supports response_format for JSON mode
        json_instruction = f"""
RESPOND ONLY with a valid JSON object that matches this schema:

{json.dumps(schema, indent=2)}

Do not include any markdown formatting, code blocks, or explanations.
Only output the raw JSON object.
"""

        full_prompt = f"{prompt}\n\n{json_instruction}"

        # Use JSON mode if available
        extra_kwargs = kwargs.copy()
        if "gpt-4" in self.model or "gpt-3.5" in self.model:
            extra_kwargs["response_format"] = {"type": "json_object"}

        response = await self.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            **extra_kwargs
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
        """Check if OpenAI API is accessible"""
        return self.api_key is not None and self.client is not None

    def get_context_window(self) -> int:
        """Get context window size"""
        if "gpt-4o" in self.model:
            return 128000
        elif "gpt-4-turbo" in self.model:
            return 128000
        elif "gpt-4" in self.model:
            return 8192
        elif "gpt-3.5-turbo" in self.model:
            return 16385
        return 8192

    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"openai ({self.model})"

    async def close(self):
        """Close client"""
        if hasattr(self.client, 'close'):
            await self.client.close()
