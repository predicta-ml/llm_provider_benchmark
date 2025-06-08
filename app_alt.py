import streamlit as st
import requests
import subprocess
import platform
import time
import os
from dotenv import load_dotenv
from typing import Optional

# --- CONFIGURACIÓN INICIAL Y CARGA DE SECretos ---

# Cargar las variables de entorno (API keys) desde el archivo .env
load_dotenv()

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="LLM Speed & Trace Tester",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 LLM Speed & Trace Tester")
st.caption("Una herramienta para chatear con diferentes LLMs y analizar la latencia y la ruta de red.")

# --- DEFINICIÓN DE PROVEEDORES ---

# Diccionario para configurar los proveedores de LLM.
# Esto hace que sea fácil añadir o modificar proveedores en el futuro.
PROVIDERS = {
    "Google": {
        "api_url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-8b:generateContent",
        "host": "generativelanguage.googleapis.com",
        "api_key": (os.getenv("GOOGLE_API_KEY") or "").strip(),
        "model": "gemini-1.5-flash-8b",
        "docs": "https://ai.google.dev/api/rest"
    },
    "Groq": {
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "host": "api.groq.com",
        "api_key": (os.getenv("GROQ_API_KEY") or "").strip(),
        "model": "llama-3.1-8b-instant",
        "docs": "https://console.groq.com/docs/text-chat"
    },
    "Together.ai": {
        "api_url": "https://api.together.xyz/v1/chat/completions",
        "host": "api.together.xyz",
        "api_key": (os.getenv("TOGETHER_API_KEY") or "").strip(),
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "docs": "https://docs.together.ai/reference/chat-completions"
    },
    "Fireworks.ai": {
        "api_url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "host": "api.fireworks.ai",
        "api_key": (os.getenv("FIREWORKS_API_KEY") or "").strip(),
        "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "docs": "https://readme.fireworks.ai/reference/createchatcompletion"
    },
    "Predicta": {
        "api_url": "http://localhost:11434/api/chat",
        "host": "localhost",
        "api_key": "ollama", # No se requiere API Key real
        "model": "llama3.1", # Asegúrate de tener este modelo con `ollama pull llama3`
        "docs": "https://github.com/ollama/ollama/blob/main/docs/api.md"
    }
}

# --- FUNCIONES AUXILIARES ---

def get_traceroute(host):
    """Ejecuta un traceroute al host especificado y devuelve el resultado."""

    command = []
    try:
        # Determinar el comando correcto según el sistema operativo
        command = ["tracert", host] if platform.system() == "Windows" else ["traceroute", host]
        
        # Ejecutar el comando
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        
        # Recoger la salida
        stdout, stderr = process.communicate(timeout=60) # Timeout de 60 segundos
        
        if process.returncode == 0:
            return stdout
        else:
            return f"Error al ejecutar traceroute:\n{stderr}"
            
    except FileNotFoundError:
        return f"Error: El comando '{command[0]}' no se encontró. Asegúrate de que esté instalado y en el PATH de tu sistema."
    except subprocess.TimeoutExpired:
        return "Error: Traceroute tardó demasiado en responder (timeout)."
    except Exception as e:
        return f"Ocurrió un error inesperado: {e}"

# def get_llm_response(provider_name, messages):
#     """
#     Función centralizada para llamar a la API del proveedor de LLM seleccionado.
#     Construye la petición específica para cada proveedor.
#     """
#     provider = PROVIDERS[provider_name]
#     api_url = provider["api_url"]
#     api_key = provider["api_key"]
#     model = provider["model"]
    
#     if not api_key:
#         return f"Error: La API key para {provider_name} no está configurada en tu archivo .env"

#     headers = {
#         "Content-Type": "application/json",
#     }
    
#     # Adaptar la petición al formato de cada API
#     if provider_name in ["OpenAI", "Groq", "Together.ai", "Fireworks.ai"]:
#         headers["Authorization"] = f"Bearer {api_key}"
#         data = {"model": model, "messages": messages}
#     elif provider_name == "Anthropic":
#         headers["x-api-key"] = api_key
#         headers["anthropic-version"] = "2023-06-01"
#         # Anthropic necesita el mensaje del sistema fuera de la lista de mensajes
#         system_prompt = next((m['content'] for m in messages if m['role'] == 'system'), "")
#         user_messages = [m for m in messages if m['role'] != 'system']
#         data = {"model": model, "max_tokens": 1024, "messages": user_messages, "system": system_prompt}
#     elif provider_name == "Google":
#         api_url += f"?key={api_key}"
#         # Gemini tiene un formato de 'contents' diferente
#         formatted_messages = [{'parts': [{'text': m['content']}]} for m in messages]
#         data = {"contents": formatted_messages}
#     elif provider_name == "Ollama (Local)":
#         data = {"model": model, "messages": messages, "stream": False}
#     else:
#         return "Error: Proveedor no reconocido."

