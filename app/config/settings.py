"""
文件名：settings.py
作用说明：项目全局配置加载器
统一从 .env 和 request_conf.yaml 中读取所有配置，提供单一配置源。

设计原则：
- 敏感信息（密码、私钥）不设默认值，强制在 .env 中配置
- 公共参数和合理默认值提供默认值，便于开发环境快速启动
- YAML 配置通过懒加载方式集成到 Settings 类中
- 配置加载优先级：环境变量 > .env 文件 > 默认值

架构分层：
1. YAML 配置数据模型定义（Pydantic BaseModel）
2. 主配置类（继承 BaseSettings，支持环境变量）
3. 全局配置实例（单例模式）
"""

from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
from pathlib import Path
import yaml
from typing import Dict, Any, Optional


# ==============================
# YAML 配置数据模型定义
# ==============================

class CommonConfig(BaseModel):
    """
    YAML 配置中的 common 部分
    对应 request_conf.yaml 中的 common 节点
    """
    ut: str = Field(description="东方财富API的UT参数（公共认证令牌）")
    cb: str = Field(description="JSONP回调函数前缀")
    timeout: int = Field(default=10, description="HTTP请求超时时间（秒）")
    max_pages: int = Field(default=100, description="最大分页数")


class EndpointConfig(BaseModel):
    """
    YAML 配置中的 endpoints 部分
    对应 request_conf.yaml 中 endpoints 下的每个端点配置

    设计特点：
    - 使用 Optional 字段支持不同端点的不同参数组合
    - extra = "allow" 允许额外字段（如时间戳 "_" 参数）
    - 通用参数（如 fields）为必填项
    """
    url: str = Field(description="API端点URL")

    # 板块接口特有参数（可选）
    fid: Optional[str] = Field(default=None, description="排序字段ID")
    po: Optional[str] = Field(default=None, description="排序方向")
    pz: Optional[str] = Field(default=None, description="每页数量")
    np: Optional[str] = Field(default=None, description="页码类型")
    fltt: Optional[str] = Field(default=None, description="过滤类型")
    invt: Optional[str] = Field(default=None, description="投资类型")
    fs: Optional[str] = Field(default=None, description="筛选条件")

    # 通用参数（必填）
    fields: str = Field(description="返回字段列表")

    # 个股快照接口特有参数（可选）
    wbp2u: Optional[str] = Field(default=None, description="Web参数")
    dect: Optional[str] = Field(default=None, description="检测参数")

    class Config:
        extra = "allow"  # 👈 允许额外字段，包括 "_"（时间戳参数）


class RequestConfig(BaseModel):
    """
    完整的 YAML 请求配置模型
    将 common 和 endpoints 组合成完整的配置结构
    """
    common: CommonConfig
    endpoints: Dict[str, EndpointConfig]


# ==============================
# 主配置类
# ==============================

class Settings(BaseSettings):
    """
    全局配置类，继承自 Pydantic BaseSettings

    配置加载优先级（从高到低）：
    1. 环境变量 (os.environ)
    2. .env 文件
    3. 字段默认值（本文件中定义）

    这种设计确保了：
    - 生产环境可通过环境变量覆盖配置
    - 开发环境可使用 .env 文件
    - 必要配置无默认值，避免遗漏
    """

    # ==============================
    # 基础应用配置
    # ==============================
    APP_ENV: str = Field(default="dev", description="应用环境 (dev/test/prod)")
    APP_NAME: str = Field(default="TXDYGPLHXT", description="应用名称")

    # ==============================
    # PostgreSQL 数据库配置
    # ==============================
    # 敏感信息无默认值，强制在 .env 中配置
    POSTGRES_HOST: str = Field(description="数据库主机地址")
    POSTGRES_PORT: int = Field(default=5432, description="数据库端口")
    POSTGRES_DB: str = Field(description="数据库名称")
    POSTGRES_USER: str = Field(description="数据库用户名")
    POSTGRES_PASSWORD: str = Field(description="数据库密码（敏感信息，无默认值）")

    # ==============================
    # SQLAlchemy 连接池配置
    # ==============================
    DB_ECHO: bool = Field(default=False, description="是否输出SQL日志")
    DB_POOL_SIZE: int = Field(default=10, description="连接池大小")
    DB_MAX_OVERFLOW: int = Field(default=20, description="连接池溢出最大数量")

    @property
    def database_url(self) -> str:
        """
        构建完整的数据库连接URL

        返回格式：postgresql+psycopg2://user:password@host:port/dbname

        安全考虑：密码直接包含在URL中，确保此URL不在日志中暴露
        """
        return (
            f"postgresql+psycopg2://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    # ==============================
    # 东方财富 API 配置（备用方案）
    # ==============================
    # 注意：这些配置在 request_conf.yaml 中也有，此处为兼容性保留
    EASTMONEY_UT: str = Field(default="8dec03ba335b81bf4ebdf7b29ec27d15",description="东方财富API UT 参数（公共值，可安全设为默认）")
    EASTMONEY_CB_PREFIX: str = Field(default="jQuery112308004600294897531_1767433763641",description="JSONP 回调函数前缀模板")
    EASTMONEY_PAGE_SIZE: int = Field(default=100, description="每页数据量")
    EASTMONEY_TIMEOUT: int = Field(default=10, description="API请求超时时间（秒）")

    # ==============================
    # YAML 请求配置（懒加载）
    # ==============================
    @property
    def request_config(self) -> RequestConfig:
        """
        懒加载 YAML 配置文件

        优势：
        - 只在首次访问时加载，避免启动时不必要的IO
        - 将 YAML 配置与 Pydantic 模型结合，获得类型安全和验证
        - 统一配置入口，collector 不再直接读取文件

        配置文件路径：app/config/request_conf.yaml

        实现逻辑：
        1. 检查是否已加载（缓存机制）
        2. 动态确定配置文件路径（相对于 settings.py 的位置）
        3. 读取并解析 YAML 文件
        4. 转换为 Pydantic 模型，获得验证和类型安全
        5. 缓存结果避免重复加载
        """
        if not hasattr(self, "_request_config"):
            # 动态确定配置文件路径（相对于 settings.py 的位置）
            config_path = Path(__file__).parent / "request_conf.yaml"

            # 读取并解析 YAML 文件
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)

            # 转换为 Pydantic 模型，获得验证和类型安全
            self._request_config = RequestConfig(
                common=CommonConfig(**yaml_data["common"]),
                endpoints={
                    key: EndpointConfig(**value)
                    for key, value in yaml_data["endpoints"].items()
                }
            )
        return self._request_config

    class Config:
        """Pydantic 配置"""
        env_file = ".env"           # 指定 .env 文件路径
        env_file_encoding = "utf-8" # 指定 .env 文件编码
        extra = "allow"             # 👈 允许 .env 中的额外字段


# ==============================
# 全局配置实例
# ==============================
# 单例模式，整个应用使用同一个配置实例
settings = Settings()