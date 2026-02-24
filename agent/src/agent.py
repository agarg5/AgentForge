from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .prompts.system import SYSTEM_PROMPT
from .tools.accounts import account_summary
from .tools.benchmark import benchmark_comparison
from .tools.create_order import create_order
from .tools.delete_order import delete_order
from .tools.dividends import dividend_analysis
from .tools.market_data import market_data
from .tools.portfolio import portfolio_analysis
from .tools.risk_assessment import risk_assessment
from .tools.transactions import transaction_history


def create_agent():
    """Create a LangChain agent with Ghostfolio tools."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    tools = [
        portfolio_analysis,
        transaction_history,
        market_data,
        risk_assessment,
        benchmark_comparison,
        dividend_analysis,
        account_summary,
        create_order,
        delete_order,
    ]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    return agent
