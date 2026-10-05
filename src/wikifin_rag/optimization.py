import argparse
import json
import pickle

import numpy as np
import pandas as pd
from hyperopt import STATUS_OK, Trials, fmin, hp, tpe
from hyperopt.pyll import scope

from wikifin_rag.config import PROJECT_ROOT
from wikifin_rag.db_client import DocumentsDBClient
from wikifin_rag.embedder import Embedder
from wikifin_rag.evaluation_utils import evaluate
from wikifin_rag.search_utils import (
    build_text_index,
    build_vector_index,
    text_search,
    vector_search,
)

GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "evals" / "retrieval_ground_truth.csv"
EVALS_DIR = PROJECT_ROOT / "data" / "evals"
PARAMS_PATH = PROJECT_ROOT / "config" / "search_params.json"
EVAL_SPLIT = 0.25
SPLIT_RANDOM_STATE = 1
DEFAULT_MAX_EVALS = 10


def _load_documents():
    db_client = DocumentsDBClient()

    with db_client.get_db_connection() as connection:
        connection.row_factory = lambda _, row: {
            "id": row[0],
            "title": row[1],
            "section": row[2],
            "content": row[3],
            "embedding": np.frombuffer(row[4]),
            "source_url": row[5],
        }
        rows = connection.execute(
            """
            SELECT
                c.document_id || '_' || c.chunk_id AS id,
                d.title,
                d.section,
                c.content,
                c.embedding,
                d.source_url
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.language = 'nl';
            """
        ).fetchall()

    documents = rows
    embeddings = [document.pop("embedding") for document in documents]
    return documents, embeddings


def _load_optimization_ground_truth(path=GROUND_TRUTH_PATH):
    if not path.exists():
        raise FileNotFoundError(
            f"Ground-truth data not found at {path}. Generate it before running optimization."
        )

    ground_truth_df = pd.read_csv(path)
    required_columns = {"question", "document"}
    if not required_columns.issubset(ground_truth_df.columns):
        raise ValueError(f"Ground-truth data must contain columns: {sorted(required_columns)}")

    evaluation_df = ground_truth_df.sample(
        frac=EVAL_SPLIT,
        random_state=SPLIT_RANDOM_STATE,
    )
    optimization_df = ground_truth_df.drop(index=evaluation_df.index)
    optimization_ground_truth = optimization_df.to_dict(orient="records")

    if not optimization_ground_truth:
        raise ValueError("Ground-truth data has no records available for optimization.")

    return optimization_ground_truth


def _run_optimization(name, objective, search_space, max_evals, refresh):
    trials_path = EVALS_DIR / f"{name}_trials.pkl"
    if trials_path.exists() and not refresh:
        with trials_path.open("rb") as file:
            _, trials_data = pickle.load(file)
        best_params = max(trials_data, key=lambda trial: trial["mrr"])["params"]
        return best_params, trials_data

    trials = Trials()
    fmin(
        fn=objective,
        space=search_space,
        algo=tpe.suggest,
        max_evals=max_evals,
        trials=trials,
    )
    trials_data = [
        {
            "id": trial["tid"],
            "mrr": trial["result"]["metrics"]["mrr"],
            "hit_rate": trial["result"]["metrics"]["hit_rate"],
            "params": trial["result"]["params"],
        }
        for trial in trials.trials
    ]
    best_params = max(trials_data, key=lambda trial: trial["mrr"])["params"]

    trials_path.parent.mkdir(parents=True, exist_ok=True)
    with trials_path.open("wb") as file:
        pickle.dump((best_params, trials_data), file)

    return best_params, trials_data


def _text_search_space():
    return {
        "title": hp.uniform("title", 0, 10),
        "description": hp.uniform("description", 0, 10),
        "section": hp.uniform("section", 0, 10),
        "content": hp.uniform("content", 0, 10),
    }


