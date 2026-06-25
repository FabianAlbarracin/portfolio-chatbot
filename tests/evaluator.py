import json
import os
import time
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8000/chat"
API_KEY = os.environ.get("CHATBOT_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "http://localhost:5173",
}

if not GROQ_API_KEY:
    print("ERROR FATAL: GROQ_API_KEY no configurada en .env (requerida para RAGAS)")
    sys.exit(1)

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import ContextRelevancy, Faithfulness, AnswerRelevancy
from ragas.dataset_schema import SingleTurnSample


zona_local = timezone(timedelta(hours=-5))
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

evaluator_llm = LangchainLLMWrapper(ChatGroq(
    model="llama-3.1-8b-Instant",
    temperature=0.0,
    api_key=GROQ_API_KEY,
))

metrics = [
    ContextRelevancy(llm=evaluator_llm),
    Faithfulness(llm=evaluator_llm),
    AnswerRelevancy(llm=evaluator_llm),
]


def load_datasets(datasets_dir: str) -> dict[str, list[dict]]:
    datasets = {}
    for fname in sorted(os.listdir(datasets_dir)):
        if fname.endswith(".json"):
            with open(os.path.join(datasets_dir, fname), "r", encoding="utf-8") as f:
                datasets[fname] = json.load(f)
    return datasets


