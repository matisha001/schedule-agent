"""
日志初始化

集中管理项目的日志输出行为，业务代码只需要导入这里的 logger，就可以使用同一套日志能力
"""

from loguru import logger

__all__ = ["logger"]
