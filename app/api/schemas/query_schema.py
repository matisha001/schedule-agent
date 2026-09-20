"""API 请求/响应模型。"""

from pydantic import BaseModel


class QuerySchema(BaseModel):
    query: str
