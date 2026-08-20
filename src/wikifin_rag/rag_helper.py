INSTRUCTIONS = '''
Your task is to answer questions about personal finance management
based on the provided context.

Use the context to find relevant information and provide accurate
answers. If the answer is not found in the context,
respond with "I don't know."

If you do provide an answer, always include the source URLs as a reference.
'''

PROMPT_TEMPLATE = '''
QUESTION: {question}

CONTEXT:
{context}
'''.strip()

from wikifin_rag.db_client import PostgresClient


class RAGBase:

    def __init__(
        self,
        embedder,
        llm_client,
        instructions=INSTRUCTIONS,
        prompt_template=PROMPT_TEMPLATE,
        model='gpt-5.4-mini'
    ):
        self.db_client = PostgresClient(embedder=embedder)
        self.llm_client = llm_client
        self.instructions = instructions
        self.prompt_template = prompt_template
        self.model = model


    def search(self, query, num_results=5):
        self.db_client.open_connection()
        results = self.db_client.vector_search(query, num_results)
        self.db_client.close_connection()
        return results


    def build_context(self, search_results):
        lines = []

        for chunk in search_results:
            lines.append(f"DOCUMENT: {chunk['title']}")
            lines.append(f"SECTION: {chunk['section']}")
            lines.append(f"CONTENT: {chunk['content']}")
            lines.append(f"SOURCE: {chunk['source_url']}")
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