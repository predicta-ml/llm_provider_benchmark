import streamlit as st
import time
import os
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import json

load_dotenv()

# ----------- Configuración inicial ----------
st.set_page_config(page_title="Benchmark LLM Providers", layout="wide")

# ----------- Providers disponibles -----------
PROVIDERS = {
    "Google Gemini": {
        "host": "generativelanguage.googleapis.com",
        "call_fn": "call_google_gemini_api",
        "color": "#00c3ff"
    },
    "Groq": {
        "host": "api.groq.com",
        "call_fn": "call_groq_api",
        "color": "#00ff99"
    },
    "Together.ai": {
        "host": "api.together.xyz",
        "call_fn": "call_together_api",
        "color": "#ffeb3b"
    },
    "Fireworks.ai": {
        "host": "api.fireworks.ai",
        "call_fn": "call_fireworks_api",
        "color": "#ff5a36"
    },
    "Industria Predicta": {
        "host": "localhost",
        "call_fn": "call_predicta_api",
        "color": "#cd83ff"
    }
}

# ----------- Funciones de Providers -----------

def run_traceroute(host, max_hops=30, timeout=3):
    traceroute_cmd = ["traceroute", "-m", str(max_hops), "-w", str(timeout), host]
    if os.name == "nt":
        traceroute_cmd = ["tracert", "-h", str(max_hops), "-w", str(timeout*1000), host]
    try:
        result = subprocess.run(
            traceroute_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout*max_hops
        )
        output = result.stdout.decode("utf-8").splitlines()
        hops = []
        for line in output[1:]:
            if "*" in line:
                continue
            parts = line.split()
            hops.append(parts[2])
        return hops if hops else ["Traceroute incompleto"]
    except Exception as e:
        return [f"Error traceroute: {str(e)}"]

def call_google_gemini_api(user_msg):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None, "No API key de Gemini configurada."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-8b:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": user_msg}]}]}
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        if resp.status_code != 200:
            return None, f"Error Gemini ({resp.status_code}): {resp.text}"
        res_json = resp.json()
        reply = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return reply, None
    except Exception as e:
        return None, f"Error Gemini: {str(e)}"

def call_groq_api(user_msg):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None, "No API key configurada."
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": user_msg}],
        "max_tokens": 60
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        resp.raise_for_status()
        res_json = resp.json()
        return res_json['choices'][0]['message']['content'], None
    except Exception as e:
        return None, f"Error GROQ: {str(e)}"

def call_together_api(user_msg):
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        return None, "No API key configurada."
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "messages": [{"role": "user", "content": user_msg}],
        "max_tokens": 60
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        resp.raise_for_status()
        res_json = resp.json()
        return res_json['choices'][0]['message']['content'], None
    except Exception as e:
        return None, f"Error Together.ai: {str(e)}"

def call_fireworks_api(user_msg):
    api_key = os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        return None, "No API key configurada."
    url = "https://api.fireworks.ai/inference/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "messages": [{"role": "user", "content": user_msg}],
        "max_tokens": 60
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        resp.raise_for_status()
        res_json = resp.json()
        return res_json['choices'][0]['message']['content'], None
    except Exception as e:
        return None, f"Error Fireworks.ai: {str(e)}"

def call_predicta_api(user_msg):
    try:
        url = "http://localhost:11434/api/chat"
        data = {
            "model": "llama3.1",
            "messages": [{"role": "user", "content": user_msg}]
        }
        resp = requests.post(url, json=data, timeout=30, stream=True)
        reply = ""
        for line in resp.iter_lines():
            if line:
                chunk = line.decode("utf-8")
                try:
                    json_chunk = json.loads(chunk)
                    if "message" in json_chunk and "content" in json_chunk["message"]:
                        reply += json_chunk["message"]["content"]
                    elif "response" in json_chunk:
                        reply += json_chunk["response"]
                except Exception:
                    continue
        return reply.strip(), None
    except Exception as e:
        return None, f"Error predicta: {str(e)}"

# ----------- Función wrapper para thread -----------
def process_provider(provider_key, user_msg):
    provider = PROVIDERS[provider_key]
    # 1. Traceroute
    hops = run_traceroute(provider["host"])
    # 2. LLM inference
    t0 = time.time()
    if provider["call_fn"] == "call_google_gemini_api":
        reply, err = call_google_gemini_api(user_msg)
    elif provider["call_fn"] == "call_groq_api":
        reply, err = call_groq_api(user_msg)
    elif provider["call_fn"] == "call_together_api":
        reply, err = call_together_api(user_msg)
    elif provider["call_fn"] == "call_fireworks_api":
        reply, err = call_fireworks_api(user_msg)
    elif provider["call_fn"] == "call_predicta_api":
        reply, err = call_predicta_api(user_msg)
    else:
        reply, err = None, "Función no soportada."
    t1 = time.time()
    latency_ms = int((t1 - t0) * 1000)
    return {
        "provider": provider_key,
        "latency": latency_ms,
        "output": reply if not err else err,
        "traceroute": hops
    }

# ----------- Layout principal -----------
st.title("🚀 Benchmark multiproveedor de LLMs")
st.markdown("Envía el mismo prompt a cada LLM y compara la latencia, salida y traceroute en tiempo real.")

prompt = st.text_input("Escribe tu mensaje y presiona Enter:", key="input_text")

if prompt:
    # Usa ThreadPoolExecutor para correr todos los providers en paralelo
    results = {k: {"latency": None, "output": "Procesando...", "traceroute": []} for k in PROVIDERS.keys()}
    cols = st.columns(len(PROVIDERS))

    # Muestra un spinner global
    with st.spinner("Enviando prompt a todos los proveedores..."):
        with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as executor:
            future_to_provider = {
                executor.submit(process_provider, k, prompt): k for k in PROVIDERS.keys()
            }
            for future in as_completed(future_to_provider):
                provider = future_to_provider[future]
                try:
                    result = future.result()
                    results[provider] = result
                except Exception as e:
                    results[provider] = {
                        "latency": None,
                        "output": f"ERROR: {str(e)}",
                        "traceroute": []
                    }
                # Refresca la UI para mostrar el resultado de este provider
                with cols[list(PROVIDERS.keys()).index(provider)]:
                    st.subheader(provider)
                    st.markdown(f"**Latencia:** {results[provider]['latency']} ms" if results[provider]['latency'] is not None else "Latencia: ...")
                    st.markdown("---")
                    st.markdown(results[provider]["output"])
                    st.markdown("---")
                    st.markdown("Traceroute:")
                    for i, hop in enumerate(results[provider]["traceroute"]):
                        st.markdown(f"{i+1}. {hop}")
else:
    # Layout en blanco, listo para la primer consulta
    cols = st.columns(len(PROVIDERS))
    for idx, key in enumerate(PROVIDERS.keys()):
        with cols[idx]:
            st.subheader(key)
            st.markdown("Latencia: N ms")
            st.markdown("---")
            st.markdown("*Esperando input...*")
            st.markdown("---")
            st.markdown("Traceroute:")

