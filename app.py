import streamlit as st
import requests
import subprocess
import platform
import time
import os
import threading
import queue
from dotenv import load_dotenv

# --- CONFIGURACIÓN INICIAL ---

# Cargar las variables de entorno (API keys) desde el archivo .env
load_dotenv()

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="LLM Benchmark",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Benchmark de Proveedores de LLMs")
st.caption("Escribe un prompt para enviarlo simultáneamente a todos los proveedores y comparar su rendimiento.")

# --- DEFINICIÓN DE PROVEEDORES ---

# Diccionario centralizado para configurar los proveedores de LLM.
# Facilita añadir o modificar proveedores en el futuro.
PROVIDERS = {
    "Groq": {
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "host": "api.groq.com",
        "api_key": os.getenv("GROQ_API_KEY"),
        "model": "llama-3.1-8b-instant",
    },
    "Google": {
        "api_url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "host": "generativelanguage.googleapis.com",
        "api_key": os.getenv("GOOGLE_API_KEY"),
        "model": "gemini-1.5-flash-8b",
    },
    "Fireworks.ai": {
        "api_url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "host": "api.fireworks.ai",
        "api_key": os.getenv("FIREWORKS_API_KEY"),
        "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
    },
    "Together.ai": {
        "api_url": "https://api.together.xyz/v1/chat/completions",
        "host": "api.together.xyz",
        "api_key": os.getenv("TOGETHER_API_KEY"),
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    },
    "Industria Predicta": {
        "api_url": "http://localhost:11434/api/chat",
        "host": "localhost",
        "api_key": "ollama", # No se requiere API Key real
        "model": "llama3.1",
    }
}

# --- FUNCIONES DE RED Y PROCESAMIENTO (WORKERS) ---

def get_traceroute(host):
    """Ejecuta un traceroute al host y devuelve el resultado como texto."""
    if host == "localhost":
        return "Traceroute no aplica para localhost."
    try:
        command = ["tracert", "-w", "100", host] if platform.system() == "Windows" else ["traceroute", "-w", "1", "-m", "15", host]
        process = subprocess.run(command, capture_output=True, text=True, timeout=45, encoding='utf-8', errors='replace')
        if process.returncode == 0:
            return process.stdout
        return f"Traceroute finalizó con error:\n{process.stderr}"
    except FileNotFoundError:
        return f"Error: Comando no encontrado. Asegúrate de que 'traceroute' o 'tracert' esté instalado."
    except subprocess.TimeoutExpired:
        return "Error: Traceroute tardó demasiado (timeout)."
    except Exception as e:
        return f"Error inesperado en traceroute: {e}"

def get_llm_response(provider_name, prompt):
    """Prepara y envía la petición a la API del proveedor, devolviendo la respuesta."""
    provider = PROVIDERS[provider_name]
    api_url = provider["api_url"]
    api_key = provider["api_key"]
    model = provider["model"]
    
    if not api_key:
        raise ValueError(f"API key para {provider_name} no encontrada. Revisa tu .env")

    headers = {"Content-Type": "application/json"}
    messages = [{"role": "user", "content": prompt}]
    
    # Adaptar el cuerpo y cabeceras de la petición a cada API
    if provider_name in ["Groq", "Fireworks.ai", "Together.ai"]:
        headers["Authorization"] = f"Bearer {api_key}"
        data = {"model": model, "messages": messages, "max_tokens": 256}
    elif provider_name == "Google":
        api_url += f"?key={api_key}"
        data = {"contents": [{'parts': [{'text': m['content']}] for m in messages}]}
    elif provider_name == "Industria Predicta":
        data = {"model": model, "messages": messages, "stream": False}
    else:
        raise NotImplementedError(f"Formato de API para {provider_name} no implementado.")

    response = requests.post(api_url, headers=headers, json=data, timeout=120)
    response.raise_for_status()
    
    # Extraer el contenido de la respuesta, que varía entre APIs
    resp_json = response.json()
    if provider_name in ["Groq", "Fireworks.ai", "Together.ai"]:
        return resp_json["choices"][0]["message"]["content"]
    elif provider_name == "Industria Predicta":
        return resp_json["message"]["content"]
    elif provider_name == "Google":
        return resp_json["candidates"][0]["content"]["parts"][0]["text"]
    return "Error al parsear la respuesta."

