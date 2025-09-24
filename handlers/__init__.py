from .user import user_router
from .admin import admin_router
from .fallbacks import fallback_router

__all__ = ['user_router', 'admin_router', 'fallback_router']
