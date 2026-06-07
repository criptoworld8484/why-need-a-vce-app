"""Why need a VCE app? - Modulo de configuracion y rutas."""

from .paths import get_app_dir, get_data_dir, get_config_dir
from .api_key_manager import save_api_key, load_api_key

__all__ = [
    "get_app_dir",
    "get_data_dir", 
    "get_config_dir",
    "save_api_key",
    "load_api_key",
]
