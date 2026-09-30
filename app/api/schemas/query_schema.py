"""API 请求/响应模型。"""

from pydantic import BaseModel, Field


class QuerySchema(BaseModel):
    query: str = Field(description="用户的自然语言问数内容，如「上届冠军是谁」")


class PresetQueryParam(BaseModel):
    key: str = Field(description="参数键名，用于在模板中占位替换")
    source: str = Field(default="tournaments", description="参数候选来源，如 tournaments（赛事）")


class PresetQueryOut(BaseModel):
    id: str = Field(description="预制提示词 ID")
    title: str = Field(description="预制提示词标题")
    template: str = Field(description="提示词模板内容，包含 {key} 占位符")
    params: list[PresetQueryParam] = Field(default_factory=list, description="模板参数列表")
