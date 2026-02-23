from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .prompts.system import SYSTEM_PROMPT
from .tools.portfolio import portfolio_analysis


def create_agent():
    """Create a LangChain agent with Ghostfolio tools."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    tools = [portfolio_analysis]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    return agent
