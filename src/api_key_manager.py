"""Modulo para gestionar la API key de Google Gemini de forma segura."""

import os
import json
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

CONFIG_FILE = "gemini_key.enc"
KEY_FILE = ".keyfile"


def _get_config_path():
    """Obtiene la ruta del directorio de configuracion."""
    from .paths import get_config_dir
    config_dir = get_config_dir()
    return config_dir


def _ensure_config_dir():
    """Crea el directorio de configuracion si no existe."""
    path = _get_config_path()
    os.makedirs(path, exist_ok=True)
    return path


def _get_key():
    """Obtiene o genera la clave de encriptacion."""
    if not CRYPTO_AVAILABLE:
        return None
    
    config_dir = _ensure_config_dir()
    key_path = os.path.join(config_dir, KEY_FILE)
    
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return key


def save_api_key(api_key: str) -> bool:
    """Guarda la API key de forma encriptada.
    
    Args:
        api_key: La clave de API de Google Gemini.
        
    Returns:
        True si se guardo correctamente, False en caso contrario.
    """
    if not CRYPTO_AVAILABLE:
        return False
    
    try:
        key = _get_key()
        if key is None:
            return False
            
        f = Fernet(key)
        config_dir = _ensure_config_dir()
        config_path = os.path.join(config_dir, CONFIG_FILE)
        
        encrypted = f.encrypt(api_key.encode())
        with open(config_path, "wb") as file:
            file.write(encrypted)
        return True
    except Exception:
        return False


def load_api_key() -> str | None:
    """Carga la API key encriptada guardada.
    
    Returns:
        La API key desencriptada o None si no existe o hay error.
    """
    if not CRYPTO_AVAILABLE:
        return None
    
    try:
        key = _get_key()
        if key is None:
            return None
            
        f = Fernet(key)
        config_path = os.path.join(_get_config_path(), CONFIG_FILE)
        
        if os.path.exists(config_path):
            with open(config_path, "rb") as file:
                encrypted = file.read()
            return f.decrypt(encrypted).decode()
    except Exception:
        pass
    return None


def delete_api_key() -> bool:
    """Elimina la API key guardada.

    Borra tambien la keyfile de Fernet: solo sirve para (des)encriptar la
    key que se esta borrando, y dejarla huerfana obligaria a generar otra
    en el siguiente guardado.
    """
    try:
        config_path = os.path.join(_get_config_path(), CONFIG_FILE)
        if os.path.exists(config_path):
            os.remove(config_path)
        key_path = os.path.join(_get_config_path(), KEY_FILE)
        if os.path.exists(key_path):
            os.remove(key_path)
        return True
    except Exception:
        return False


def has_api_key() -> bool:
    """Verifica si existe una API key guardada.
    
    Returns:
        True si existe una API key, False en caso contrario.
    """
    config_path = os.path.join(_get_config_path(), CONFIG_FILE)
    return os.path.exists(config_path)
