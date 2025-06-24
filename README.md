# 🚀 Benchmark de Proveedores de LLMs

## 📋 Descripción
Este repositorio contiene una aplicación web sencilla para comparar el rendimiento y la latencia entre diferentes proveedores de Grandes Modelos de Lenguaje (LLMs).

Envía simultáneamente el mismo prompt a varios servicios de LLM como Groq, Google Gemini, Fireworks.ai, Together.ai y Ollama (self-hosted), y muestra las respuestas junto con la latencia y el traceroute de la petición en una interfaz visual clara. ¡Perfecto para probar y decidir qué proveedor se adapta mejor a tus necesidades en términos de facilidad de uso, velocidad y calidad de respuesta! 💡

## 🔧 Instalación

1. Clona el repositorio:

```bash 
git clone https://github.com/prsantiago/llm_provider_benchmark.git
cd llm_provider_benchmark
```

2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

3. Crea un archivo .env en la raíz del proyecto con tus claves API:

```bash
GROQ_API_KEY=tu_clave_groq
GOOGLE_API_KEY=tu_clave_google
FIREWORKS_API_KEY=tu_clave_fireworks
TOGETHER_API_KEY=tu_clave_together
```

Nota: Si deseas usar Ollama localmente, debes tenerlo instalado y ejecutándose en tu máquina.

## ▶️ Ejecución
Para iniciar la aplicación:

```bash
streamlit run app.py
```

Esto lanzará un servidor local y abrirá automáticamente la interfaz web en tu navegador predeterminado (normalmente en http://localhost:8501).

## 🎮 Cómo usar la aplicación
1. Escribe un prompt en el campo de entrada de texto
2. Presiona el botón "🚀 Iniciar Benchmark"
3. Observa cómo las respuestas aparecen en tiempo real para cada proveedor
4. Compara los tiempos de latencia y la calidad de las respuestas
5. Para ver información de red, expande la sección "Ver Traceroute" bajo cada respuesta

## 📝 Licencia
Este proyecto está bajo la Licencia MIT - consulta el archivo LICENSE para más detalles.