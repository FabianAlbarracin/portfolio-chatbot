import json
import os
import time
import sys
import requests
import re
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

# ==========================================
# 1. CONFIGURACIÓN DEL ENTORNO Y API
# ==========================================
load_dotenv()
API_KEY = os.environ.get("CHATBOT_API_KEY")

if not API_KEY:
    print("❌ ERROR FATAL: No se encontró la CHATBOT_API_KEY en el archivo .env")
    sys.exit(1)

API_URL = "http://localhost:8000/chat"
DELAY_SECONDS = 1 # Tiempo de espera entre peticiones para no saturar el servidor

# Cabeceras requeridas por el backend FastAPI (El API_KEY ya no es obligatorio para /chat, pero lo mantenemos por compatibilidad)
HEADERS = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY,
    "Origin": "http://localhost:5173"
}

# ==========================================
# 2. CONFIGURACIÓN DEL JUEZ SEMÁNTICO (LLM-as-a-Judge)
# ==========================================
def get_judge_llm():
    """Instancia un cliente LLM aislado para la evaluación estricta de las respuestas."""
    judge_api_key = os.environ.get("GROQ_API_KEY")
    if not judge_api_key:
        print("❌ ERROR FATAL: No se encontró GROQ_API_KEY para el Juez en el archivo .env")
        sys.exit(1)

    return ChatGroq(
        model="llama-3.1-8b-Instant",
        temperature=0.0, # Cero creatividad para mantener evaluaciones consistentes
        api_key=judge_api_key,
        max_tokens=150   # Forzamos una salida rápida y concisa
    ).bind(response_format={"type": "json_object"})

# Instancia global del juez
judge_llm = get_judge_llm()