def evaluate_dataset(
    name: str,
    tests: list[dict],
    db: Chroma,
    run_folder: str,
) -> dict:
    timestamp = datetime.now(zona_local).strftime("%Y-%m-%d %H:%M:%S")

    stats = {
        "total": len(tests),
        "scored": 0,
        "blocked_count": 0,
        "context_relevancy": 0.0,
        "faithfulness": 0.0,
        "answer_relevancy": 0.0,
        "categories": defaultdict(lambda: {"total": 0, "scored": 0}),
    }

    report_name = f"report_{name.replace('.json', '.txt')}"
    report_path = os.path.join(run_folder, report_name)
    report_lines = [
        f"REPORTE RAGAS: {name}",
        f"FECHA LOCAL: {timestamp}",
        f"{'=' * 60}\n",
    ]

    samples = []
    results = []

    for i, test in enumerate(tests, 1):
        test_id = test.get("id", f"TEST-{i}")
        category = test.get("category", "uncategorized")
        question = test["question"]
        ideal = test.get("ideal_answer", "")
        expected_retrieval = test.get("expected_retrieval", [])

        stats["categories"][category]["total"] += 1

        delay = 0.5 if i > 1 else 0
        if delay:
            time.sleep(delay)

        try:
            base_session = test_id.split("-")[0] if "-" in test_id else test_id
            base_session = base_session.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
            session_id = f"eval_{base_session}"

            resp = requests.post(
                API_URL,
                json={"question": question, "session_id": session_id},
                headers=HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            answer = data.get("answer", "")
            sources = data.get("sources", [])
            blocked = data.get("blocked", False)
            confidence = data.get("confidence", "high")

            if blocked:
                stats["blocked_count"] += 1

            docs = db.similarity_search(question, k=6)
            contexts = [doc.page_content for doc in docs]

            sample = SingleTurnSample(
                user_input=question,
                response=answer,
                reference=ideal,
                retrieved_contexts=contexts,
            )
            samples.append(sample)
            results.append({
                "id": test_id,
                "category": category,
                "question": question,
                "answer": answer[:300],
                "sources": sources,
                "blocked": blocked,
                "confidence": confidence,
            })

            status = "BLOCKED" if blocked else "OK"
            print(f"[{i}/{len(tests)}] {test_id} | {status} | {category}")

        except Exception as e:
            print(f"[{i}/{len(tests)}] {test_id} | ERROR - {e}")
            results.append({
                "id": test_id,
                "category": category,
                "question": question,
                "answer": f"ERROR: {e}",
                "sources": [],
                "blocked": True,
                "confidence": "low",
            })

    if samples:
        print(f"\n  Evaluando {len(samples)} muestras con RAGAS...")
        try:
            scores = evaluate(samples, metrics)

            cr_score = float(scores.get("context_relevancy", 0) or 0)
            fa_score = float(scores.get("faithfulness", 0) or 0)
            ar_score = float(scores.get("answer_relevancy", 0) or 0)

            stats["scored"] = len(samples)
            stats["context_relevancy"] = round(cr_score, 4)
            stats["faithfulness"] = round(fa_score, 4)
            stats["answer_relevancy"] = round(ar_score, 4)

            report_lines.append(f"RAGAS Context Relevancy:  {cr_score:.4f}")
            report_lines.append(f"RAGAS Faithfulness:       {fa_score:.4f}")
            report_lines.append(f"RAGAS Answer Relevancy:   {ar_score:.4f}")

            if isinstance(scores, dict):
                for key, val in scores.items():
                    if key not in ("context_relevancy", "faithfulness", "answer_relevancy"):
                        report_lines.append(f"  {key}: {val}")

            print(f"  Context Relevancy: {cr_score:.4f}")
            print(f"  Faithfulness:      {fa_score:.4f}")
            print(f"  Answer Relevancy:  {ar_score:.4f}")
        except Exception as e:
            print(f"  ERROR en evaluacion RAGAS: {e}")
            report_lines.append(f"ERROR RAGAS: {e}")

    report_lines.append(f"\n{'=' * 60}")
    report_lines.append(f"Total: {stats['total']} | Bloqueados: {stats['blocked_count']} | Evaluados por RAGAS: {stats['scored']}")

    for r in results:
        report_lines.append(f"\nTest ID: {r['id']} | Categoria: {r['category']}")
        report_lines.append(f"Pregunta: {r['question']}")
        report_lines.append(f"Fuentes: {r['sources']}")
        report_lines.append(f"Bloqueado: {r['blocked']} | Confianza: {r['confidence']}")
        report_lines.append(f"Respuesta:\n{r['answer']}\n")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    return stats


if __name__ == "__main__":
    datasets_dir = "tests/datasets"
    if not os.path.exists(datasets_dir):
        print(f"ERROR: La carpeta {datasets_dir} no existe.")
        sys.exit(1)

    db_path = os.path.join("data", "chroma_db")
    db = Chroma(persist_directory=db_path, embedding_function=embeddings)

    timestamp = datetime.now(zona_local).strftime("%Y%m%d_%H%M%S")
    run_folder = f"tests/reports/run_{timestamp}"
    os.makedirs(run_folder, exist_ok=True)

    print("INICIANDO EVALUACION RAGAS v2.0")
    print(f"Reportes en: {run_folder}\n")

    datasets = load_datasets(datasets_dir)

    all_stats = {}
    total_tests = 0
    total_scored = 0

    for name, tests in datasets.items():
        print(f"\n{'=' * 60}")
        print(f"Evaluando: {name} ({len(tests)} preguntas)")
        print(f"{'=' * 60}")
        stats = evaluate_dataset(name, tests, db, run_folder)
        all_stats[name] = stats
        total_tests += stats["total"]
        total_scored += stats["scored"]

    summary_path = os.path.join(run_folder, "summary.json")
    summary = {
        "timestamp": datetime.now(zona_local).isoformat(),
        "total_tests": total_tests,
        "total_scored": total_scored,
        "datasets": {},
    }

    for name, stats in all_stats.items():
        summary["datasets"][name] = {
            "total": stats["total"],
            "scored": stats["scored"],
            "blocked": stats["blocked_count"],
            "context_relevancy": stats["context_relevancy"],
            "faithfulness": stats["faithfulness"],
            "answer_relevancy": stats["answer_relevancy"],
        }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"EVALUACION COMPLETA. {total_tests} tests, {total_scored} evaluados por RAGAS.")
    print(f"Reportes en: {run_folder}")
    print(f"Resumen JSON: {summary_path}")
