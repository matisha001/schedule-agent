"""配置层：从 conf/app_config.yaml + .env 加载全局配置。

参照 k.md 3.1。启动时只做读取，不在模块导入时访问外部依赖。
"""

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from omegaconf import OmegaConf


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int


@dataclass
class EmbeddingConfig:
    model: str
    base_url: str
    api_key: str


@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str


@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str


@dataclass
class AuthConfig:
    token_secret: str
    token_ttl: int = 7 * 24 * 3600  # token 有效期（秒）


@dataclass
class AppConfig:
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig
    auth: AuthConfig
    # 问数权限矩阵：{"domains": {...}, "roles": {...}, "sensitive_columns": [...], "forbid_columns": [...]}
    # 结构见 conf/app_config.yaml 的 query_permissions 段（docs/permission-design.md 第 8 节）
    query_permissions: dict | None = None


# 从当前文件位置回到项目根目录（app/conf/app_config.py -> 项目根）
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")
context = OmegaConf.load(project_root / "conf" / "app_config.yaml")
schema = OmegaConf.structured(AppConfig)
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
