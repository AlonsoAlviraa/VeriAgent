"""
[TEAM-AI][COST-ZERO-001] Multi-Provider LLM Router
Router inteligente que rota entre proveedores gratuitos para conseguir
$0.00 en costes de inferencia manteniendo alta disponibilidad.

Proveedores soportados:
- Groq: 60 RPM (Llama 3.3 70B)
- Cerebras: 30 RPM (Llama 3.1 70B)
- Gemini: 30+ RPM (Gemini 2.0 Flash)
- OpenRouter: Modelos gratuitos rotativos

Capacidad total estimada: 120+ peticiones/minuto GRATIS

Autor: AI Cost Optimization Engineer
Fecha: 2024-12
Version: 1.0
"""

import os
import time
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import threading

# LiteLLM unifica todas las APIs bajo un interfaz tipo OpenAI
import litellm
from litellm import completion, RateLimitError, APIError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

class Provider(Enum):
    """Proveedores de LLM gratuitos soportados."""
    GROQ = "groq"
    CEREBRAS = "cerebras"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


@dataclass
class ProviderConfig:
    """Configuracion de un proveedor de LLM."""
    name: Provider
    model: str
    rpm_limit: int  # Requests per minute
    env_key: str    # Environment variable for API key
    priority: int = 1  # Lower = higher priority


# Configuracion de proveedores gratuitos
FREE_PROVIDERS: List[ProviderConfig] = [
    ProviderConfig(
        name=Provider.GROQ,
        model="groq/llama-3.3-70b-versatile",
        rpm_limit=60,
        env_key="GROQ_API_KEY",
        priority=1
    ),
    ProviderConfig(
        name=Provider.CEREBRAS,
        model="cerebras/llama-3.3-70b",  # Fixed model name
        rpm_limit=30,
        env_key="CEREBRAS_API_KEY",
        priority=2
    ),
    ProviderConfig(
        name=Provider.GEMINI,
        model="gemini/gemini-1.5-flash",  # Changed to stable version
        rpm_limit=30,
        env_key="GEMINI_API_KEY",
        priority=3
    ),
    ProviderConfig(
        name=Provider.OPENROUTER,
        model="openrouter/google/gemini-2.0-flash-thinking-exp:free",
        rpm_limit=20,
        env_key="OPENROUTER_API_KEY",
        priority=4
    ),
]


# ============================================================
# LLM ROUTER CLASS
# ============================================================

