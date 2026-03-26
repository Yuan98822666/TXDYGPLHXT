"""
app/config/settings.py
==================
全局配置加载器

配置来源（优先级从高到低）：
  1. 环境变量（生产环境）
  2. .env 文件（开发环境）
  3. YAML 文件（app/config/request_conf.yaml）
  4. 代码默认值（本文件）

单例模式：整个应用使用同一个 settings 实例
"""

from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
from pathlib import Path
import yaml
from typing import Dict, Any, Optional


# =========================================================
# YAML 配置数据模型
# 定义 request_conf.yaml 的数据结构
# =========================================================

class CommonConfig(BaseModel):
    """通用参数，所有接口共用"""
    ut: str = Field(description="东方财富API认证令牌")
    cb: str = Field(description="JSONP回调函数名")
    timeout: int = Field(default=10, description="HTTP请求超时（秒）")
    max_pages: int = Field(default=100, description="最大分页数")


class EndpointConfig(BaseModel):
    """
    单个接口端点的配置参数
    字段说明：
      url      = API接口URL
      fid      = 排序字段ID
      po       = 排序方向（1=降序）
      pz       = 每页数量
      np       = 页码类型
      fltt     = 过滤类型
      invt     = 投资类型
      fs       = 筛选条件（重要！决定采集范围）
      fields   = 返回字段列表
      wbp2u    = Web参数（个股接口用）
      dect     = 检测参数
    """
    url: str = Field(description="API接口URL")
    fid: Optional[str] = Field(default=None, description="排序字段ID")
    po: Optional[str] = Field(default=None, description="排序方向")
    pz: Optional[str] = Field(default=None, description="每页数量")
    np: Optional[str] = Field(default=None, description="页码类型")
    fltt: Optional[str] = Field(default=None, description="过滤类型")
    invt: Optional[str] = Field(default=None, description="投资类型")
    fs: Optional[str] = Field(default=None, description="筛选条件")
    fields: str = Field(description="返回字段列表")
    wbp2u: Optional[str] = Field(default=None, description="Web参数")
    dect: Optional[str] = Field(default=None, description="检测参数")

    class Config:
        extra = "allow"  # 允许额外字段（如 "_" 时间戳参数）


class RequestConfig(BaseModel):
    """完整的YAML配置结构"""
    common: CommonConfig
    endpoints: Dict[str, EndpointConfig]


# =========================================================
# 主配置类
# 继承 Pydantic BaseSettings，支持环境变量覆盖
# =========================================================

class Settings(BaseSettings):
    """
    全局配置实例

    数据库配置（敏感信息，无默认值，强制在.env中配置）：
      POSTGRES_HOST      = 数据库主机
      POSTGRES_PORT      = 端口（默认5432）
      POSTGRES_DB        = 数据库名
      POSTGRES_USER      = 用户名
      POSTGRES_PASSWORD  = 密码

    YAML配置（通过request_conf.yaml加载）：
      通过 @property request_config 访问
    """

    # ---------- 应用基础 ----------
    APP_ENV: str = Field(default="dev", description="应用环境 (dev/test/prod)")
    APP_NAME: str = Field(default="TXDYGPLHXT", description="应用名称")
    APP_PORT: int = Field(default=8084, description="应用端口")

    # ---------- 数据库（必须配置） ----------
    POSTGRES_HOST: str = Field(description="数据库主机")
    POSTGRES_PORT: int = Field(default=5432, description="数据库端口")
    POSTGRES_DB: str = Field(description="数据库名称")
    POSTGRES_USER: str = Field(description="数据库用户名")
    POSTGRES_PASSWORD: str = Field(description="数据库密码")

    # ---------- 数据库连接池 ----------
    DB_ECHO: bool = Field(default=False, description="是否输出SQL日志")
    DB_POOL_SIZE: int = Field(default=10, description="连接池大小")
    DB_MAX_OVERFLOW: int = Field(default=20, description="连接池溢出")

    # ---------- 东方财富API（备用，默认值来自YAML） ----------
    # 用途：如果YAML加载失败，使用这些默认值
    EASTMONEY_UT: str = Field(default="8dec03ba335b81bf4ebdf7b29ec27d15", description="UT认证令牌")
    EASTMONEY_CB_PREFIX: str = Field(default="jQuery1", description="JSONP回调前缀")
    EASTMONEY_PAGE_SIZE: int = Field(default=100, description="每页数量")
    EASTMONEY_TIMEOUT: int = Field(default=10, description="请求超时")

    @property
    def database_url(self) -> str:
        """构建数据库连接URL"""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def request_config(self) -> RequestConfig:
        """
        懒加载YAML配置文件
        配置路径：app/config/request_conf.yaml
        """
        if not hasattr(self, "_request_config"):
            config_path = Path(__file__).parent / "request_conf.yaml"
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            self._request_config = RequestConfig(
                common=CommonConfig(**yaml_data["common"]),
                endpoints={
                    key: EndpointConfig(**value)
                    for key, value in yaml_data["endpoints"].items()
                }
            )
        return self._request_config

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


# =========================================================
# 全局配置实例（单例）
# =========================================================
settings = Settings()
