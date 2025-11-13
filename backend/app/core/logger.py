import logging
import sys
import colorlog  
from logging.handlers import RotatingFileHandler
from app.core.config import settings


LOG_FORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_FORMAT_CONSOLE = (
    "%(log_color)s%(levelname)-8s%(reset)s | "  
    "%(asctime)s | "
    "%(name)s | "
    "%(message)s"
)

# --- Cấu hình Handlers ---

color_formatter = colorlog.ColoredFormatter(
    LOG_FORMAT_CONSOLE,
    datefmt=DATE_FORMAT,
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white', 
    },
    secondary_log_colors={},
    style='%'
)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(color_formatter)  

file_formatter = logging.Formatter(LOG_FORMAT_FILE, DATE_FORMAT)
file_handler = RotatingFileHandler(
    "app_log.log", 
    maxBytes=5*1024*1024, 
    backupCount=2,
    encoding='utf-8' 
)
file_handler.setFormatter(file_formatter) 

# --- Cấu hình logging cơ bản ---
log_level = logging.DEBUG if settings.api_reload else logging.INFO

root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.addHandler(stream_handler)
# root_logger.addHandler(file_handler) # Bỏ comment dòng này để ghi ra file

# Hàm để các module khác sử dụng
def get_logger(name: str) -> logging.Logger:
    """
    Lấy một logger instance với tên cụ thể.
    """
    return logging.getLogger(name)

# Logger gốc để import nhanh
logger = get_logger("fake_news_detector")