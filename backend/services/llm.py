import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def generate_answer(prompt: str) -> str:
    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text


def generate_routing_answer(prompt: str) -> str:
    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
        reasoning={"effort": "low"},
        max_output_tokens=200
    )
   
    return response.output_text
    
