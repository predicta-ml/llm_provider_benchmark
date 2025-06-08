import streamlit as st
import time
import os
import subprocess
import requests

# Si quieres cargar keys de .env (recomendado)
from dotenv import load_dotenv
load_dotenv()

# ----------- Configuración inicial ----------
st.set_page_config(page_title="Chatbot Multiproveedor de LLMs", layout="wide")

# ----------- Providers disponibles -----------
PROVIDERS = {
    "Google (Gemini)": {"host": "generativelanguage.googleapis.com"},
    "Together.ai": {"host": "api.together.xyz"},
    "Fireworks.ai": {"host": "api.fireworks.ai"},
    "Groq": {"host": "api.groq.com"},
    "Ollama (local)": {"host": "localhost"},
}

# ----------- Estado de la app (session state) -----------
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "traceroute" not in st.session_state:
    st.session_state["traceroute"] = []
if "latency_ms" not in st.session_state:
    st.session_state["latency_ms"] = None
if "last_provider" not in st.session_state:
    st.session_state["last_provider"] = list(PROVIDERS.keys())[0]

# ----------- Utilidades -----------

def run_traceroute(host, max_hops=10, timeout=3):
    # Usamos 'traceroute' en Unix/macOS y 'tracert' en Windows
    traceroute_cmd = ["traceroute", "-m", str(max_hops), "-w", str(timeout), host]
    if os.name == "nt":
        traceroute_cmd = ["tracert", "-h", str(max_hops), "-w", str(timeout*1000), host]
    try:
        result = subprocess.run(
            traceroute_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout*max_hops
        )
        output = result.stdout.decode("utf-8").splitlines()
        hops = []
        for line in output[1:]:  # Saltar encabezado
            if "*" in line:
                continue  # hop no respondido
            # Extraer IP usando split o regex simple
            parts = line.split()
            for part in parts:
                if part.replace('.', '').isdigit():
                    hops.append(part)
                    break
        return hops if hops else ["Traceroute incompleto"]
    except Exception as e:
        return [f"Error traceroute: {str(e)}"]

def call_ollama_api(user_msg):
    try:
        url = "http://localhost:11434/api/chat"
        data = {
            "model": "llama3.1",
            "messages": [{"role": "user", "content": user_msg}],
            "stream": False,
            "keep_alive": -1
        }
        resp = requests.post(url, json=data, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()
        return res_json['message']['content'], None
    except Exception as e:
        return None, f"Error Ollama: {str(e)}"

def call_google_gemini_api(user_msg):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None, "No API key de Gemini configurada."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-8b:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": user_msg}]}]
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        if resp.status_code != 200:
            return None, f"Error Gemini ({resp.status_code}): {resp.text}"
        res_json = resp.json()
        reply = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return reply, None
    except Exception as e:
        return None, f"Error Gemini: {str(e)}"


def call_together_api(user_msg):
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        return "No API key configurada.", None
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
        return "No API key configurada.", None
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

def call_groq_api(user_msg):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "No API key configurada.", None
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

def call_provider(provider, user_msg):
    # Centraliza aquí la lógica de enrutado a cada proveedor
    if provider == "Ollama (local)":
        return call_ollama_api(user_msg)
    elif provider == "Google (Gemini)":
        return call_google_gemini_api(user_msg)
    elif provider == "Together.ai":
        return call_together_api(user_msg)
    elif provider == "Fireworks.ai":
        return call_fireworks_api(user_msg)
    elif provider == "Groq":
        return call_groq_api(user_msg)
    else:
        return None, "Proveedor no soportado."

# ----------- Layout de la app -----------
col1, col2 = st.columns([2,1])

with col1:
    st.title("💬 Benchmark de proveedores de LLMs")
    provider = st.selectbox("Selecciona el proveedor", list(PROVIDERS.keys()), key="prov_sel")
    
    # Reset historial si cambias de proveedor
    if provider != st.session_state["last_provider"]:
        st.session_state["chat_history"] = []
        st.session_state["traceroute"] = []
        st.session_state["latency_ms"] = None
        st.session_state["last_provider"] = provider
    
    st.markdown("### Conversación")
    for m in st.session_state["chat_history"]:
        if m["role"] == "user":
            st.markdown(f"**Tú:** {m['msg']}")
        else:
            st.markdown(f"**Bot ({provider}):** {m['msg']}")
    
    user_msg = st.text_input("Escribe tu mensaje", key="user_msg_input")
    send_btn = st.button("Enviar")
    
    bot_reply = None  # Inicializar variable para la respuesta del bot
    if send_btn and user_msg:
        st.session_state["chat_history"].append({"role": "user", "msg": user_msg})
        
        # Traceroute al host del proveedor seleccionado
        host = PROVIDERS[provider]["host"]
        with st.spinner("Ejecutando traceroute..."):
            traceroute_result = run_traceroute(host)
        st.session_state["traceroute"] = traceroute_result
        
        # Medir tiempo y llamar proveedor
        start = time.time()
        with st.spinner("Consultando LLM..."):
            bot_reply, err = call_provider(provider, user_msg)
        end = time.time()
        latency = int((end - start) * 1000)

        st.session_state["latency_ms"] = latency
        
        if err:
            st.session_state["chat_history"].append({"role": "bot", "msg": f"[ERROR]: {err}"})
        else:
            st.session_state["chat_history"].append({"role": "bot", "msg": bot_reply})

    # Mostrar el último mensaje del bot (si existe)
    if st.session_state["chat_history"]:
        last_bot_msg = next(
            (m["msg"] for m in reversed(st.session_state["chat_history"]) if m["role"] == "bot"),
            None
        )
        if last_bot_msg:
            # st.markdown(f"**Respuesta del bot:** {last_bot_msg}")
            st.markdown(f"**Respuesta del bot:** {bot_reply}")

with col2:
    st.header("🔍 Traceroute y Latencia")
    st.markdown("**Traceroute al proveedor:**")
    for hop in st.session_state["traceroute"]:
        st.markdown(f"- {hop}")
    st.markdown("---")
    st.markdown(
        f"**Latencia total:** {st.session_state['latency_ms']} ms" if st.session_state['latency_ms'] else ""
    )
