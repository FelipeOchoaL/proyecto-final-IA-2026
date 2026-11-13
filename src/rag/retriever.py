"""RAG: un chunk por sección (## ...) de cada documento de data/corpus_rag, embeddings
multilingües (sentence-transformers) e índice FAISS de producto interno sobre vectores
normalizados (= similitud coseno).

Cada chunk conserva el archivo y la URL principal del documento para que el agente cite.
El índice se cachea en data/cache/rag/ y se reconstruye si cambia el corpus.
"""
import hashlib
import json
import re
from functools import lru_cache

import faiss
import numpy as np

from src.data.loader import CACHE, ROOT

CORPUS = ROOT / "data" / "corpus_rag"
INDEX_DIR = CACHE / "rag"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
URL_RE = re.compile(r"https?://[^\s)\]]+")


def chunk_corpus():
    chunks = []
    for path in sorted(CORPUS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parts = re.split(r"\n(?=## )", text)
        header = parts[0]
        title = header.splitlines()[0].lstrip("# ").strip()
        urls = URL_RE.findall(header)
        url = urls[0] if urls else ""
        for sec in parts[1:]:
            sec_title = sec.splitlines()[0].lstrip("# ").strip()
            if sec_title.lower() == "aviso":
                continue
            chunks.append({"archivo": path.name, "titulo": title, "seccion": sec_title, "url": url,
                           # el título del documento da contexto al embedding de la sección
                           "texto": f"{title}. {sec.strip()}"})
    return chunks


def _corpus_hash():
    h = hashlib.sha256(MODEL_NAME.encode())
    for p in sorted(CORPUS.glob("*.md")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def _index():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    key = _corpus_hash()
    idx_path, meta_path = INDEX_DIR / f"{key}.faiss", INDEX_DIR / f"{key}.json"
    if idx_path.exists() and meta_path.exists():
        return faiss.read_index(str(idx_path)), json.loads(meta_path.read_text(encoding="utf-8"))
    chunks = chunk_corpus()
    emb = _model().encode([c["texto"] for c in chunks], normalize_embeddings=True)
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(np.asarray(emb, dtype="float32"))
    faiss.write_index(index, str(idx_path))
    meta_path.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    return index, chunks


def search_docs(query: str, k: int = 4) -> list:
    """Top-k secciones más similares a la consulta, con su fuente."""
    if not query or not query.strip():
        raise ValueError("La consulta está vacía.")
    index, chunks = _index()
    q = _model().encode([query], normalize_embeddings=True).astype("float32")
    scores, ids = index.search(q, min(k, len(chunks)))
    return [{**chunks[i], "score": round(float(s), 3)} for s, i in zip(scores[0], ids[0]) if i >= 0]
