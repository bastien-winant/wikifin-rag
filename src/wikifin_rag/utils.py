def vec_to_str(vector):
    return f"[{",".join(str(x) for x in vector)}]"


def text_to_chunks(text, chunk_size, overlap):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")

    length = len(text)
    step = chunk_size - overlap

    chunks = {}

    for i in range(0, length - overlap, step):
        chunk = text[i:i + chunk_size]
        chunks[i] = chunk

    return chunks