INSTRUCTIONS = '''
Your task is to answer questions about personal finance
based on the provided context using simple, everyday words.

Use the context to find relevant information and provide accurate
answers. If the answer is not found in the context,
respond with "I don't know."

You never give financial advice or recommendations. Your responses should be
informative and based on the context provided. If the user asks for advice or recommendations,
respond with "I am not able to provide financial advice or recommendations. Please consult a qualified financial advisor for personalized guidance."
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
        query_str = "[" + ",".join(str(x) for x in query_vector) + "]"
        rows = self.conn.execute(
            """
            SELECT
                id,
                language,
                topic,
                content,
                1 - (embedding <=> %s::vector) AS similarity
            FROM documents
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_str, query_str, num_results)
        ).fetchall()

        return [{
            'id': row[0],
            'language': row[1],
            'topic': row[2],
            'content': row[3],
            'similarity': row[4]
            } for row in rows]

    def build_context(self, search_results):
        lines = []

        for doc in search_results:
            lines.append('Topic: ' + doc['topic'])
            lines.append('Language: ' + doc['language'])
            lines.append('Content: ' + doc['content'])
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

    def rag(self, query, num_results=5):
        search_results = self.search(query, num_results=num_results)
        prompt = self.build_prompt(query, search_results)
        answer = self.llm(prompt)
        return answer