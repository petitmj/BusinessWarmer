import streamlit as st
import os
import re
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from huggingface_hub import InferenceClient

# --- Configuration ---

# Load .env file if it exists (primarily for local development)
load_dotenv()

# Try fetching the token from Streamlit secrets first (for deployed apps)
# then fall back to environment variables (for local or other environments)
HF_API_TOKEN = None # Initialize as None
if hasattr(st, 'secrets') and "HUGGINGFACEHUB_API_TOKEN" in st.secrets:
    # Use secret from Streamlit Cloud deployment
    HF_API_TOKEN = st.secrets["HUGGINGFACEHUB_API_TOKEN"]
else:
    # Fallback for local development (using .env file) or other environments
    HF_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Check if API token was found through EITHER method
if not HF_API_TOKEN:
    # Display error and stop if no token is found from secrets or .env
    st.error("Hugging Face API token not found. Ensure 'HUGGINGFACEHUB_API_TOKEN' is set correctly in Streamlit secrets (for deployment) or your local .env file (for local testing).")
    st.stop() # Stop execution if no token is found

# --- Initialize Hugging Face Client (Do this ONCE, after token is confirmed) ---
try:
    hf_client = InferenceClient(token=HF_API_TOKEN)
except Exception as e:
    st.error(f"Failed to initialize Hugging Face client: {e}")
    st.stop()

# --- Constants ---
DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.1"
MAX_SCRAPED_TEXT_LENGTH = 4000 # Limit text sent to LLM to manage tokens/cost

# --- Helper Functions --- 

def clean_text(text):
    """Removes excessive whitespace and non-printable chars."""
    text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespace with single space
    text = ''.join(char for char in text if char.isprintable())
    return text.strip()

def scrape_website_content(url: str) -> str | None:
    """Scrapes the main textual content from a website using BeautifulSoup and requests."""
    st.write(f"Attempting to scrape: {url}")
    try:
        # Send GET request to the URL
        response = requests.get(url, timeout=60)  # Timeout after 60 seconds
        if response.status_code != 200:
            st.error(f"Failed to fetch the webpage. Status code: {response.status_code}")
            return None

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script, style, and other non-relevant elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # Extract main content from 'main', 'article', or 'body' tags
        main_content = soup.find('main') or soup.find('article') or soup.find('div', role='main')
        if main_content:
            raw_text = main_content.get_text(separator=' ', strip=True)
        else:
            # Fallback to body if specific main tags aren't found
            body = soup.find('body')
            if body:
                raw_text = body.get_text(separator=' ', strip=True)

        st.success(f"Successfully scraped content from {url}")
        return clean_text(raw_text)

    except requests.exceptions.Timeout:
        st.error(f"Timeout error when trying to load {url}. The page might be too slow or complex.")
        return None
    except Exception as e:
        st.error(f"An error occurred during scraping {url}: {e}")
        return None

