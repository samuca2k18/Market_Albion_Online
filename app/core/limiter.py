# app/core/limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Instância global do rate limiter — importada por main.py e routers
limiter = Limiter(key_func=get_remote_address)
