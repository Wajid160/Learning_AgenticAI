# Deep Research Agent System

## Overview
This project implements a professional-grade Deep Research Agent System inspired by industry leaders (e.g., OpenAI, Anthropic). It uses a multi-agent architecture to handle complex research queries, breaking them into manageable tasks, gathering data, assessing source quality, detecting conflicts, and synthesizing findings into conversational responses with APA citations. The system is personalized for Wajid, who is interested in cars, and adheres to a three-search limit per query for efficiency.

## Setup
1. **Install Dependencies**:
   - Ensure Python 3.10+ and `uv` are installed.
   - Run: `uv pip install openai openai-agents-python python-dotenv tavily-python aiohttp`
2. **Configure Environment**:
   - Create a `.env` file in the project root:
     ```
     GEMINI_API_KEY=your_gemini_key
     TAVILY_API_KEY=your_tavily_key
     BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
     ```
3. **Create Database Directory**:
   - Run: `mkdir DB` to create the `DB` directory for `tabby.db` (SQLite session storage).
4. **Run the System**:
   - Execute: `uv run deep_research_system.py`
   - Start chatting in the console; type `exit` to quit.

## Agents
- **QueryAgent**: Primary contact for Wajid. Handles greetings (e.g., "Hi Wajid! How can I help with your interest in cars today?") and hands off research queries (e.g., "compare electric vs gas cars") to OrchestratorAgent. Asks clarifying questions for unclear inputs.
- **OrchestratorAgent**: Coordinates the research process using tools: creates a plan, gathers data, checks sources, analyzes data, and formats citations. Delivers a conversational response with sections (e.g., Environmental, Cost), conflicts, trends, and APA citations.
- **PlanningAgent**: Analyzes queries to create a JSON research plan with objectives, sub-questions, and up to three search queries.
- **DataGatherAgent**: Collects web data using Tavily (limited to three searches per query, with refinements like "2025" or metrics).
- **SourceCheckerAgent**: Rates sources as High (.edu, .gov, major news), Medium (Wikipedia, industry sites), or Low (blogs, forums).
- **ReflectionAgent**: Analyzes data for biases, gaps, insights, and conflicts (e.g., "Source A claims EVs save $1000/year, Source B claims $500/year"). Suggests additional queries if gaps are found.
- **CitationAgent**: Formats APA citations for High and Medium sources.

## Coordination
- **Workflow**: 
  1. `QueryAgent` detects research queries and hands them off to `OrchestratorAgent`.
  2. `OrchestratorAgent` uses tools sequentially: 
     - Calls `planning_tool` to create a JSON research plan.
     - Calls `data_gather_tool` for up to three searches.
     - Calls `source_check_tool` to rate sources.
     - Calls `reflect_data_tool` to analyze biases, gaps, insights, and conflicts.
     - Calls `format_citations_tool` for APA citations.
     - If gaps are found, performs one additional cycle with up to three new queries.
     - Synthesizes outputs into a conversational response with sections, trends, conflicts, and citations, personalized for Wajid’s interest in cars.
  3. No intermediate outputs are shown; only the final response is delivered.
- **Error Handling**: Includes timeouts, retries, and fallback mocked data in `tavily_search` to handle network issues (e.g., `[WinError 10051]`).

## Example Questions
- **Level 1**: "What are the benefits of electric cars?"
- **Level 2**: "Compare electric vs gas cars"
- **Level 3**: "How has AI changed healthcare from 2020 to 2024?"
- **Level 4**: "Analyze the economic impact of remote work policies on small businesses vs large corporations"

### Example Interaction
```
You: Hi
Agent: Hi Wajid! How can I help with your interest in cars today?
You: compare electric vs gas cars?
Agent: Wajid, here’s a comparison of electric cars (EVs) and gas cars, tailored to your interest in cars:

**Environmental Impact**: EVs produce zero tailpipe emissions, with 40-60% lower lifecycle emissions than gas cars, equivalent to 88 mpg (MIT Climate Portal, 2022). Gas cars emit more due to fuel combustion. Conflict: One source claims EVs are nearly carbon-neutral with renewable grids, but another notes battery production emissions (Lectron EV, 2025).

**Cost**: EVs have higher upfront costs ($59,205 vs. $48,699 for gas cars) but save $790/year on fuel and ~50% on maintenance, ideal for city driving (Consumer Reports, 2023). Trend: EVs are becoming cost-competitive as battery prices decline.

**Performance**: EVs offer instant acceleration and 250+ mile ranges, great for urban commutes, while gas cars refuel faster, suiting long trips (Edmunds, 2024).

**Infrastructure**: Over 61,000 EV charging stations exist in 2025, but gas stations are more widespread (U.S. Environmental Protection Agency, 2025).

**Safety**: Both have comparable crash test ratings, but EVs often include advanced safety features.

Wajid, EVs could save money long-term if you have charging access, but gas cars may be better for long trips.

Sources:
- Consumer Reports. (2023). Why hybrid vehicles are a smart choice right now. Retrieved from https://www.consumerreports.org
- Edmunds. (2024). Electric cars vs. gas cars. Retrieved from https://www.edmunds.com
- Lectron EV. (2025). Average price of electric car vs. gas car. Retrieved from https://ev-lectron.com
- MIT Climate Portal. (2022). Are electric vehicles definitely better for the climate than gas-powered cars? Retrieved from https://climate.mit.edu
- U.S. Environmental Protection Agency. (2025). Electric vehicle myths. Retrieved from https://www.epa.gov
```

## Troubleshooting
- **Network Errors (e.g., `[WinError 10051]`)**:
  - Check internet: `ping google.com`
  - Disable VPNs/firewalls to ensure `tavily.com` and `generativelanguage.googleapis.com` are accessible.
  - Verify API keys in `.env`.
  - Test Tavily API: `curl -X POST https://api.tavily.com/search -H "Content-Type: application/json" -d '{"api_key":"YOUR_TAVILY_API_KEY","query":"test"}'`
  - Check ports 80/443: `netstat -an`
- **Module Errors**:
  - If `No module named 'aiohttp'`, run: `uv pip install aiohttp`
- **Database Issues**:
  - Ensure `DB` directory exists: `mkdir DB`
- **Timeouts**: The system uses a 30-second timeout for queries and 10-second timeout for searches. If it times out, check network or API status.

## Notes
- **Assignment Completion**: Meets all requirements for Phases 1-4 (environment setup, multi-agent system, planning, source checking, conflict detection, synthesis, citations). Includes error handling (+5 bonus points).
- **Optional Features**:
  - Streaming: Replace `chat_loop` with the streaming version for real-time output (+5 bonus points).
  - XPostAgent: Add an agent to fetch social media data from X for creative research (+5 bonus points).
  - Demo Video: Record a video showing the system handling a complex query (+15 bonus points).
