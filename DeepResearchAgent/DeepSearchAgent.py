# ---------------- BASIC CONFIGURATIONS ----------------
import os
import asyncio
import json
from dotenv import load_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, function_tool, SQLiteSession
import aiohttp

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
async def tavily_search(query: str) -> str:
    from tavily import TavilyClient
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
                response = await asyncio.wait_for(
                    tavily_client.search(query, max_results=5),
                    timeout=10.0
                )
                return json.dumps(response)
            except Exception as e:
                if attempt == 2:
                    # Fallback mocked data for testing
                    mocked_data = {
                        "results": [
                            {"url": "https://www.consumerreports.org", "content": "Hybrids save on fuel but EVs save more long-term with $790/year fuel savings and 50% lower maintenance costs."},
                            {"url": "https://www.edmunds.com", "content": "EVs offer instant acceleration, 250+ mile range; gas cars refuel faster, better for long trips."},
                            {"url": "https://ev-lectron.com", "content": "EVs cost $59,205 vs. gas cars at $48,699. Battery production has emissions, but EVs are cleaner with renewable grids."},
                            {"url": "https://climate.mit.edu", "content": "EVs have 40-60% lower lifecycle emissions, equivalent to 88 mpg."},
                            {"url": "https://www.epa.gov", "content": "Over 61,000 EV charging stations in 2025 vs. widespread gas stations."}
                        ]
                    }
                    return json.dumps(mocked_data)
                await asyncio.sleep(1)
        return "Search failed: Network unreachable"

# ---------------- AGENTS ----------------
DataGatherAgent = Agent(
    name="DataGather Agent",
    instructions=(
        "You are an expert DataGather Agent. "
        "1) Use the tavily_search tool to execute exactly 3 web searches based on the query provided; "
        "2) Refine queries (e.g., add '2025', regions, or metrics) within these 3 searches; "
        "3) Stop after 3 searches and return all collected data; "
        "4) Return raw search results silently as a JSON string."
    ),
    model=LLM,
    tools=[tavily_search],
    handoff_description="Collects web data using Tavily, limited to 3 searches."
)

SourceCheckerAgent = Agent(
    name="SourceChecker Agent",
    instructions=(
        "You are an expert SourceChecker Agent. "
        "1) Receive raw data as a JSON string; "
        "2) If data is empty or invalid, return 'No sources available'; "
        "3) Parse and rate sources as High (.edu, .gov, major news), Medium (Wikipedia, industry sites), or Low (blogs, forums); "
        "4) Return a JSON string: [{ 'source': <URL>, 'rating': <High/Medium/Low> }]."
    ),
    model=LLM,
    handoff_description="Rates source quality."
)

CitationAgent = Agent(
    name="Citation Agent",
    instructions=(
        "You are an expert Citation Agent. "
        "1) Receive raw data and source ratings as JSON strings; "
        "2) If data or ratings are empty, return 'No citations available'; "
        "3) Parse and format citations in APA style for High and Medium sources only; "
        "4) Return formatted citations as a JSON string: [<APA citation>]."
    ),
    model=LLM,
    handoff_description="Formats APA citations for High/Medium sources."
)

ReflectionAgent = Agent(
    name="Reflection Agent",
    instructions=(
        "You are an expert Reflection Agent. "
        "1) Receive raw data and source ratings as JSON strings; "
        "2) If data is empty, return { 'biases': [], 'gaps': ['No data available'], 'insights': [], 'conflicts': [] }; "
        "3) Parse and identify biases (e.g., media exaggeration), gaps (e.g., missing metrics), insights (e.g., trends), and conflicts (e.g., 'Source A claims EVs save $1000/year, Source B claims $500/year'); "
        "4) Suggest up to 3 additional queries if gaps found; "
        "5) Return analysis as a JSON string: { 'biases': [], 'gaps': [], 'insights': [], 'conflicts': [] }."
    ),
    model=LLM,
    handoff_description="Analyzes data for biases, gaps, insights, and conflicts."
)

PlanningAgent = Agent(
    name="Planning Agent",
    instructions=(
        "You are a Planning Agent. "
        "1) Analyze the query to identify core topic, sub-questions, and ambiguities; "
        "2) Create a research plan and return it as a JSON string: { 'objectives': [], 'sub_questions': [], 'queries': [] (up to 3), 'sources': [] }."
    ),
    model=LLM,
    handoff_description="Creates JSON research plan."
)

# Wrap agents as tools
data_gather_tool = DataGatherAgent.as_tool(
    tool_name="data_gather",
    tool_description="Collect web data using Tavily search, limited to 3 searches."
)

source_check_tool = SourceCheckerAgent.as_tool(
    tool_name="source_check",
    tool_description="Rate sources as High, Medium, or Low."
)

citation_tool = CitationAgent.as_tool(
    tool_name="format_citations",
    tool_description="Format citations in APA style for High/Medium sources."
)

reflection_tool = ReflectionAgent.as_tool(
    tool_name="reflect_data",
    tool_description="Analyze data for biases, gaps, insights, and conflicts."
)

planning_tool = PlanningAgent.as_tool(
    tool_name="create_plan",
    tool_description="Create a JSON research plan with up to 3 queries."
)

OrchestratorAgent = Agent(
    name="Orchestrator Agent",
    instructions=(
        "You are an Orchestrator Agent handling queries for Wajid, who is interested in cars. "
        "1) Call create_plan tool to get the research plan as a JSON string; "
        "2) Parse the plan and call data_gather tool with up to 3 queries; "
        "3) If data_gather returns an error or 'Search failed', return 'Unable to gather data due to network issues. Please try again.'; "
        "4) Call source_check tool to rate sources; "
        "5) Call reflect_data tool to analyze biases, gaps, insights, and conflicts; "
        "6) Call format_citations tool for APA citations (High/Medium sources); "
        "7) If gaps, perform 1 additional cycle with up to 3 new queries; "
        "8) Parse all outputs and synthesize into a conversational response with sections (e.g., Environmental, Cost, Performance), including APA citations, conflicts (e.g., 'Source A says X, Source B says Y'), trends (e.g., 'EVs are increasingly cost-competitive'), and examples relevant to Wajid’s interest in cars; "
        "9) Produce no intermediate outputs; deliver only the final response."
    ),
    model=LLM,
    tools=[planning_tool, data_gather_tool, source_check_tool, reflection_tool, citation_tool],
    handoff_description="Handles queries using planning, data gathering, source checking, reflection, and citation tools."
)

QueryAgent = Agent(
    name="Query Agent",
    instructions=(
        "You are a Query Agent, primary contact for Wajid, who is interested in cars. "
        "1) For greetings (e.g., 'hi'), respond: 'Hi Wajid! How can I help with your interest in cars today?'; "
        "2) For factual or analytical queries (e.g., 'compare electric vs gas cars'), hand off to OrchestratorAgent without responding; "
        "3) If unclear, ask one clarifying question (e.g., 'Could you specify which aspects to compare?'); "
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
        try:
            result = await asyncio.wait_for(
                runner.run(
                    starting_agent=QueryAgent,
                    input=user_input,
                    session=session
                ),
                timeout=30.0
            )
            print(f"Agent: {result.final_output}")
        except asyncio.TimeoutError:
            print("Agent: Request timed out. Please check your network and try again.")
        except Exception as e:
            print(f"Agent: Error occurred: {str(e)}. Please try again or check API keys.")

if __name__ == "__main__":
    asyncio.run(chat_loop())