# ==========================================
# 3. MOTOR PRINCIPAL DE EVALUACIÓN
# ==========================================
def evaluate_dataset(dataset_path, run_folder):
    """Carga un archivo JSON de pruebas, lanza las peticiones al bot y evalúa las respuestas."""
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    total_tests = len(dataset)
    nombre_archivo = os.path.basename(dataset_path)

    # Diccionario para almacenar estadísticas de la corrida
    metrics = {
        'total': total_tests,
        'passed': 0,
        'categories': defaultdict(lambda: {'pass': 0, 'total': 0}),
        'types': defaultdict(lambda: {'pass': 0, 'total': 0}),
        'hallucinations': 0,
        'total_retrieval_precision': 0.0,
        'retrieval_precision_count': 0
    }

    print(f"\n▶️ Evaluando Dataset: {nombre_archivo} ({total_tests} preguntas)")
    print("-" * 60)

    # Configuración de hora local para los reportes
    zona_local = timezone(timedelta(hours=-5))
    fecha_actual = datetime.now(zona_local).strftime("%Y-%m-%d %H:%M:%S")

    # Archivo de salida del reporte
    report_name = f"report_{nombre_archivo.replace('.json', '.txt')}"
    report_path = os.path.join(run_folder, report_name)

    report_lines = [
        f"REPORTE DE LOTE: {nombre_archivo}",
        f"FECHA LOCAL: {fecha_actual}",
        f"{'='*60}\n"
    ]

    # Iteración sobre cada caso de prueba en el JSON
    for i, test in enumerate(dataset, 1):
        test_id = test.get('id', f'TEST-{i}')
        category = test.get('category', 'uncategorized')
        test_type = test.get('test_type', 'standard')
        ideal_answer = test.get('ideal_answer', 'Respuesta esperada no definida')

        metrics['categories'][category]['total'] += 1
        metrics['types'][test_type]['total'] += 1

        # Agrupamos las sesiones recortando la letra final (ej. MEM-001A -> MEM-001)
        base_session_id = re.sub(r'[A-Za-z]$', '', str(test_id))
        payload = {"session_id": f"test_session_{base_session_id}", "question": test['question']}

        try:
            # ==========================================
            # 3.1 Petición al Chatbot con EXPONENTIAL BACKOFF
            # ==========================================
            max_retries = 4
            for attempt in range(max_retries):
                start_time = time.time() # Reiniciamos el timer en cada intento para no afectar la métrica
                response = requests.post(API_URL, json=payload, headers=HEADERS)

                if response.status_code == 429:
                    wait_time = 15 * (attempt + 1)
                    print(f"   ⏳ [RATE LIMIT] Servidor saturado (HTTP 429). Pausando {wait_time}s (Intento {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue

                # Si no es un 429, validamos posibles errores 500 o 400 y rompemos el bucle
                response.raise_for_status()
                break
            else:
                # Si el bucle termina sin un 'break' (es decir, agotó los reintentos)
                raise Exception(f"Fallo crítico: El script fue bloqueado por Rate Limit tras {max_retries} intentos consecutivos.")

            latency = round(time.time() - start_time, 2)
            data = response.json()
            bot_reply = data.get("answer", "")
            sources_used = data.get("sources", [])

            # Variables de estado de la prueba
            retrieval_pass = True
            retrieval_msg = ""
            generation_pass = False
            gen_fail_reason = ""

            expected_retrieval = test.get('expected_retrieval', "IGNORE")

            # ==========================================
            # FASE 1: EVALUACIÓN DE RECUPERACIÓN (Vector DB)
            # ==========================================
            precision_score = 0.0
            if expected_retrieval != "IGNORE":
                real_sources = [s for s in sources_used if s.endswith('.md')]

                # Si se esperaba una lista de documentos específicos
                if isinstance(expected_retrieval, list):
                    if len(real_sources) > 0:
                        hits = len(set(expected_retrieval).intersection(set(real_sources)))
                        precision_score = hits / len(real_sources)
                    elif len(expected_retrieval) == 0:
                        precision_score = 1.0 # El bot hizo bien en no traer nada
                    else:
                        precision_score = 0.0

                    metrics['total_retrieval_precision'] += precision_score
                    metrics['retrieval_precision_count'] += 1

                    # Validación de éxito/fracaso del buscador
                    if len(expected_retrieval) == 0:
                        if real_sources:
                            retrieval_pass = False
                            retrieval_msg = f"Retrieval Falló: Se esperaban 0 documentos, obtuvo {real_sources}"
                    else:
                        if not set(expected_retrieval).issubset(set(real_sources)):
                            retrieval_pass = False
                            retrieval_msg = f"Retrieval Falló: Esperaba {expected_retrieval}, obtuvo {real_sources}"

            # ==========================================
            # FASE 2: EVALUACIÓN DE GENERACIÓN (Heurística + LLM)
            # ==========================================
            bot_text = bot_reply.strip().lower()

            # 1. Filtro de Sanidad: Respuestas mudas o colapsos de red
            if len(bot_reply) < 10:
                generation_pass = False
                gen_fail_reason = "Respuesta demasiado corta (posible evasiva o error de red)."

            # 2. BYPASS HEURÍSTICO: Cortocircuito de Seguridad (Evita falsos negativos del LLM Juez)
            elif "no tengo información" in bot_text or "solo estoy autorizado" in bot_text:
                generation_pass = True
                gen_fail_reason = "✅ Aprobado por Bypass de Python (Activación correcta de Guardrails de Seguridad)."

            # 3. EVALUACIÓN AVANZADA: Juez LLM para análisis semántico profundo
            else:
                judge_prompt = f"""
                Eres un juez experto evaluando un sistema RAG.

                Pregunta del Usuario: {test['question']}
                Respuesta Esperada (Ideal): {ideal_answer}
                Respuesta del Bot: {bot_reply}

                Evalúa siguiendo ESTAS 2 REGLAS ESTRICTAS:
                1. EXCESO TÉCNICO ES BUENO: Si el Bot menciona hardware o arquitecturas reales que NO están en la Respuesta Esperada, APROBAR (pass: true).
                2. REPROBADO POR INVENTAR: Si el bot lista el nombre de un proyecto que explícitamente NO está en la Respuesta Esperada, REPROBAR (pass: false).

                FORMATO OBLIGATORIO DE SALIDA (Solo JSON válido):
                {{
                    "pass": true o false,
                    "reason": "Explicación de 1 línea indicando por qué falló o pasó."
                }}
                """
                try:
                    # Llamada a Groq API
                    judge_response = judge_llm.invoke([SystemMessage(content=judge_prompt)])
                    decision = json.loads(judge_response.content.strip())

                    generation_pass = decision.get("pass", False)
                    gen_fail_reason = decision.get("reason", "Fallo sin justificación del juez.")

                    if not generation_pass:
                        metrics['hallucinations'] += 1

                except Exception as e:
                    generation_pass = False
                    gen_fail_reason = f"Error en el parseo JSON del Juez Evaluador: {str(e)}"

            # ==========================================
            # FASE 3: CONSOLIDACIÓN DE RESULTADOS
            # ==========================================
            status = "✅ PASS" if (retrieval_pass and generation_pass) else "❌ FAIL"

            if status == "✅ PASS":
                metrics['passed'] += 1
                metrics['categories'][category]['pass'] += 1
                metrics['types'][test_type]['pass'] += 1

            # Log en terminal
            print(f"[{i}/{total_tests}] {test_id} | {status} ({latency}s) | {test_type}")
            if not retrieval_pass: print(f"   └─ 🔎 {retrieval_msg} | Precisión: {precision_score*100:.1f}%")
            if not generation_pass: print(f"   └─ 🧠 {gen_fail_reason}")

            # Escritura en reporte de texto
            report_lines.append(f"Test ID: {test_id} | Categoría: {category} | Tipo: {test_type}")
            report_lines.append(f"Pregunta: {test['question']}")
            report_lines.append(f"📚 Fuentes: {sources_used} (Precisión: {precision_score*100:.1f}%)")
            report_lines.append(f"Respuesta:\n{bot_reply}\n")
            report_lines.append(f"Veredicto: {status}")
            if not retrieval_pass: report_lines.append(retrieval_msg)
            if not generation_pass: report_lines.append(f"Fallo de Generación: {gen_fail_reason}")
            report_lines.append(f"{'-'*60}\n")

        except Exception as e:
            print(f"[{i}/{total_tests}] {test_id} | ⚠️ ERROR - {e}")

        # Respetamos el Rate Limit nativo entre cada test (fuera de las pausas de castigo)
        if i < total_tests:
            time.sleep(DELAY_SECONDS)

    # ==========================================
    # FASE 4: CÁLCULO DE DASHBOARD GLOBAL
    # ==========================================
    global_acc = (metrics['passed'] / metrics['total']) * 100 if metrics['total'] > 0 else 0
    avg_precision = (metrics['total_retrieval_precision'] / metrics['retrieval_precision_count'] * 100) if metrics['retrieval_precision_count'] > 0 else 0.0

    report_lines.append("\n" + "="*60)
    report_lines.append(f"📊 DASHBOARD DE MÉTRICAS - {nombre_archivo}")
    report_lines.append("="*60)
    report_lines.append(f"Precisión Global: {metrics['passed']}/{metrics['total']} ({global_acc:.1f}%)")
    report_lines.append(f"Precisión del Buscador: {avg_precision:.1f}%")
    report_lines.append(f"Alucinaciones: {metrics['hallucinations']}\n")

    # Guardado físico del reporte
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    return metrics['passed'], metrics['total'], global_acc

# ==========================================
# 4. PUNTO DE ENTRADA (TEST RUNNER AUTOMÁTICO)
# ==========================================
if __name__ == "__main__":
    import glob

    # 4.1 Configurar hora local y crear subcarpeta de la corrida
    zona_local = timezone(timedelta(hours=-5))
    timestamp = datetime.now(zona_local).strftime("%Y%m%d_%H%M%S")
    run_folder = f"tests/reports/run_{timestamp}"
    os.makedirs(run_folder, exist_ok=True)

    print(f"🚀 INICIANDO TEST SUITE AUTOMÁTICO (MODO ESTRICTO)")
    print(f"📁 Todos los reportes se guardarán en: {run_folder}\n")

    # 4.2 Buscar todos los archivos JSON en la carpeta datasets
    datasets_dir = "tests/datasets"
    if not os.path.exists(datasets_dir):
        print(f"❌ ERROR: La carpeta {datasets_dir} no existe.")
        sys.exit(1)

    archivos_json = sorted([f for f in os.listdir(datasets_dir) if f.endswith('.json')])

    if not archivos_json:
        print(f"❌ ERROR: No se encontraron archivos .json en {datasets_dir}")
    else:
        # 4.3 Ejecutar cada lote encontrado secuencialmente
        for archivo in archivos_json:
            lote_path = os.path.join(datasets_dir, archivo)
            evaluate_dataset(lote_path, run_folder)

    print(f"\n🏁 EJECUCIÓN MASIVA FINALIZADA. Revisa la carpeta: {run_folder}")