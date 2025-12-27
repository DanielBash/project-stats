"""
Файл задания основных настроек сервера.
"""

# -- импорт модулей
import dataclasses
from pathlib import Path


# -- создание класса настроек
@dataclasses.dataclass
class Config:
    PORT = 5000
    DEBUG = True
    REPO_FOLDER = Path('.repo')
    REPO_CACHES = Path('.repo_cache')

# - создание настроек
config = Config()