def generate_llm_pitch(scraped_content: str, business_url: str, model_name: str) -> str | None:
    """Generates a personalized email pitch using an LLM."""
    if not scraped_content:
        st.warning("No content scraped, cannot generate pitch.")
        return None

    # Limit the length of text sent to the LLM
    content_to_analyze = scraped_content[:MAX_SCRAPED_TEXT_LENGTH]
    if len(scraped_content) > MAX_SCRAPED_TEXT_LENGTH:
        st.info(f"Note: Website text truncated to {MAX_SCRAPED_TEXT_LENGTH} characters for analysis.")

    # Construct the prompt for the LLM
    prompt = f"""
    Analyze the following text scraped from the website {business_url}:
    --- WEBSITE TEXT ---
    {content_to_analyze}
    --- END WEBSITE TEXT ---

    Based *only* on the text provided:
    1. Briefly identify the primary services or products offered by the business.
    2. Infer potential operational inefficiencies or areas where automation services could provide value (e.g., manual appointment booking if no online system is mentioned, repetitive tasks implied by service descriptions, lack of clear online sales process). Be specific if possible, but avoid making definitive claims if the text is vague.
    3. Generate a concise, personalized, and professional cold outreach email (around 150-200 words) addressed to the business owner.

    The email should:
    - Start with a brief, relevant observation about their business based *specifically* on the scraped text (e.g., "I saw on your website, {business_url}, that you offer [Service Mentioned]...").
    - Gently introduce a *potential* challenge or opportunity related to automation that might resonate based on your analysis (e.g., "Many businesses offering similar services find that automating [Specific Process like 'client scheduling' or 'quote generation'] can save significant time...").
    - Briefly introduce your automation services as a possible solution to such challenges.
    - Include a clear, low-friction call to action (e.g., "Would you be open to a brief 10-minute call next week to explore if automation could benefit your operations?").
    - Maintain a helpful and professional tone. Avoid overly aggressive sales language.
    - Do NOT invent information not present in the text (like specific employee names or internal processes).

    Output *only* the generated email content below, starting with a subject line like "Subject: Enhancing [Business Area] Operations at [Business Name inferred from URL/Content if possible, otherwise use 'Your Business']".
    """

    st.write(f"Generating pitch using model: {model_name}...")
    try:
        response = hf_client.text_generation(
            prompt=prompt,
            model=model_name,
            max_new_tokens=400,  # Adjust token limit as needed
            temperature=0.7,     # Controls creativity (lower is more focused)
            top_p=0.9,           # Nucleus sampling
            repetition_penalty=1.1 # Penalize repeating words
        )
        # The response might include the prompt or other artifacts depending on the model,
        # try to clean it up if necessary. Often the core generated text is the main part.
        # Simple extraction: assume the response *is* the email. More robust parsing might be needed.
        generated_email = response.strip()
        st.success("Email pitch generated successfully!")
        return generated_email

    except Exception as e:
        st.error(f"Error during LLM generation with model {model_name}: {e}")
        return None


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("🤖 AI Business Warmer for Automation Services")
st.markdown("Enter a business owner's website URL. The AI will analyze it and generate a personalized cold outreach email pitching automation services.")

# Allow model selection (optional, defaults to one known to work well)
available_models = [
    "mistralai/Mistral-7B-Instruct-v0.1",
    "google/gemma-7b-it",
    "HuggingFaceH4/zephyr-7b-beta",
    # Add other instruction-tuned models available on Inference API if desired
]
# Ensure default is first in list for the selectbox
if DEFAULT_MODEL not in available_models:
    available_models.insert(0, DEFAULT_MODEL)

selected_model = st.selectbox("Select LLM Model (requires compatibility with Inference API):", available_models, index=available_models.index(DEFAULT_MODEL))


website_url = st.text_input("Enter Business Website URL:", placeholder="https://www.examplebusiness.com")

if st.button("🚀 Generate Outreach Email"):
    if website_url:
        # Basic URL validation
        if not (website_url.startswith('http://') or website_url.startswith('https://')):
            st.warning("Please enter a valid URL starting with http:// or https://")
        else:
            with st.spinner(f"Analyzing {website_url}... Please wait."):
                # Step 1: Scrape Website
                scraped_data = scrape_website_content(website_url)

                if scraped_data:
                    st.subheader("Scraped Content Summary (First 500 chars):")
                    st.text_area("Scraped Text", scraped_data[:500] + "...", height=150, disabled=True)

                    # Step 2: Generate Pitch using LLM
                    generated_pitch = generate_llm_pitch(scraped_data, website_url, selected_model)

                    if generated_pitch:
                        st.subheader("✨ Generated Email Pitch:")
                        st.markdown(f"\n{generated_pitch}\n") # Use markdown code block for better formatting
                    else:
                        st.error("Failed to generate email pitch.")
                else:
                    st.error(f"Could not scrape content from {website_url}. Cannot generate pitch.")
    else:
        st.warning("Please enter a website URL.")

st.markdown("---")
st.markdown("Built with Streamlit, BeautifulSoup, Requests, and Hugging Face Inference API.")
