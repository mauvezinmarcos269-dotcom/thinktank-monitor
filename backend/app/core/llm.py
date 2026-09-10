import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SiliconFlowClient:
    """
    SiliconFlow OpenAI Compatible API Client。

    一个 SiliconFlowClient 实例持有一个可复用的
    httpx.AsyncClient。

    同一个报告的 translation / summary / commentary
    可以共享底层 HTTP 连接池。
    """

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        self.timeout = httpx.Timeout(
            connect=settings.LLM_CONNECT_TIMEOUT_SECONDS,
            read=settings.LLM_READ_TIMEOUT_SECONDS,
            write=settings.LLM_WRITE_TIMEOUT_SECONDS,
            pool=settings.LLM_POOL_TIMEOUT_SECONDS,
        )

        self.limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=30.0,
        )

        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
        )

        self._closed = False

    def _validate_config(self) -> None:
        """
        校验 LLM 配置。
        """
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")

        if not self.base_url:
            raise ValueError("LLM_BASE_URL 未配置")

        if not self.model:
            raise ValueError("LLM_MODEL 未配置")

    async def chat(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1200,
        response_format_json: bool = True,
    ) -> str:
        """
        调用 SiliconFlow OpenAI Compatible API。

        同一个 SiliconFlowClient 实例会复用
        self.client 对应的 HTTP 连接池。
        """
        self._validate_config()

        if self._closed:
            raise RuntimeError(
                "SiliconFlowClient 已关闭，无法继续发送请求"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一名专业的国际关系与智库研究分析助手。"
                        "你必须严格遵守用户要求。"
                        "如果要求返回 JSON，只能返回合法 JSON。"
                        "不得输出 Markdown、解释文字或其他内容。"
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format_json:
            payload["response_format"] = {
                "type": "json_object"
            }

        logger.info(
            "Calling SiliconFlow: model=%s, prompt_len=%s, max_tokens=%s",
            self.model,
            len(prompt),
            max_tokens,
        )

        try:
            response = await self.client.post(
                self.base_url,
                headers=headers,
                json=payload,
            )

            logger.info(
                "SiliconFlow response: status=%s, elapsed=%.2fs",
                response.status_code,
                response.elapsed.total_seconds(),
            )

            response.raise_for_status()

        except httpx.TimeoutException:
            logger.exception(
                "SiliconFlow request timeout: model=%s",
                self.model,
            )
            raise

        except httpx.HTTPError:
            logger.exception(
                "SiliconFlow HTTP request failed: model=%s",
                self.model,
            )
            raise

        try:
            data = response.json()

        except ValueError as exc:
            logger.error(
                "SiliconFlow returned invalid JSON: %s",
                response.text[:1000],
            )

            raise ValueError(
                "SiliconFlow 返回的 HTTP 响应不是有效 JSON"
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            logger.error(
                "Unexpected SiliconFlow response: %s",
                data,
            )

            raise ValueError(
                f"SiliconFlow 返回格式异常: {data}"
            ) from exc

        if not isinstance(content, str):
            raise ValueError(
                f"LLM 返回内容类型异常: {type(content)}"
            )

        return content.strip()

    async def close(self) -> None:
        """
        关闭底层 HTTP Client 并释放连接池资源。

        允许重复调用，不会重复关闭。
        """
        if self._closed:
            return

        self._closed = True

        await self.client.aclose()

        logger.debug(
            "SiliconFlowClient closed"
        )

    async def __aenter__(self):
        """
        支持：

        async with SiliconFlowClient() as client:
            ...
        """
        if self._closed:
            raise RuntimeError(
                "已关闭的 SiliconFlowClient 不能再次使用"
            )

        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """
        async with 退出时自动释放 HTTP 连接池。
        """
        await self.close()
