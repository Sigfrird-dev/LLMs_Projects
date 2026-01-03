# System & Environment
# =======================

import os
import traceback
from dotenv import load_dotenv

# =======================
# Web scraping
# =======================
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ========================
# AI-related
# ========================
from IPython.display import Markdown, display
from openai import OpenAI
import ollama

# load environment variables in a file called .env

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

# Check for api key

if not api_key:
    print("No API key was found")

elif not api_key.startswith("sk-proj-"):
    print("An API KEY was found but doesn't start sk-proj-")

elif api_key.strip() != api_key:
    print("An API KEY was found, but it looks like it might have space or tab characters at the start or end")

else:
    print("API KEY found and looks good")

MODEL_OLLAMA = "llama3.2"


class WebSummarizer:
    def __init__(self, url, model_name=MODEL_OLLAMA):
        self.url = url
        self.model_name = model_name
        self.title = ""
        self.text = ""
        self.scrape()

    def scrape(self):
        try:
            # Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # Try to find Chrome
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(
                    os.getenv('USERNAME')),
            ]

            chrome_binary = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    break

            if chrome_binary:
                chrome_options.binary_location = chrome_binary

            # Create driver with webdriver-manager (with fallback)
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(
                    service=service, options=chrome_options)
            except Exception as e:
                print(f"Warning: Could not use webdriver-manager: {e}")
                # Fallback to system Chrome driver
                driver = webdriver.Chrome(options=chrome_options)

            driver.set_page_load_timeout(30)

            print(f"Loading: {self.url}")
            driver.get(self.url)

            # Wait for page to load
            time.sleep(5)

            # Try to wait for main content

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "main"))
                )
            except Exception:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except Exception:
                    pass  # Continue anyway

            # Get title and page source
            self.title = driver.title
            page_source = driver.page_source
            driver.quit()

            print(f"Page loaded: {self.title}")

            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')

            # Remove unwanted elements
            for element in soup(["script", "style", "img", "input", "button", "nav", "footer", "header"]):
                element.decompose()

            # Get main content
            main = soup.find('main') or soup.find(
                'article') or soup.select_one('.content') or soup.find('body')
            if main:
                self.text = main.get_text(separator="\n", strip=True)
            else:
                self.text = soup.get_text(separator="\n", strip=True)

            # Clean up text
            lines = [line.strip() for line in self.text.split(
                '\n') if line.strip() and len(line.strip()) > 2]
            self.text = '\n'.join(lines[:200])  # Limit to first 200 lines

            print(f"Extracted {len(self.text)} characters")

        except Exception as e:
            print(f"Error occurred: {e}")
            self.title = "Error occurred"
            self.text = "Could not scrape website content"


system_prompt = "You are an assistant that analyzes the contents of a website \
and provides a short summary, ignoring text that might be navigation related. \
Respond in markdown."


def user_prompt_for(website):
    user_prompt = f"You are looking at a website titled {website.title}"
    user_prompt += "\nThe contents of this website is as follows; please provide a short summary of this website in markdown. If it includes news or announcements, then summarize these too.\n\n"
    user_prompt += website.text
    return user_prompt


def messages_for(website):
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_for(website)}
    ]


def summarize_ollama(url):
    """Scrape website and summarize with Ollama"""
    site = WebSummarizer(url)

    if "Error occurred" in site.title or len(site.text) < 50:
        print(f"Failed to scrape meaningful content from {url}")
        return

    print("🤖 Creating summary...")

    try:
        # Create summary using Ollama
        response = ollama.chat(
            model=MODEL_OLLAMA,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_for(site)}
            ]
        )

        # Handle response format (ollama returns dict with 'message' key)
        if isinstance(response, dict):
            web_summary = response.get('message', {}).get('content', '')
        elif hasattr(response, 'message'):
            web_summary = getattr(response.message, 'content', '')
        else:
            web_summary = str(response)

        if web_summary:
            display(Markdown(web_summary))
        else:
            print(f"Failed to generate summary. Response: {response}")
    except Exception as e:
        print(f"Error generating summary: {e}")
        traceback.print_exc()


summarize_ollama('https://openai.com')
# summarize_ollama('https://stripe.com')
# summarize_ollama('https://vercel.com')
# summarize_ollama('https://react.dev')
