INSTRUCTIONS = '''
ROLE & PURPOSE:
You are "FinWiki AI," a precise, objective financial knowledge retrieval assistant. Your sole purpose is to answer user queries using ONLY the verified context provided below. You must help users understand personal finance concepts, savings strategies, and investment definitions found strictly within your knowledge base.

CRITICAL CONSTRAINTS (STRICT COMPLIANCE REQUIRED):
1. STRICT GROUNDING: Base your answers ONLY on the provided context. If the context does not contain the answer to a question, you must state exactly: "I am sorry, but the provided financial wiki does not contain information to answer that question." Do not use external or pre-trained knowledge to fill in gaps.
2. NO SPECULATION OR INFERENCE: Do not infer, extrapolate, or assume financial trends, returns, or advice not explicitly written in the context.
3. FINANCIAL ADVICE BAN: You are an educational tool, not a financial advisor. Never use phrases like "I recommend," "You should invest in," "This is a good/bad asset," or "This return is guaranteed." Keep your tone strictly neutral and informational.
4. SOURCE CITATION: When providing an answer, cite the specific section or article name from the context where you found the information.

OUTPUT FORMATTING:
- Structure your answers clearly using short sentences and bullet points for high scannability.
- If data or a comparison is present in the context, present it in a clean Markdown table.
'''

PROMPT_TEMPLATE = '''
QUESTION: {question}

CONTEXT:
{context}
'''.strip()


class RAGBase:

    def __init__(
        self,
        embedder,
        conn,
        llm_client,
        instructions=INSTRUCTIONS,
        prompt_template=PROMPT_TEMPLATE,
        model='gpt-5.4-mini'
    ):
        self.embedder = embedder
        self.conn = conn
        self.llm_client = llm_client
        self.instructions = instructions
        self.prompt_template = prompt_template
        self.model = model

    def search(self, query, num_results=5):
        query_vector = self.embedder.encode(query)
        query_str = f"[{",".join(str(x) for x in query_vector)}]"

        rows = self.conn.execute(
            """
            SELECT *
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_str, num_results)
        ).fetchall()

        return [
            {"course": r[0], "section": r[1], "question": r[2], "answer": r[3]}
            for r in rows
        ]

    def build_context(self, search_results):
        lines = []

        for doc in search_results:
            lines.append(doc['section'])
            lines.append('Q: ' + doc['question'])
            lines.append('A: ' + doc['answer'])
            lines.append('')

        return '\n'.join(lines).strip()

    def build_prompt(self, query, search_results):
        context = self.build_context(search_results)
        return self.prompt_template.format(
            question=query, context=context
        )

    def llm(self, prompt):
        input_messages = [
            {'role': 'developer', 'content': self.instructions},
            {'role': 'user', 'content': prompt}
        ]

        response = self.llm_client.responses.create(
            model=self.model,
            input=input_messages
        )

        return response.output_text

    def rag(self, query):
        search_results = self.search(query)
        prompt = self.build_prompt(query, search_results)
        answer = self.llm(prompt)
        return answer
