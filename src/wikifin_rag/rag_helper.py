import time
from wikifin_rag.items import LLMCallRecord
from wikifin_rag.evaluation_utils import calculate_cost, calculate_total_cost

INSTRUCTIONS = '''
Your task is to answer questions about **personal finance management** using only the information provided in the retrieved context.

### Instructions

1. **Use the provided context as your primary and authoritative source.**

   * Base your answers only on information explicitly supported by the retrieved context.
   * Do not invent, assume, or supplement information from your general knowledge when it is not present in the context.
   * If multiple sources are provided, synthesize them accurately and resolve differences only when the context supports doing so.

2. **Always cite your sources.**

   * Include the relevant source or sources in every answer.
   * Make the source attribution clear and easy to identify.
   * Do not cite a source that does not support the information in your answer.

3. **When the answer is not available in the context:**
   * Respond exactly:

   > I was unable to find relevant information to provide an answer to your question.
   * Do not include a source citation.

4. **Do not provide personalized financial, investment, tax, legal, or other regulated financial advice.**

   * You may explain financial concepts, products, terminology, and general principles when supported by the context.
   * Do not recommend specific investments, financial products, transactions, or strategies for an individual.
   * Do not tell the user what they should buy, sell, invest in, borrow, save, or otherwise do with their money.
   * Do not express personal opinions about financial decisions.

5. **When asked for specific financial advice:**
   * Respond exactly:

   > I am not in a position to answer this question. Please talk to a financial advisor.
   * Do not include a source citation.

6. **Be accurate and transparent.**

   * Distinguish clearly between facts stated in the context and any uncertainty.
   * Do not make claims that cannot be supported by the retrieved context.
   * If the context only partially answers the question, provide only the supported information.
   * If the missing information is essential to answering the question, use the fallback response from step 3.

7. **Keep responses clear and concise.**

   * Answer the user's question directly.
   * Avoid unnecessary explanations or speculation.
   * Keep the tone conversational rather than formal.
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

        self.usages = []
        self.last_call: LLMCallRecord = None

    def reset_usage(self):
        self.usages = []
        self.last_call = None

    def _log_response(self, prompt, response, response_time):
        usage = response.usage
        self.usages.append(usage)
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

    def llm(self, prompt, history=None):
        start_time = time.time()

        history = [] if history is None else history
        history.append({
            "role": "user",
            "content": prompt
        })

        response = self.llm_client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=history,
            temperature=0.0,
            max_output_tokens=750
        )

        response_time = time.time() - start_time
        self._log_response(prompt, response, response_time)

        return response.output_text

    def rag(self, query, history=None):
        try:
            search_results = self.search_function(query)
            prompt = self.build_prompt(query, search_results)
            answer = self.llm(prompt=prompt, history=history)
        except Exception as e:
            raise
        return answer

    def total_cost(self):
        return calculate_total_cost(self.usages)
