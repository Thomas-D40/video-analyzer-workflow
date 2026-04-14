from typing import List, Dict
import json
import hashlib
from openai import OpenAI
from ...config import get_settings
from ...logger import get_logger

logger = get_logger(__name__)
from ...constants import (
    PROS_CONS_MAX_CONTENT_LENGTH,
    PROS_CONS_MIN_PARTIAL_CONTENT,
    LLM_TEMP_PROS_CONS_ANALYSIS,
)
from ...prompts import (
    JSON_OUTPUT_STRICT,
    CITATION_INSTRUCTION,
)

# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT = f"""You are an expert in scientific analysis and argument critique.
Analyze scientific articles to identify points that support (pros) or contradict (cons) an argument.

**STRICT VERIFICATION RULES:**
1.  **Explicit Evidence Required**: Each point ("claim") MUST be explicitly supported by the text of a provided article.
2.  **No Invention**: If no article mentions a point, DO NOT INVENT IT.
3.  **Citation Required**: Each claim must be associated with the exact URL of the article containing it.
4.  **Relevance**: Only retain points directly related to the analyzed argument.
5.  **Access Level**: Abstracts and summaries are VALID sources - do not dismiss sources for lacking full text access.

For each article, identify:
- Claims that SUPPORT the argument (pros)
- Claims that CONTRADICT or QUESTION the argument (cons)

{JSON_OUTPUT_STRICT}

**RESPONSE FORMAT:**
{{
    "pros": [{{"claim": "point description (with implicit citation)", "source": "article URL"}}],
    "cons": [{{"claim": "point description (with implicit citation)", "source": "article URL"}}]
}}

If no article contains relevant information, return empty lists."""

USER_PROMPT_TEMPLATE = """Argument to analyze: {argument}

Scientific articles:
{articles_context}

Analyze these articles and extract supporting (pros) and contradicting (cons) points for this argument."""

# ============================================================================
# LOGIC
# ============================================================================

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

    logger.debug("pros_cons_input", argument_preview=argument[:50], articles_count=len(articles))

    if not argument or not articles:
        logger.debug("pros_cons_empty", has_argument=bool(argument), articles_count=len(articles) if articles else 0)
        return {"pros": [], "cons": []}

    # Generate a unique ID for the argument if not provided
    if not argument_id:
        argument_id = hashlib.md5(argument.encode()).hexdigest()[:8]

    # Format articles context (use fulltext if available, otherwise snippet/abstract)
    articles_context = ""
    current_length = 0

    fulltext_count = 0
    abstract_count = 0

    for article in articles:
        # Prefer fulltext over abstract/snippet
        content = ""
        content_type = "Summary"

        if "fulltext" in article and article["fulltext"]:
            content = article["fulltext"]
            content_type = "Full Text"
            fulltext_count += 1
        else:
            # Fallback to snippet/abstract
            content = article.get('snippet') or article.get('abstract') or article.get('summary', '')
            content_type = "Summary"
            abstract_count += 1

        article_text = f"Article: {article.get('title', '')}\nURL: {article.get('url', '')}\n{content_type}: {content}\n\n"

        if current_length + len(article_text) > PROS_CONS_MAX_CONTENT_LENGTH:
            # Still include at least partial content
            remaining_space = PROS_CONS_MAX_CONTENT_LENGTH - current_length
            if remaining_space > PROS_CONS_MIN_PARTIAL_CONTENT:
                article_text = f"Article: {article.get('title', '')}\nURL: {article.get('url', '')}\n{content_type}: {content[:remaining_space]}\n\n"
                articles_context += article_text
            break

        articles_context += article_text
        current_length += len(article_text)

    logger.debug("pros_cons_content", fulltext_count=fulltext_count, abstract_count=abstract_count, total_chars=current_length)

    if len(articles) > 0 and not articles_context:
         # Fallback if the first article is too long
         first_content = articles[0].get('fulltext') or articles[0].get('snippet', '')
         articles_context = f"Article: {articles[0].get('title', '')}\nURL: {articles[0].get('url', '')}\nContent: {first_content[:PROS_CONS_MAX_CONTENT_LENGTH]}\n\n"

    client = OpenAI(api_key=settings.openai_api_key)

    # Build prompts from constants
    user_prompt = USER_PROMPT_TEMPLATE.format(
        argument=argument,
        articles_context=articles_context
    )


    try:
        response = client.chat.completions.create(
            model=settings.openai_model,  # Use fast model for analysis
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=LLM_TEMP_PROS_CONS_ANALYSIS,
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
        logger.error("pros_cons_json_error", detail=str(e))
        return {"pros": [], "cons": []}
    except Exception as e:
        logger.error("pros_cons_failed", detail=str(e))
        return {"pros": [], "cons": []}
