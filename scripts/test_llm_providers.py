"""
[TEST] Zero-Cost LLM Provider Verification Script
Tests each provider individually with strict rate limiting.

Usage:
    1. Create a .env file with your API keys (see .env.example)
    2. python scripts/test_llm_providers.py
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
from dotenv import load_dotenv

# Try to load from VeriAgent.env first, then .env
env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VeriAgent.env")
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"[Config] Loaded: VeriAgent.env")
else:
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"[Config] Loaded: .env")
    else:
        print("[WARNING] No .env file found. API keys must be set manually.")

# Now import litellm
import litellm


# ============================================================
# RATE LIMIT CONFIGURATION (STRICT - NO COST)
# ============================================================

MAX_REQUESTS_PER_PROVIDER = 3  # Only 3 test requests per provider
DELAY_BETWEEN_REQUESTS = 2     # 2 seconds between requests

# ============================================================
# TEST FUNCTIONS
# ============================================================

def test_provider_litellm(name: str, model: str, api_key_env: str) -> dict:
    """
    Tests a provider via LiteLLM.
    """
    print(f"\n{'='*50}")
    print(f"Testing: {name} (via LiteLLM)")
    print(f"Model: {model}")
    print(f"{'='*50}")
    
    if not os.getenv(api_key_env):
        return {"success": False, "error": f"API key not set: {api_key_env}"}
    
    try:
        start_time = time.time()
        
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": "Responde en UNA sola linea, maximo 20 palabras."},
                {"role": "user", "content": f"Confirma que funcionas diciendo: 'Proveedor {name} operativo.'"}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        
        print(f"  Status: OK")
        print(f"  Response: {content}")
        print(f"  Tokens: {tokens}")
        print(f"  Latency: {elapsed:.2f}s")
        
        return {
            "success": True,
            "content": content,
            "tokens": tokens,
            "latency": elapsed
        }
        
    except Exception as e:
        print(f"  Status: ERROR")
        print(f"  Error: {str(e)[:100]}")
        return {"success": False, "error": str(e)}


def test_gemini_native() -> dict:
    """
    Tests Gemini using the native google-genai SDK.
    """
    print(f"\n{'='*50}")
    print(f"Testing: Gemini (via Native SDK)")
    print(f"Model: gemini-2.5-flash")
    print(f"{'='*50}")
    
    try:
        from google import genai
        
        # Client gets API key from GEMINI_API_KEY env var
        client = genai.Client()
        
        start_time = time.time()
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Responde en una linea: 'Proveedor Gemini operativo.'"
        )
        
        elapsed = time.time() - start_time
        content = response.text
        
        print(f"  Status: OK")
        print(f"  Response: {content}")
        print(f"  Latency: {elapsed:.2f}s")
        
        return {
            "success": True,
            "content": content,
            "tokens": 0,  # Native SDK doesn't return token count easily
            "latency": elapsed
        }
        
    except Exception as e:
        print(f"  Status: ERROR")
        print(f"  Error: {str(e)[:100]}")
        return {"success": False, "error": str(e)}


def run_all_tests():
    """Runs tests for all configured providers."""
    
    # LiteLLM-based providers
    litellm_providers = [
        ("Groq", "groq/llama-3.3-70b-versatile", "GROQ_API_KEY"),
        ("Cerebras", "cerebras/llama-3.3-70b", "CEREBRAS_API_KEY"),
    ]
    
    results = {}
    total_tokens = 0
    
    print("\n" + "="*60)
    print(" ZERO-COST LLM PROVIDER TEST SUITE")
    print(" Rate Limit: 3 requests per provider (cost protection)")
    print("="*60)
    
    # Test LiteLLM providers
    for name, model, env_key in litellm_providers:
        result = test_provider_litellm(name, model, env_key)
        results[name] = result
        
        if result.get("success"):
            total_tokens += result.get("tokens", 0)
        
        print(f"  [Rate Limit] Waiting {DELAY_BETWEEN_REQUESTS}s before next test...")
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Test Gemini with native SDK
    gemini_result = test_gemini_native()
    results["Gemini"] = gemini_result
    
    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results.values() if r.get("success"))
    print(f"  Providers tested: {len(results)}")
    print(f"  Successful: {successful}/{len(results)}")
    print(f"  Total tokens used: {total_tokens}")
    print(f"  Estimated cost: $0.00 (free tier)")
    
    print("\n  Provider Status:")
    for name, result in results.items():
        status = "OK" if result.get("success") else "FAIL"
        latency = f"{result.get('latency', 0):.2f}s" if result.get("success") else "-"
        print(f"    - {name}: {status} ({latency})")
    
    # Calculate total capacity
    if results.get("Groq", {}).get("success"):
        print("\n  Capacity Available:")
        print(f"    - Groq: 60 RPM")
    if results.get("Cerebras", {}).get("success"):
        print(f"    - Cerebras: 30 RPM")
    if results.get("Gemini", {}).get("success"):
        print(f"    - Gemini: 30 RPM")
    
    total_rpm = (60 if results.get("Groq", {}).get("success") else 0) + \
                (30 if results.get("Cerebras", {}).get("success") else 0) + \
                (30 if results.get("Gemini", {}).get("success") else 0)
    print(f"    TOTAL: {total_rpm} RPM FREE")
    
    print("\n" + "="*60)
    
    return results


if __name__ == "__main__":
    run_all_tests()

