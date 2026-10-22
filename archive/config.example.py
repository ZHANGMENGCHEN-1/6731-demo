"""复制为 config.py，或通过环境变量配置。不要提交真实 Key。"""
import os

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "zhipu")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-5.3")
LLM_API_KEY = os.getenv("LLM_API_KEY")
