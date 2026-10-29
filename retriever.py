import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

POLICY_FILE = Path(__file__).parent / "data" / "policy_handbook.md"

TOP_K = 2              # maximum chunks returned per query
MIN_SCORE = 0.12       # below this, a chunk is treated as "not relevant"
RELATIVE_CUTOFF = 0.5  # extra chunks must score >= 50% of the best chunk
TITLE_WEIGHT = 3       # repeat the title so it counts more in matching


def _slug(title):
    """'Payment Portal Failure' -> 'payment-portal-failure'"""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def load_chunks(path=POLICY_FILE):
    """Split the handbook into chunks: one chunk per '## ' section."""
    text = Path(path).read_text(encoding="utf-8")
    sections = re.split(r"^## ", text, flags=re.MULTILINE)[1:]   # skip the '# ' title
    chunks = []
    for section in sections:
        title, _, body = section.partition("\n")
        title, body = title.strip(), body.strip()
        # Keywords help matching, but are not sent to the LLM (saves tokens)
        answer_text = re.sub(r"^\*\*Keywords:\*\*.*$", "", body, flags=re.MULTILINE).strip()
        chunks.append({
            "id": _slug(title),
            "title": title,
            "text": f"{title}\n{answer_text}",
            "index_text": f"{(title + ' ') * TITLE_WEIGHT}\n{body}",
        })
    if not chunks:
        raise ValueError(f"No '## ' sections found in {path}")
    return chunks


# ---- Build the index once, when the module is imported ----
CHUNKS = load_chunks()
VECTORIZER = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2),     # single words + word pairs ("late fee", "next working")
    sublinear_tf=True,      # stops very repeated words from dominating
)
MATRIX = VECTORIZER.fit_transform([c["index_text"] for c in CHUNKS])


def retrieve(query, k=TOP_K, min_score=MIN_SCORE):
    """
    Return the most relevant policy chunks for a query.

    Each result: {"id", "title", "text", "score"}.
    Returns [] if nothing is relevant (the agent then says the policy
    does not cover the question).
    """
    if not query or not query.strip():
        return []
    scores = cosine_similarity(VECTORIZER.transform([query]), MATRIX)[0]
    ranked = scores.argsort()[::-1]
    best = scores[ranked[0]]
    if best < min_score:
        return []
    results = []
    for i in ranked[:k]:
        s = scores[i]
        if s < min_score or s < best * RELATIVE_CUTOFF:
            break
        results.append({"id": CHUNKS[i]["id"], "title": CHUNKS[i]["title"],
                        "text": CHUNKS[i]["text"], "score": round(float(s), 3)})
    return results


if __name__ == "__main__":
    print(f"Loaded {len(CHUNKS)} chunks from {POLICY_FILE.name}")
    while True:
        q = input("\nQuery (blank to exit): ").strip()
        if not q:
            break
        hits = retrieve(q)
        if not hits:
            print("  -> No relevant policy found")
        for h in hits:
            print(f"  -> {h['title']}  (score {h['score']})")
            