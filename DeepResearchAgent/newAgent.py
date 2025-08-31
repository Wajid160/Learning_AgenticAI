# ---------------- BASIC CONFIGURATIONS ----------------
import os
import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, function_tool, SQLiteSession, ModelSettings
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

if not GEMINI_API_KEY or not TAVILY_API_KEY:
    raise ValueError("API KEY MISSING")

provider = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=BASE_URL)
LLM = OpenAIChatCompletionsModel(model="gemini-2.5-pro", openai_client=provider)

# ---------------- TOOLS ----------------
@function_tool
def tavily_search(query: str) -> str:
    from tavily import TavilyClient
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    response = tavily_client.search(query, max_results=5)
    return str(response)

# ---------------- AGENTS ----------------
DataGatherAgent = Agent(
    name="DataGather Agent",
    instructions="You are an expert DataGather Agent. Use the tavily_search tool to execute up to 3 web searches based on the query provided. Refine queries if needed, stop after 3, and return raw results silently.",
    model=LLM,
    tools=[tavily_search],
    handoff_description="Collects web data using Tavily for the Orchestrator Agent."
)

CitationAgent = Agent(
    name="Citation Agent",
    instructions="You are an expert Citation Agent. Format citations in APA style from raw data, ensuring accuracy. Return formatted citations silently.",
    model=LLM,
    handoff_description="Formats citations in APA style for the Orchestrator Agent."
)

ReflectionAgent = Agent(
    name="Reflection Agent",
    instructions="You are an expert Reflection Agent. Analyze data for biases, gaps, and insights. Suggest up to 3 additional queries if gaps found. Return analysis silently.",
    model=LLM,
    handoff_description="Analyzes data for biases, gaps, and insights for the Orchestrator Agent."
)

PlanningAgent = Agent(
    name="Planning Agent",
    instructions="You are a Planning Agent. Create a JSON research plan with: { 'objectives': [], 'sub_questions': [], 'queries': [] (up to 3), 'sources': [] }. Return the JSON silently.",
    model=LLM,
    handoff_description="Creates JSON research plan for the Orchestrator Agent."
)

# Wrap agents as tools
data_gather_tool = DataGatherAgent.as_tool(
    tool_name="data_gather",
    tool_description="Collect web data using Tavily search, limited to 3 searches per query."
)

citation_tool = CitationAgent.as_tool(
    tool_name="format_citations",
    tool_description="Format citations in APA style from raw data."
)

reflection_tool = ReflectionAgent.as_tool(
    tool_name="reflect_data",
    tool_description="Analyze data for biases, gaps, and insights."
)

planning_tool = PlanningAgent.as_tool(
    tool_name="create_plan",
    tool_description="Create a JSON research plan for the query."
)


OrchestratorAgent = Agent(
    name="Orchestrator Agent",
    instructions=(
        "You are an Orchestrator Agent tasked with handling the user query. "
        "1) Call create_plan tool to get the research plan JSON; "
        "2) Call data_gather tool with up to 3 queries from the plan; "
        "3) Call reflect_data tool to analyze biases, gaps, and insights; "
        "4) Call format_citations tool to format APA citations; "
        "5) If gaps, perform 1 additional cycle with up to 3 new queries; "
        "6) Synthesize outputs into a concise, conversational response with APA citations; "
        "7) Produce no intermediate outputs; deliver only the final response."
    ),
    model=LLM,
    model_settings=ModelSettings(tool_choice="required"),
    tools=[planning_tool, data_gather_tool, reflection_tool, citation_tool],
    handoff_description="Handles queries by using planning, data gathering, reflection, and citation tools to deliver a final response."
)

QueryAgent = Agent(
    name="Query Agent",
    instructions=(
        "You are a Query Agent, the user’s primary contact. "
        "1) For greetings or small talk, respond briefly; "
        "2) For factual or analytical queries, immediately hand off to OrchestratorAgent without responding; "
        "3) If unclear, ask one clarifying question; "
        "4) Do not answer research queries directly."
    ),
    model=LLM,
    handoffs=[OrchestratorAgent],
    handoff_description="Detects research queries and hands off to OrchestratorAgent."
)

# ---------------- RUNNER LOOP ----------------
async def chat_loop():
    session = SQLiteSession(session_id="user_123", db_path="DB/tabby.db")
    runner = Runner()
    print("Start chatting (type 'exit' to quit):")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            await session.clear_session()
            break
        result = await runner.run(
            starting_agent=QueryAgent,
            input=user_input,
            session=session
        )
        print(f"Agent: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(chat_loop())
