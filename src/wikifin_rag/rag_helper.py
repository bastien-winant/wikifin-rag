import time
from wikifin_rag.items import LLMCallRecord
from wikifin_rag.evaluation_utils import calculate_cost

INSTRUCTIONS = '''
Your task is to answer questions about finance personal management
based on the provided context.

Use the context to find relevant information and provide accurate
answers. If the answer is not found in the context,
respond with "I don't know."

You never give investment advice or offer opinions. If you are asked for advice,
respond with "I am not in a position to answer this question. Please talk to a financial advisor.".
'''

PROMPT_TEMPLATE = '''
QUESTION: {question}

CONTEXT:
{context}
'''.strip()


class RAGBase:

    def __init__(
        self,
        search_function,
        llm_client,
        instructions=INSTRUCTIONS,
        prompt_template=PROMPT_TEMPLATE,
        model='gpt-5.4-mini'
    ):
        self.search_function = search_function
        self.llm_client = llm_client
        self.instructions = instructions
        self.prompt_template = prompt_template
        self.model = model

        self.last_call: LLMCallRecord = None

    def _log_response(self, prompt, response, response_time):
        usage = response.usage
        cost = calculate_cost(usage)

        call_record = LLMCallRecord(
            model=self.model,
            prompt=prompt,
            instructions=self.instructions,
            answer=response.output_text,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            response_time=response_time,
            total_cost=cost["total_cost"],
            input_cost=cost["input_cost"],
            output_cost=cost["output_cost"]
        )
    
        self.last_call = call_record

    def build_context(self, search_results):
        lines = []

        for chunk in search_results:
            lines.append(f"DOCUMENT: {chunk['title']}")
            lines.append(f"SECTION: {chunk['section']}")
            lines.append(f"CONTENT: {chunk['content']}")
            lines.append(f"SOURCES: {chunk['source_url']}")
            lines.append('')

        return '\n'.join(lines).strip()

    def build_prompt(self, query, search_results):
        context = self.build_context(search_results)
        return self.prompt_template.format(
            question=query, context=context
        )

    def llm(self, prompt):
        start_time = time.time()
        
        response = self.llm_client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=prompt,
            temperature=0.0
        )

        response_time = time.time() - start_time
        self._log_response(prompt, response, response_time)

        return response.output_text

    def rag(self, query):
        search_results = self.search_function(query)
        prompt = self.build_prompt(query, search_results)
        answer = self.llm(prompt)
        return answer
