from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, set_tracing_disabled, function_tool
import os
from dotenv import load_dotenv, find_dotenv
import asyncio

_: bool= load_dotenv(find_dotenv())
API_KEY= os.environ.get("GEMINI_API_KEY")
set_tracing_disabled(disabled=True)

#PROVIDER
external_client: AsyncOpenAI= AsyncOpenAI(
    api_key= API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
) 


# MODEL
Model: OpenAIChatCompletionsModel= OpenAIChatCompletionsModel(
    model='gemini-2.5-flash',
    openai_client=external_client
)

#TOOLS
@function_tool
def sum(a: int, b: int)-> int:
    print("/nTOOL CALLING/n")
    return a+b


#RUNNER
async def functi():

    # AGENT
    Math_Agent: Agent= Agent(
        name="Math Tutor",
        instructions="you are helpful math professor",
        tools=[sum],
        model=Model
    )
    result: Runner= await Runner.run(starting_agent=Math_Agent,
                                    input="4 plust 6?")
   
    print(result.final_output)


asyncio.run(functi())