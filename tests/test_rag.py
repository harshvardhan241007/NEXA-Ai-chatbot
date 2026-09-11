from app.rag import chunk_text, TfidfIndex, DocumentStore


def test_chunk_text_splits_long_text():
    text = "word " * 1000
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 220 for c in chunks)


def test_chunk_text_empty_returns_empty():
    assert chunk_text("") == []


def test_tfidf_retrieves_relevant_chunk():
    chunks = [
        "The refund policy allows returns within 30 days of purchase.",
        "Our office is located in Jaipur, Rajasthan.",
        "Cats are small domesticated carnivorous mammals.",
    ]
    index = TfidfIndex(chunks)
    results = index.search("What is the refund policy?", top_k=1)
    assert results
    assert "refund" in results[0][0].lower()


def test_document_store_end_to_end():
    store = DocumentStore()
    text = (
        "NEXA is an AI chatbot. It supports document question answering. "
        "It also supports a calculator tool for basic arithmetic."
    )
    n_chunks = store.add_document("session-1", text)
    assert n_chunks >= 1
    assert store.has_document("session-1")

    results = store.retrieve("session-1", "calculator tool")
    assert results
    assert any("calculator" in r.lower() for r in results)


def test_document_store_no_document_returns_empty():
    store = DocumentStore()
    assert store.retrieve("missing-session", "anything") == []
