from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, function_tool, SQLiteSession
from dotenv import load_dotenv, find_dotenv
from tavily import TavilyClient
import os
import asyncio

#---------------- BASIC CONFIGURATIONS ----------------
_: bool= load_dotenv(find_dotenv())
# set_tracing_disabled(disabled=True)
os.environ['OPENAI_API_KEY']= os.getenv("OPENAI_API_KEY")
GEMINI = os.getenv("GEMINI_API_KEY")
TAVILY = os.getenv("TAVILY_API_KEY")
URL_ = os.getenv("BASE_URL")

if not GEMINI or not TAVILY:
    raise ValueError("API KEY MISSING")

provider: AsyncOpenAI = AsyncOpenAI(api_key=GEMINI, base_url=URL_)
LLM: OpenAIChatCompletionsModel= OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=provider)

# ----------------------------------------------------------------------------------------------------------------------------

# -------------------------- TOOLS ---------------------------
@function_tool
def Search(query: str) -> str:
    print("TOOL CALLING....")
    tavily_client = TavilyClient(api_key=TAVILY)
    response = tavily_client.search(query, max_results=5)
    return str(response)




# ---------------- AGENTS ----------------
DataGatherAgent: Agent = Agent(
    name="DataGather Agent",
    instructions="You are an expert DataGather Agent tasked with collecting data for the Orchestrator Agent. Use the tavily_search tool to execute web searches based on the query from the Orchestrator Agent. 1) Perform searches, refining queries (e.g., add keywords, dates, regions) if results lack depth or relevance; 2) Continue until sufficient, high-quality data is collected from reputable sources (e.g., news, government, academic); 3) Return raw search results without any user-facing output or commentary; 4) Do not respond to the user; silently hand off results to the Orchestrator Agent.",
    model=LLM,
    tools=[Search],
    handoff_description="Expert DataGather Agent that collects comprehensive web data using Tavily, refining queries for the Orchestrator Agent."
)

CitationAgent: Agent = Agent(
    name="Citation Agent",
    instructions="You are an expert Citation Agent tasked with formatting citations for the Orchestrator Agent. 1) Receive raw data from the Orchestrator Agent; 2) Extract source metadata (e.g., URL, publication, date); 3) Format citations in APA style, ensuring accuracy and ethical standards (e.g., no unverified sources); 4) Return formatted citations without user-facing output; 5) Do not respond to the user; silently hand off citations to the Orchestrator Agent.",
    model=LLM,
    handoff_description="Expert Citation Agent that formats and validates citations in APA style for the Orchestrator Agent."
)

ReflectionAgent: Agent = Agent(
    name="Reflection Agent",
    instructions="You are an expert Reflection Agent tasked with analyzing data for the Orchestrator Agent. 1) Receive raw data from the Orchestrator Agent; 2) Identify biases (e.g., media sensationalism), gaps (e.g., missing data), and insights (e.g., environmental impacts); 3) Suggest additional queries if gaps are found; 4) Return analysis and recommendations without user-facing output; 5) Do not respond to the user; silently hand off results to the Orchestrator Agent.",
    model=LLM,
    handoff_description="Expert Reflection Agent that analyzes data for biases, gaps, and insights for the Orchestrator Agent."
)

# ---------------- AGENTS AS TOOLS ----------------------------

data_gather_tool = DataGatherAgent.as_tool(
    tool_name="data_gather",
    tool_description="Collect comprehensive web data using Tavily search for a given query."
)

citation_tool = CitationAgent.as_tool(
    tool_name="format_citations",
    tool_description="Format citations in APA style from raw data."
)

reflection_tool = ReflectionAgent.as_tool(
    tool_name="reflect_data",
    tool_description="Analyze data for biases, gaps, and insights, suggesting additional queries if needed."
)

OrchestratorAgent: Agent = Agent(
    name="Orchestrator Agent",
    instructions="You are an expert Orchestrator Agent tasked with executing the research plan from the Planning Agent. 1) Delegate data collection to DataGather Agent with specific queries; 2) Delegate analysis to Reflection Agent for biases, gaps, and insights; 3) Delegate citation formatting to Citation Agent; 4) Repeat agent calls if gaps are identified; 5) Synthesize outputs into a concise, conversational response addressing the user’s query (e.g., benefits of electric cars), including APA citations, without mentioning internal processes, plans, or agent interactions; 6) Do not produce intermediate outputs; deliver only the final response; 7) Ensure ethical standards (e.g., avoid sensationalism, respect privacy).",
    model=LLM,
    handoffs=[DataGatherAgent, CitationAgent, ReflectionAgent],
    tools=[data_gather_tool, citation_tool, reflection_tool],
    handoff_description="Expert Orchestrator Agent that coordinates DataGather, Citation, and Reflection Agents to deliver seamless, accurate user responses."
)

PlanningAgent: Agent = Agent(
    name="Planning Agent",
    instructions="You are an expert Planning Agent tasked with creating actionable research plans for complex queries received via handoff from the Query Agent. Analyze the query thoroughly: identify the core topic, sub-questions, ambiguities, and implications through step-by-step reasoning. Create a structured research plan including: 1) Key objectives and sub-topics; 2) Recommended sources and tools (e.g., web searches via Tavily, X posts, official reports); 3) Steps for data gathering and cross-verification across multiple perspectives; 4) Methods for synthesis, reasoning, and identifying biases or gaps; 5) Guidelines for citation accuracy and ethical considerations (e.g., privacy, avoiding sensationalism). Do not generate any output or response for the user. Instead, produce the plan as an internal artifact and immediately handoff it to the [OrchestratorAgent] via the handoff mechanism, maintaining a seamless experience without exposing internal processes. REMEMBER your job is to create Plan and Handoff to the OrchestratorAgent",
    model=LLM,
    handoff_description="Expert Planning Agent that analyzes queries, performs initial reasoning, and crafts detailed, multi-step research plans for autonomous deep investigation, ensuring comprehensive coverage and accurate synthesis.",
    handoffs=[OrchestratorAgent]
)

QueryAgent: Agent= Agent(name="Query Agent", instructions="You are a friendly and professional Query Agent, the primary point of contact for users. Your role is to engage users with warm, natural greetings for casual inputs like 'hello' or 'hi', making them feel welcomed and supported. For inputs that imply a question or topic requiring deep research (e.g., queries about complex topics, requests for analysis, or factual investigations), identify the need for research and seamlessly hand off to the Planning Agent to create a research plan, without indicating the handoff to the user. Maintain a consistent, conversational tone throughout, ensuring the user feels they are interacting with a single, knowledgeable assistant. If the input is unclear, ask clarifying questions to determine if research is needed. Always prioritize a smooth and engaging user experience.", model=LLM, handoffs=[PlanningAgent])



# -------------------------- RUNNER LOOP --------------------------

async def chat_loop():
    session = SQLiteSession(session_id="user_123", db_path="conversations.db")  # Persistent session storage
    runner = Runner()

    print("Start chatting (type 'exit' to quit):")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            session.clear_session()
            break
        
        result = await runner.run(
            starting_agent=QueryAgent,
            input=user_input,
            session=session,  # Maintains conversation history
            
        )
        print(f"Agent: {result.final_output}")




# ----------------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(chat_loop())
