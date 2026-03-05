import json
import os
import time
import sys
import requests
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# ==========================================
# CONFIGURACIÓN
# ==========================================
load_dotenv()
API_KEY = os.environ.get("CHATBOT_API_KEY")

if not API_KEY:
    print("❌ ERROR FATAL: No se encontró la CHATBOT_API_KEY en el archivo .env")
    sys.exit(1)

API_URL = "http://localhost:8000/chat"
SESSION_ID = "test_session_suite_01"
DELAY_SECONDS = 1 # Lo mantenemos en 10s si tienes activado el Rate Limit estricto, o bájalo a 1 si tienes el bypass

# Headers con la clave real
HEADERS = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY,
    "Origin": "http://localhost:5173"
}
# ==========================================
# FUNCIÓN DEL JUEZ ESTRICTO
# ==========================================
def evaluate_dataset(dataset_path, run_folder):
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    total_tests = len(dataset)
    nombre_archivo = os.path.basename(dataset_path)

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

    # Configuramos la zona horaria a UTC-5 (Hora de Colombia)
    zona_local = timezone(timedelta(hours=-5))
    fecha_actual = datetime.now(zona_local).strftime("%Y-%m-%d %H:%M:%S")

    report_name = f"report_{nombre_archivo.replace('.json', '.txt')}"
    report_path = os.path.join(run_folder, report_name)

    report_lines = [
        f"REPORTE DE LOTE: {nombre_archivo}",
        f"FECHA LOCAL: {fecha_actual}",
        f"{'='*60}\n"
    ]

    for i, test in enumerate(dataset, 1):
        test_id = test['id']
        category = test.get('category', 'uncategorized')
        test_type = test.get('test_type', 'standard')

        metrics['categories'][category]['total'] += 1
        metrics['types'][test_type]['total'] += 1

        payload = {"session_id": SESSION_ID, "question": test['question']}
        start_time = time.time()

        try:
            response = requests.post(API_URL, json=payload, headers=HEADERS)
            response.raise_for_status()

            latency = round(time.time() - start_time, 2)
            data = response.json()
            bot_reply = data.get("answer", "")
            sources_used = data.get("sources", [])
            reply_lower = bot_reply.lower().strip()

            retrieval_pass = True
            retrieval_msg = ""
            generation_pass = False
            gen_fail_reason = ""

            expected_retrieval = test.get('expected_retrieval', "IGNORE")
            forbidden_claims = test.get('forbidden_claims', [])
            allowed_patterns = test.get('allowed_response_patterns', [])
            is_guardrail = test_type in ["guardrail_trigger", "out_of_scope"]

            # --- FASE 1: RETRIEVAL ---
            precision_score = 0.0
            if expected_retrieval != "IGNORE":
                real_sources = [s for s in sources_used if s.endswith('.md')]
                if isinstance(expected_retrieval, list):
                    if len(real_sources) > 0:
                        hits = len(set(expected_retrieval).intersection(set(real_sources)))
                        precision_score = hits / len(real_sources)
                    elif len(expected_retrieval) == 0:
                        precision_score = 1.0
                    else:
                        precision_score = 0.0

                    metrics['total_retrieval_precision'] += precision_score
                    metrics['retrieval_precision_count'] += 1

                    if len(expected_retrieval) == 0:
                        if real_sources:
                            retrieval_pass = False
                            retrieval_msg = f"Retrieval Falló: Se esperaban 0 documentos, obtuvo {real_sources}"
                    else:
                        if not set(expected_retrieval).issubset(set(real_sources)):
                            retrieval_pass = False
                            retrieval_msg = f"Retrieval Falló: Esperaba {expected_retrieval}, obtuvo {real_sources}"

            # --- FASE 2: GENERATION ---
            if len(bot_reply) < 10:
                gen_fail_reason = "Respuesta demasiado corta (posible evasiva)."
            else:
                hallucinated = [claim for claim in forbidden_claims if claim.lower() in reply_lower]
                if hallucinated:
                    gen_fail_reason = f"Alucinación detectada: {hallucinated}"
                    metrics['hallucinations'] += 1
                else:
                    if allowed_patterns:
                        if is_guardrail:
                            if reply_lower.startswith(tuple(p.lower() for p in allowed_patterns)):
                                generation_pass = True
                            else:
                                gen_fail_reason = "No INICIA con el patrón de rechazo esperado."
                        else:
                            if any(pattern.lower() in reply_lower for pattern in allowed_patterns):
                                generation_pass = True
                            else:
                                gen_fail_reason = "No contiene el patrón esperado."
                    else:
                        generation_pass = True

            # --- VEREDICTO ---
            status = "✅ PASS" if (retrieval_pass and generation_pass) else "❌ FAIL"
            if status == "✅ PASS":
                metrics['passed'] += 1
                metrics['categories'][category]['pass'] += 1
                metrics['types'][test_type]['pass'] += 1

            print(f"[{i}/{total_tests}] {test_id} | {status} ({latency}s) | {test_type}")
            if not retrieval_pass: print(f"   └─ 🔎 {retrieval_msg} | Precisión: {precision_score*100:.1f}%")
            if not generation_pass: print(f"   └─ 🧠 {gen_fail_reason}")

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

        if i < total_tests:
            time.sleep(DELAY_SECONDS)

    # --- DASHBOARD ---
    global_acc = (metrics['passed'] / metrics['total']) * 100 if metrics['total'] > 0 else 0
    avg_precision = (metrics['total_retrieval_precision'] / metrics['retrieval_precision_count'] * 100) if metrics['retrieval_precision_count'] > 0 else 0.0

    report_lines.append("\n" + "="*60)
    report_lines.append(f"📊 DASHBOARD DE MÉTRICAS - {nombre_archivo}")
    report_lines.append("="*60)
    report_lines.append(f"Precisión Global: {metrics['passed']}/{metrics['total']} ({global_acc:.1f}%)")
    report_lines.append(f"Precisión del Buscador: {avg_precision:.1f}%")
    report_lines.append(f"Alucinaciones: {metrics['hallucinations']}\n")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    return metrics['passed'], metrics['total'], global_acc

# ==========================================
# BLOQUE DE EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    # 1. Obtenemos la hora local exacta
    zona_local = timezone(timedelta(hours=-5))
    timestamp = datetime.now(zona_local).strftime("%Y%m%d_%H%M%S")

    # 2. Creamos una carpeta ÚNICA para esta ejecución
    run_folder = f"tests/reports/run_{timestamp}"
    os.makedirs(run_folder, exist_ok=True)

    # Ruta estricta para correr SOLO el lote 2
    lote_2_path = "tests/datasets/test_lote_2_seguridad.json"

    print(f"🚀 INICIANDO TEST SUITE (MODO ESTRICTO)")
    print(f"📁 Reportes guardados en: {run_folder}")

    if os.path.exists(lote_2_path):
        evaluate_dataset(lote_2_path, run_folder)
    else:
        print(f"❌ ERROR: No se encontró el archivo {lote_2_path}")

    print(f"\n🏁 PRUEBA FINALIZADA. Revisa la carpeta {run_folder}")