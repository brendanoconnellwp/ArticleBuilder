import os
from anthropic import Anthropic
from openai import OpenAI
from models import APIKey
from app import db

def get_api_key(service):
    api_key = APIKey.query.filter_by(service=service).first()
    if not api_key:
        raise ValueError(f"No API key found for {service}")
    return api_key.key

def generate_article(title):
    # Try OpenAI first, fall back to Anthropic
    try:
        return generate_with_openai(title)
    except Exception as e:
        try:
            return generate_with_anthropic(title)
        except Exception as ae:
            raise Exception(f"Both API calls failed. OpenAI: {str(e)}, Anthropic: {str(ae)}")

def generate_with_openai(title):
    # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    api_key = get_api_key('openai')
    client = OpenAI(api_key=api_key)
    
    prompt = f"""Write a comprehensive article about the following topic:
    {title}
    
    The article should be well-structured, informative, and engaging.
    Include an introduction, main body with key points, and a conclusion."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a professional article writer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    return response.choices[0].message.content

def generate_with_anthropic(title):
    # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
    api_key = get_api_key('anthropic')
    client = Anthropic(api_key=api_key)
    
    prompt = f"""Write a comprehensive article about the following topic:
    {title}
    
    The article should be well-structured, informative, and engaging.
    Include an introduction, main body with key points, and a conclusion."""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.content[0].text
