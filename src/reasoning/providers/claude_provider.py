"""
Claude (Anthropic) provider implementation
"""
import json
import time
import logging
from typing import Dict, Any, Optional

from ..llm_interface import LLMInterface

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMInterface):
    """
    Provider for Anthropic Claude API

    Requires API key from https://console.anthropic.com/
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        timeout: int = 120
    ):
        """
        Initialize Claude provider

        Args:
            api_key: Anthropic API key
            model: Claude model identifier
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=api_key, timeout=timeout)
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using Claude API"""
        start_time = time.time()

        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "content": response.content[0].text,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "model": self.model,
                "finish_reason": response.stop_reason,
                "latency_ms": latency_ms
            }

        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise Exception(f"Claude API error: {str(e)}")

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
        """Check if Claude API is accessible"""
        # Simple check - API key exists and client is initialized
        return self.api_key is not None and self.client is not None

    def get_context_window(self) -> int:
        """Get context window size"""
        # Claude 3.5 Sonnet has 200k context window
        if "claude-3-5" in self.model or "claude-3" in self.model:
            return 200000
        return 100000

    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"claude ({self.model})"

    async def close(self):
        """Close client"""
        if hasattr(self.client, 'close'):
            await self.client.close()
