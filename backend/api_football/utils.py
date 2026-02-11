"""Utilidades para el módulo API-Futbol."""
import logging
import sys
from typing import Optional
from .config import LOG_LEVEL, LOG_FILE, LOG_FORMAT


def setup_logger(name: str = __name__) -> logging.Logger:
    """Configura y retorna un logger.
    
    Args:
        name: Nombre del logger
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Evitar duplicar handlers si ya existen
    if logger.handlers:
        return logger
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def normalize_string(text: Optional[str]) -> str:
    """Normaliza un string removiendo acentos y caracteres especiales.
    
    Args:
        text: Texto a normalizar
        
    Returns:
        Texto normalizado
    """
    if not text:
        return ""
    
    # Mapeo de caracteres con acentos
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U',
        ' ': '_', '-': '_', '.': '', "'": '', '"': ''
    }
    
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    # Remover caracteres especiales y convertir a mayúsculas
    result = ''.join(c for c in result if c.isalnum() or c == '_')
    return result.upper()