#     response : Optional[requests.Response] = None
#     try:
#         response = requests.post(api_url, headers=headers, json=data, timeout=120)
#         response.raise_for_status()  # Lanza un error para códigos de estado 4xx/5xx
        
#         # Extraer la respuesta del JSON, que varía según el proveedor
#         if provider_name in ["OpenAI", "Groq", "Together.ai", "Fireworks.ai"]:
#             return response.json()["choices"][0]["message"]["content"]
#         elif provider_name == "Anthropic":
#             return response.json()["content"][0]["text"]
#         elif provider_name == "Google":
#             return response.json()["candidates"][0]["content"]["parts"][0]["text"]
#         elif provider_name == "Ollama (Local)":
#             return response.json()["message"]["content"]
            
#     except requests.exceptions.RequestException as e:
#         return f"Error de conexión con la API: {e}"
#     except KeyError as e:
#         return f"Error: Respuesta inesperada de la API. No se encontró la clave: {e}. Respuesta completa: {response.text}"
#     except Exception as e:
#         return f"Ocurrió un error al procesar la respuesta: {e}"

def call_predicta_api(user_msg):
    try:
        url = "http://localhost:11434/api/chat"
        data = {
            "model": "llama3.1",
            "messages": [{"role": "user", "content": user_msg}],
            "stream": False,
        }
        resp = requests.post(url, json=data, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()
        return res_json['message']['content'], None
    except Exception as e:
        return None, f"Error Predicta: {str(e)}"

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
    if provider == "Predicta":
        return call_predicta_api(user_msg)
    elif provider == "Google":
        return call_google_gemini_api(user_msg)
    elif provider == "Together.ai":
        return call_together_api(user_msg)
    elif provider == "Fireworks.ai":
        return call_fireworks_api(user_msg)
    elif provider == "Groq":
        return call_groq_api(user_msg)
    else:
        return None, "Proveedor no soportado."

# --- INTERFAZ DE USUARIO (UI) ---

# Crear dos columnas para el layout: Chat a la izquierda, Diagnósticos a la derecha
col_chat, col_diagnostics = st.columns([2, 1])

with col_diagnostics:
    st.header("🔍 Diagnósticos")
    # Placeholder para la latencia y el traceroute. Se llenarán cuando se envíe un mensaje.
    latency_placeholder = st.empty()
    traceroute_placeholder = st.empty()
    
    latency_placeholder.info("La latencia se mostrará aquí después de enviar un mensaje.")
    traceroute_placeholder.info("El resultado de Traceroute aparecerá aquí.")

with col_chat:
    st.header("💬 Chat")

    # Selector para elegir el proveedor de LLM
    provider_name = st.selectbox(
        "Elige un proveedor de LLM:",
        list(PROVIDERS.keys())
    )

    # Mostrar enlace a la documentación de la API del proveedor seleccionado
    st.markdown(f"[Ver documentación de la API de {provider_name}]({PROVIDERS[provider_name]['docs']})", unsafe_allow_html=True)

    # Inicializar el historial de chat en el estado de la sesión si no existe
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Mostrar los mensajes del historial en la recarga de la página
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Si el mensaje es del asistente, mostrar sus métricas
            if message["role"] == "assistant" and "latency" in message:
                 st.caption(f"Proveedor: {message['provider']} | Latencia: {message['latency']:.2f}s")


    # Entrada de texto del usuario en la parte inferior de la página
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        # Añadir mensaje del usuario al historial y mostrarlo en la UI
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Mostrar mensaje del asistente con un spinner mientras se procesa la respuesta
        with st.chat_message("assistant"):
            # Medir el tiempo de inicio
            start_time = time.monotonic()
            
            # Realizar y mostrar el traceroute
            with traceroute_placeholder:
                with st.spinner(f"Ejecutando traceroute a {PROVIDERS[provider_name]['host']}..."):
                    trace_result = get_traceroute(PROVIDERS[provider_name]['host'])
                    st.code(trace_result, language="bash")
            
            # Preparar el historial para la API (puede incluir un prompt de sistema)
            api_messages = [{"role": "system", "content": "You are a helpful assistant."}] + st.session_state.messages
            
            # Obtener la respuesta del LLM
            with st.spinner(f"Esperando respuesta de {provider_name}..."):
                response_text, _ = call_provider(provider_name, prompt)
            
            # Medir el tiempo final y calcular la latencia
            end_time = time.monotonic()
            latency = end_time - start_time
            
            # Mostrar la latencia en el panel de diagnósticos
            latency_placeholder.metric(label="Latencia Total (Red + Inferencia)", value=f"{latency:.2f}s")

            # Mostrar la respuesta y la información de la métrica debajo del mensaje
            st.markdown(response_text)
            st.caption(f"Proveedor: {provider_name} | Latencia: {latency:.2f}s")

        # Añadir la respuesta del asistente al historial de chat con sus metadatos
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_text,
            "latency": latency,
            "provider": provider_name
        })