def benchmark_worker(provider_name, prompt, result_queue):
    """
    Función "trabajador" que se ejecuta en un hilo.
    Realiza el traceroute y la llamada a la API para un proveedor.
    """
    result = {"provider": provider_name}
    try:
        start_time = time.monotonic()
        
        # Ejecutar traceroute y llamada a la API en paralelo dentro del hilo
        # para optimizar aún más el tiempo.
        with threading.Lock(): # Usamos un lock para futuras extensiones si fuera necesario
            llm_thread = threading.Thread(target=lambda q, arg1, arg2: q.put(get_llm_response(arg1, arg2)), args=(response_q := queue.Queue(), provider_name, prompt))
            trace_thread = threading.Thread(target=lambda q, arg1: q.put(get_traceroute(arg1)), args=(trace_q := queue.Queue(), PROVIDERS[provider_name]['host']))
            
            llm_thread.start()
            trace_thread.start()
            
            llm_thread.join()
            trace_thread.join()
            
            result["response"] = response_q.get()
            result["traceroute"] = trace_q.get()

        latency = time.monotonic() - start_time
        result["latency"] = latency
    except Exception as e:
        result["error"] = str(e)
    
    result_queue.put(result)


# --- INTERFAZ DE USUARIO (UI) ---

# Campo de entrada de texto
prompt = st.text_input("Introduce un prompt para el benchmark:", key="prompt_input")
start_button = st.button("🚀 Iniciar Benchmark", type="primary")

# Crear columnas para los resultados
columns = st.columns(len(PROVIDERS))
placeholders = {name: col.empty() for name, col in zip(PROVIDERS.keys(), columns)}

# Lógica principal de ejecución del benchmark
if start_button and prompt:
    result_queue = queue.Queue()
    threads = []
    
    # Inicializar placeholders con spinners
    for provider_name, placeholder in placeholders.items():
        with placeholder.container():
            st.subheader(provider_name)
            st.metric("Latencia", "...")
            st.text_area("Respuesta", "Cargando...", height=200, key=f"resp_{provider_name}")
            with st.expander("Ver Traceroute"):
                st.code("Cargando...")

    # Lanzar un hilo por cada proveedor
    for provider_name in PROVIDERS.keys():
        thread = threading.Thread(
            target=benchmark_worker,
            args=(provider_name, prompt, result_queue)
        )
        threads.append(thread)
        thread.start()

    # Bucle para recoger resultados y actualizar la UI sin congelarla
    completed_threads = 0
    while completed_threads < len(PROVIDERS):
        try:
            # Esperar por el próximo resultado en la cola
            result = result_queue.get(timeout=1.0)
            provider_name = result["provider"]
            
            # Actualizar el placeholder correspondiente con el resultado
            with placeholders[provider_name].container():
                st.subheader(provider_name)
                if "error" in result:
                    st.error(f"Error: {result['error']}", icon="🔥")
                else:
                    st.metric("Latencia", f"{result['latency']:.2f} s")
                    st.text_area("Respuesta", result["response"], height=200, key=f"resp_{provider_name}_done")
                    with st.expander("Ver Traceroute", expanded=False):
                        st.code(result["traceroute"])

            completed_threads += 1
        except queue.Empty:
            # Si la cola está vacía, simplemente continuamos el bucle,
            # permitiendo que la UI se mantenga reactiva.
            pass
    
    # Asegurarse de que todos los hilos han terminado
    for thread in threads:
        thread.join()

