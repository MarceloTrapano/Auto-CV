from langchain_core.prompts import ChatPromptTemplate


class LLMAgent:
    def __init__(self,
                 llm,
                 system_prompt_path: str,
                 human_prompt_path: str
                 ):

        self.llm = llm

        with open(system_prompt_path, "r", encoding="utf-8") as file:
            system_prompt = file.read()
        with open(human_prompt_path, "r", encoding="utf-8") as file:
            human_prompt = file.read()

        self.prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_prompt)])

    def set_prompt(self,  system_prompt, human_prompt):
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_prompt)])

    def invoke(self, **kwargs):
        chain = self.prompt | self.llm
        return chain.invoke(kwargs)

    def invoke_with_schema(self, schema, **kwargs):
        chain = self.prompt | self.llm.with_structured_output(schema)
        return chain.invoke(kwargs)