def _vector_search_space():
    return hp.pchoice(
        "mode",
        [
            (
                0.8,
                {
                    "mode": "hnsw",
                    "m": hp.choice("m", [8, 12, 16, 24, 32]),
                    "ef_construction": hp.choice(
                        "ef_construction", [50, 100, 200, 400]
                    ),
                    "ef_search": hp.choice(
                        "ef_search", [10, 20, 40, 80, 160, 320]
                    ),
                },
            ),
            (
                0.1,
                {
                    "mode": "lsh",
                    "n_tables": scope.int(hp.quniform("lsh_n_tables", 2, 32, 1)),
                    "hash_size": scope.int(hp.quniform("lsh_hash_size", 8, 24, 1)),
                    "n_probe": scope.int(hp.quniform("lsh_n_probe", 0, 2, 1)),
                },
            ),
            (
                0.1,
                {
                    "mode": "ivf",
                    "n_clusters": hp.choice(
                        "n_clusters", [None, 32, 64, 128, 256, 512]
                    ),
                    "n_probe_clusters": scope.int(
                        hp.quniform("n_probe_clusters", 1, 32, 1)
                    ),
                },
            ),
        ],
    )


def optimize_parameters(
    max_evals=DEFAULT_MAX_EVALS,
    refresh=False,
    ground_truth_path=GROUND_TRUTH_PATH,
    params_path=PARAMS_PATH,
):
    if max_evals < 1:
        raise ValueError("max_evals must be at least 1.")

    ground_truth = _load_optimization_ground_truth(ground_truth_path)
    documents, embeddings = _load_documents()
    embedder = Embedder()

    text_index = build_text_index(documents=documents)

    def text_objective(params):
        metrics = evaluate(
            ground_truth=ground_truth,
            search_function=lambda query: text_search(
                query=query,
                index=text_index,
                boost_dict=params,
            ),
        )
        return {
            "loss": -round(metrics["mrr"], 4),
            "status": STATUS_OK,
            "params": params,
            "metrics": metrics,
        }

    text_params, text_trials = _run_optimization(
        "ts",
        text_objective,
        _text_search_space(),
        max_evals,
        refresh,
    )

    def vector_objective(params):
        vector_index = build_vector_index(
            vectors=embeddings,
            documents=documents,
            **params,
        )
        metrics = evaluate(
            ground_truth=ground_truth,
            search_function=lambda query: vector_search(
                index=vector_index,
                query=query,
                embedder=embedder,
            ),
        )
        return {
            "loss": -round(metrics["mrr"], 4),
            "status": STATUS_OK,
            "params": params,
            "metrics": metrics,
        }

    vector_params, vector_trials = _run_optimization(
        "vs",
        vector_objective,
        _vector_search_space(),
        max_evals,
        refresh,
    )

    build_vector_index(
        vectors=embeddings,
        documents=documents,
        **vector_params,
    )

    params_path.parent.mkdir(parents=True, exist_ok=True)
    params_path.write_text(
        json.dumps({"text": text_params, "vector": vector_params}, indent=2) + "\n",
        encoding="utf-8",
    )

    text_mrr = max(text_trials, key=lambda trial: trial["mrr"])["mrr"]
    vector_mrr = max(vector_trials, key=lambda trial: trial["mrr"])["mrr"]
    print(f"Text search best MRR: {text_mrr:.4f}")
    print(f"Vector search best MRR: {vector_mrr:.4f}")
    print(f"Search parameters written to {params_path}")

    return {"text": text_params, "vector": vector_params}


def main():
    parser = argparse.ArgumentParser(description="Optimize Wikifin search parameters.")
    parser.add_argument(
        "--max-evals",
        type=int,
        default=DEFAULT_MAX_EVALS,
        help="Number of Hyperopt trials to run for each search method.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cached trial results and run both optimizations again.",
    )
    args = parser.parse_args()
    optimize_parameters(max_evals=args.max_evals, refresh=args.refresh)


if __name__ == "__main__":
    main()
