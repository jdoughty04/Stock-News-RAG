import os
import sys
import openai
from serpapi import GoogleSearch
from newspaper import Article
import logging

# Optional: Configure logging for newspaper3k to suppress verbose output
logging.basicConfig(level=logging.WARNING)

def get_api_keys():
    """
    Retrieves SerpApi and OpenAI API keys from environment variables.
    If not found, prompts the user to input them.
    
    Returns:
        tuple: (serpapi_key, openai_api_key)
    """
    serpapi_key = os.getenv('SERPAPI_API_KEY')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not serpapi_key:
        serpapi_key = input("Enter your SerpApi API Key: ").strip()
    if not openai_api_key:
        openai_api_key = input("Enter your OpenAI API Key: ").strip()
    
    return serpapi_key, openai_api_key

def get_user_query():
    """
    Prompts the user to enter a search query.
    
    Returns:
        str: The user's search query.
    """
    query = input("Enter your search query for Google News: ").strip()
    if not query:
        print("Search query cannot be empty.")
        sys.exit(1)
    return query

def get_google_news_articles(query, serpapi_key, num_articles=10):
    """
    Fetches news articles from Google News using SerpApi.
    
    Args:
        query (str): The search query string.
        serpapi_key (str): Your SerpApi API key.
        num_articles (int): Number of articles to retrieve (default is 10).
    
    Returns:
        list: A list of dictionaries containing article details.
    """
    params = {
        "engine": "google",
        "q": query,
        "tbm": "nws",           # 'nws' specifies the News tab
        "api_key": serpapi_key,
        "num": num_articles     # Number of results to return
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        news_results = results.get('news_results', [])
        if not news_results:
            print("No news articles found for the given query.")
            sys.exit(1)
        
        articles = []
        for article in news_results:
            article_info = {
                "title": article.get("title"),
                "link": article.get("link"),
                "source": article.get("source"),
                "published_date": article.get("published"),
                "snippet": article.get("snippet")
            }
            articles.append(article_info)
        
        return articles

    except Exception as e:
        print(f"An error occurred while fetching articles: {e}")
        sys.exit(1)

def extract_article_text(url):
    """
    Extracts the main text content from a news article URL.
    
    Args:
        url (str): The URL of the news article.
    
    Returns:
        tuple: (success: bool, text: str)
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text.strip()
        if text:
            return True, text
        else:
            return False, "Content could not be retrieved."
    except Exception as e:
        print(f"Failed to extract text from {url}: {e}")
        return False, "Content could not be retrieved."

def prepare_prompt(articles):
    """
    Prepares the prompt by including titles and bodies of the articles.
    Modify this function to customize the prompt as needed.
    
    Args:
        articles (list): List of article dictionaries with 'title' and 'full_text'.
    
    Returns:
        str: The composed prompt for GPT-4.
    """
    num_articles = len(articles)
    prompt = f"Here are {num_articles} news articles:\n\n"
    for idx, article in enumerate(articles, start=1):
        prompt += f"Article {idx}:\n"
        prompt += f"Title: {article['title']}\n"
        prompt += f"Content: {article['full_text']}\n\n"
    
    prompt += "Please provide your analysis based on the above articles. Focus on the potential reasons behind a recent change in stock price."
    return prompt

def send_to_gpt(prompt, openai_api_key):
    """
    Sends the prompt to OpenAI's GPT-4 and retrieves the response.
    
    Args:
        prompt (str): The prompt to send to GPT-4.
        openai_api_key (str): Your OpenAI API key.
    
    Returns:
        str: The response from GPT-4.
    """
    openai.api_key = openai_api_key
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        reply = response['choices'][0]['message']['content'].strip()
        return reply
    except AttributeError as ae:
        print(f"AttributeError: {ae}")
        print("Please ensure the 'openai' package is up-to-date.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while communicating with OpenAI API: {e}")
        sys.exit(1)

def display_gpt_response(response):
    """
    Displays the GPT-4 response.
    
    Args:
        response (str): The response from GPT-4.
    """
    print("\n--- GPT-4 Response ---\n")
    print(response)
    print("\n-----------------------\n")

def main():
    serpapi_key, openai_api_key = get_api_keys()
    
    query = get_user_query()
    
    print("\nFetching up to 10 news articles...\n")
    articles = get_google_news_articles(query, serpapi_key, num_articles=10)
    
    successful_articles = []
    for idx, article in enumerate(articles, start=1):
        if len(successful_articles) >= 5:
            break  # Already have 5 successful articles
        print(f"Attempting to extract content from Article {idx}: {article['link']}")
        success, full_text = extract_article_text(article['link'])
        if success:
            print(f"Successfully extracted Article {idx}")
            article['full_text'] = full_text
            successful_articles.append(article)
        else:
            print(f"Failed to extract Article {idx}, skipping.")
    
    if not successful_articles:
        print("No articles were successfully retrieved. Exiting.")
        sys.exit(1)
    elif len(successful_articles) < 5:
        print(f"\nOnly {len(successful_articles)} articles were successfully retrieved.\n")
    else:
        print("\nSuccessfully retrieved 5 articles.\n")
    
    prompt = prepare_prompt(successful_articles)
    

    
    print("Sending data to GPT-4 for processing...\n")
    gpt_response = send_to_gpt(prompt, openai_api_key)
    
    display_gpt_response(gpt_response)

if __name__ == "__main__":
    main()
