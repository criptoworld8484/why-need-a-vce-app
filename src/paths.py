"""Modulo de gestion de rutas para ejecutables y scripts."""

import os
import sys
import tempfile


def get_app_dir():
    """Retorna el directorio de recursos del ejecutable o del script Python.
    
    En modo frozen (ejecutable), retorna el directorio _internal donde estan los recursos
    En modo script, retorna el directorio donde esta app.py
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, '_internal')
        if os.path.isdir(internal_dir):
            return internal_dir
        return exe_dir
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir():
    """Retorna el directorio de datos del usuario.
    
    Windows: %APPDATA%/WhyNeedAVCEApp
    Linux/Mac: ~/.local/share/WhyNeedAVCEApp
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", tempfile.gettempdir())
    else:
        base = os.path.expanduser("~/.local/share")
    return os.path.join(base, "WhyNeedAVCEApp")


def get_config_dir():
    """Retorna el directorio de configuracion del usuario.
    
    Windows: %APPDATA%/WhyNeedAVCEApp
    Linux/Mac: ~/.config/WhyNeedAVCEApp
    """
    if sys.platform == "win32":
        return os.environ.get("APPDATA", tempfile.gettempdir())
    return os.path.join(os.path.expanduser("~/.config"), "WhyNeedAVCEApp")


def get_resource_path(relative_path):
    """Retorna la ruta absoluta a un recurso.
    
    Funciona tanto en modo frozen como en modo script.
    """
    base_path = get_app_dir()
    return os.path.join(base_path, relative_path)
