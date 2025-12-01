from typing import List, Dict
import json
import hashlib
from openai import OpenAI
from ...config import get_settings

def extract_pros_cons(argument: str, articles: List[Dict], argument_id: str = "") -> Dict[str, List[Dict]]:
    """
    Extract supporting and contradicting arguments from a list of scientific articles.

    Analyzes articles to identify:
    - Points that support the argument (pros)
    - Points that contradict or question it (cons)
    - For each point, associates the source (article URL)

    Args:
        argument: Text of the argument to analyze
        articles: List of articles with fields "title", "url", "snippet"
        argument_id: Unique identifier for the argument (optional)

    Returns:
        Dictionary with:
        - "pros": list of {"claim": str, "source": str}
        - "cons": list of {"claim": str, "source": str}
    """
    settings = get_settings()

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured in environment variables")

    print(f"[DEBUG extract_pros_cons] Argument: {argument[:50]}...")
    print(f"[DEBUG extract_pros_cons] Number of articles received: {len(articles)}")

    if not argument or not articles:
        print(f"[DEBUG extract_pros_cons] Empty return: argument={bool(argument)}, articles={len(articles) if articles else 0}")
        return {"pros": [], "cons": []}

    # Generate a unique ID for the argument if not provided
    if not argument_id:
        argument_id = hashlib.md5(argument.encode()).hexdigest()[:8]

    # Format articles context
    articles_context = ""
    current_length = 0
    max_length = 6000
    
    for article in articles:
        article_text = f"Article: {article.get('title', '')}\nURL: {article.get('url', '')}\nSummary: {article.get('snippet', '')}\n\n"

        if current_length + len(article_text) > max_length:
            break

        articles_context += article_text
        current_length += len(article_text)

    if len(articles) > 0 and not articles_context:
         # Fallback if the first article is too long (unlikely with snippet)
         articles_context = f"Article: {articles[0].get('title', '')}\nURL: {articles[0].get('url', '')}\nSummary: {articles[0].get('snippet', '')[:max_length]}\n\n"

    client = OpenAI(api_key=settings.openai_api_key)

    # Optimized prompt (shorter thanks to MCP summaries)
    system_prompt = """You are an expert in scientific analysis and argument critique.
Analyze scientific articles to identify points that support (pros) or contradict (cons) an argument.

**STRICT VERIFICATION RULES:**
1.  **Explicit Evidence Required**: Each point ("claim") MUST be explicitly supported by the text of a provided article.
2.  **No Invention**: If no article mentions a point, DO NOT INVENT IT.
3.  **Citation Required**: Each claim must be associated with the exact URL of the article containing it.
4.  **Relevance**: Only retain points directly related to the analyzed argument.

For each article, identify:
- Claims that SUPPORT the argument (pros)
- Claims that CONTRADICT or QUESTION the argument (cons)

Respond in JSON with this exact format:
{
    "pros": [{"claim": "point description (with implicit citation)", "source": "article URL"}],
    "cons": [{"claim": "point description (with implicit citation)", "source": "article URL"}]
}

If no article contains relevant information, return empty lists."""


    user_prompt = f"""Argument to analyze: {argument}

Scientific articles:
{articles_context}

Analyze these articles and extract supporting (pros) and contradicting (cons) points for this argument."""


    try:
        response = client.chat.completions.create(
            model=settings.openai_smart_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # Parse JSON response
        content = response.choices[0].message.content
        result = json.loads(content)

        return {
            "pros": result.get("pros", []),
            "cons": result.get("cons", [])
        }

    except json.JSONDecodeError as e:
        print(f"JSON parsing error from OpenAI response (pros/cons): {e}")
        return {"pros": [], "cons": []}
    except Exception as e:
        print(f"Error during pros/cons extraction: {e}")
        return {"pros": [], "cons": []}