class ZeroCostLLMRouter:
    """
    Router inteligente que balancea carga entre proveedores gratuitos.
    Usa Round-Robin con fallback automatico en caso de rate limits.
    """

    def __init__(self, providers: List[ProviderConfig] = None):
        """
        Inicializa el router con los proveedores disponibles.
        Solo activa proveedores cuyas API keys estan configuradas.
        """
        self.all_providers = providers or FREE_PROVIDERS
        self.active_providers: List[ProviderConfig] = []
        self.current_index = 0
        self.lock = threading.Lock()
        
        # Request tracking for rate limiting
        self.request_counts: Dict[str, List[float]] = {}
        
        self._init_providers()
        
        logger.info(f"[LLM-Router] Inicializado con {len(self.active_providers)} proveedores activos")
        for p in self.active_providers:
            logger.info(f"  - {p.name.value}: {p.model} ({p.rpm_limit} RPM)")

    def _init_providers(self):
        """Detecta y activa proveedores con API keys configuradas."""
        for provider in sorted(self.all_providers, key=lambda p: p.priority):
            api_key = os.getenv(provider.env_key)
            if api_key:
                self.active_providers.append(provider)
                self.request_counts[provider.name.value] = []
                logger.info(f"[LLM-Router] Proveedor activado: {provider.name.value}")
            else:
                logger.debug(f"[LLM-Router] Proveedor sin API key: {provider.name.value}")
        
        if not self.active_providers:
            logger.warning("[LLM-Router] No hay proveedores activos. Configura al menos una API key.")

    def _get_next_provider(self) -> Optional[ProviderConfig]:
        """Obtiene el siguiente proveedor usando Round-Robin."""
        if not self.active_providers:
            return None
        
        with self.lock:
            provider = self.active_providers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.active_providers)
        
        return provider

    def _check_rate_limit(self, provider: ProviderConfig) -> bool:
        """Verifica si el proveedor esta dentro de su limite de rate."""
        now = time.time()
        window_start = now - 60  # Ventana de 1 minuto
        
        # Limpiar requests antiguos
        self.request_counts[provider.name.value] = [
            t for t in self.request_counts[provider.name.value]
            if t > window_start
        ]
        
        current_rpm = len(self.request_counts[provider.name.value])
        return current_rpm < provider.rpm_limit

    def _record_request(self, provider: ProviderConfig):
        """Registra una peticion para tracking de rate limits."""
        self.request_counts[provider.name.value].append(time.time())

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Envia un mensaje al LLM usando el router de proveedores.
        Implementa fallback automatico si un proveedor falla.
        
        Args:
            messages: Lista de mensajes en formato OpenAI
            temperature: Temperatura de generacion
            max_tokens: Maximo de tokens a generar
            
        Returns:
            Respuesta del LLM en formato estandar
        """
        if not self.active_providers:
            raise RuntimeError("No hay proveedores LLM activos. Configura al menos una API key.")
        
        attempts = 0
        max_attempts = len(self.active_providers) * 2
        errors = []
        
        while attempts < max_attempts:
            provider = self._get_next_provider()
            
            # Verificar rate limit local
            if not self._check_rate_limit(provider):
                logger.debug(f"[LLM-Router] Rate limit local alcanzado para {provider.name.value}")
                attempts += 1
                continue
            
            try:
                logger.info(f"[LLM-Router] Usando proveedor: {provider.name.value} ({provider.model})")
                
                # Llamada via LiteLLM
                response = completion(
                    model=provider.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                # Registrar peticion exitosa
                self._record_request(provider)
                
                # Extraer contenido
                content = response.choices[0].message.content
                
                return {
                    "success": True,
                    "content": content,
                    "provider": provider.name.value,
                    "model": provider.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    }
                }
                
            except RateLimitError as e:
                logger.warning(f"[LLM-Router] Rate limit en {provider.name.value}: {e}")
                errors.append(f"{provider.name.value}: RateLimit")
                attempts += 1
                
            except APIError as e:
                logger.warning(f"[LLM-Router] API Error en {provider.name.value}: {e}")
                errors.append(f"{provider.name.value}: {str(e)[:50]}")
                attempts += 1
                
            except Exception as e:
                logger.error(f"[LLM-Router] Error inesperado en {provider.name.value}: {e}")
                errors.append(f"{provider.name.value}: {str(e)[:50]}")
                attempts += 1
        
        # Todos los intentos fallaron
        return {
            "success": False,
            "content": None,
            "error": f"Todos los proveedores fallaron: {'; '.join(errors)}"
        }

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado actual del router."""
        status = {
            "active_providers": len(self.active_providers),
            "total_capacity_rpm": sum(p.rpm_limit for p in self.active_providers),
            "providers": []
        }
        
        for provider in self.active_providers:
            current_rpm = len([
                t for t in self.request_counts.get(provider.name.value, [])
                if t > time.time() - 60
            ])
            status["providers"].append({
                "name": provider.name.value,
                "model": provider.model,
                "rpm_limit": provider.rpm_limit,
                "current_rpm": current_rpm,
                "available": current_rpm < provider.rpm_limit
            })
        
        return status


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_router_instance: Optional[ZeroCostLLMRouter] = None

def get_llm_router() -> ZeroCostLLMRouter:
    """Obtiene la instancia singleton del router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ZeroCostLLMRouter()
    return _router_instance


# ============================================================
# CONVENIENCE FUNCTION (Drop-in replacement for OpenAI)
# ============================================================

def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **kwargs
) -> str:
    """
    Funcion de conveniencia para reemplazar llamadas a OpenAI.
    Retorna directamente el contenido del mensaje.
    
    Ejemplo:
        response = chat_completion([
            {"role": "system", "content": "Eres un experto fiscal."},
            {"role": "user", "content": "Valida esta factura..."}
        ])
    """
    router = get_llm_router()
    result = router.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
    
    if result["success"]:
        return result["content"]
    else:
        raise RuntimeError(result["error"])


# ============================================================
# MAIN - Test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print(" Zero-Cost LLM Router - Test")
    print("=" * 60)
    
    # Check for API keys
    print("\n[Config] API Keys detectadas:")
    for provider in FREE_PROVIDERS:
        has_key = bool(os.getenv(provider.env_key))
        status = "OK" if has_key else "NO CONFIGURADA"
        print(f"  {provider.name.value}: {status}")
    
    try:
        router = get_llm_router()
        status = router.get_status()
        
        print(f"\n[Status] Proveedores activos: {status['active_providers']}")
        print(f"[Status] Capacidad total: {status['total_capacity_rpm']} RPM")
        
        if router.active_providers:
            print("\n[Test] Enviando mensaje de prueba...")
            
            result = router.chat([
                {"role": "system", "content": "Responde en una sola linea."},
                {"role": "user", "content": "Di 'Hola, soy el router de IA gratuito de VeriAgent'"}
            ])
            
            if result["success"]:
                print(f"\n[OK] Respuesta via {result['provider']}:")
                print(f"  {result['content']}")
                print(f"  Tokens: {result['usage']['total_tokens']}")
            else:
                print(f"\n[ERROR] {result['error']}")
        else:
            print("\n[WARN] No hay proveedores activos para probar.")
            print("  Configura al menos una de estas variables de entorno:")
            for provider in FREE_PROVIDERS:
                print(f"    - {provider.env_key}")
    
    except Exception as e:
        print(f"\n[ERROR] {e}")
    
    print("\n" + "=" * 60)
