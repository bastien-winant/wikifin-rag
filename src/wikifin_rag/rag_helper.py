INSTRUCTIONS = '''
Your task is to answer questions about personal finance management
based on the provided context.

Use the context to find relevant information and provide accurate
answers. If the answer is not found in the context,
respond with "I was unable to find enough relevant information to provide an answer."

When using information from the context in your answer, always include all the related source URLs as reference.
'''

PROMPT_TEMPLATE = '''
QUESTION: {question}

CONTEXT:
{context}
'''.strip()

from wikifin_rag.db_client import PostgresClient
from wikifin_rag.evaluation_utils import calc_total_price


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

        self.usages = []
        self.last_usage = None


    def reset_usage(self):
        self.usages = []
        self.last_usage = None


    def rrf(self, search_results, k=1, num_results=10):
        scores = {}
        doc_map = {}

        for results in search_results:
            for rank, doc in enumerate(results):
                key = doc["id"]
                if key not in scores:
                    scores[key] = 0
                    doc_map[key] = doc
                scores[key] += 1 / (k + rank + 1)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_map[key] for key, _ in ranked[:num_results]]


    def search(self, query, weights=None, normalization=0, num_results=5):
        self.db_client.open_connection()
        text_search_results = self.db_client.text_search(query=query, weights=weights, normalization=normalization, num_results=num_results)
        vector_search_results = self.db_client.vector_search(query=query, num_results=num_results)
        self.db_client.close_connection()
        return self.rrf([text_search_results, vector_search_results], num_results=num_results)


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
        response = self.llm_client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=prompt,
            temperature=0.0
        )

        self.last_usage = response.usage
        self.usages.append(response.usage)

        return response.output_text


    def rag(self, query):
        search_results = self.search(query)
        prompt = self.build_prompt(query, search_results)
        answer = self.llm(prompt)
        return answer
    

    def total_cost(self):
        return calc_total_price(self.usages)