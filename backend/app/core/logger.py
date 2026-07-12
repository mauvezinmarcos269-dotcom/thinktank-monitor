import logging
import sys

def setup_logging():
    """
    初始化并配置全局日志系统
    """
    # 定义日志输出格式：时间 | 级别 | 模块名 | 消息
    log_format = "%(asctime)s | %(levelname)-8s | [%(module)s] | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 基础配置，将日志输出到标准输出（控制台），以便 Docker 能够捕获
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    

# 导出一个默认的 logger 供其他模块使用
logger = logging.getLogger(__name__)