import streamlit as st
import os
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from huggingface_hub import InferenceClient

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file
HF_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
# Recommended: Choose a good instruction-following model available on the free Inference API tier
# Examples: 'mistralai/Mistral-7B-Instruct-v0.1', 'google/gemma-7b-it', 'HuggingFaceH4/zephyr-7b-beta'
DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.1"
MAX_SCRAPED_TEXT_LENGTH = 4000 # Limit text sent to LLM to manage tokens/cost

# Check if API token is available
if not HF_API_TOKEN:
    st.error("Hugging Face API token not found. Please set HUGGINGFACEHUB_API_TOKEN in your .env file.")
    st.stop()

# Initialize Hugging Face Inference Client
try:
    hf_client = InferenceClient(token=HF_API_TOKEN)
except Exception as e:
    st.error(f"Failed to initialize Hugging Face client: {e}")
    st.stop()

# --- Helper Functions ---

def clean_text(text):
    """Removes excessive whitespace and non-printable chars."""
    text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespace with single space
    text = ''.join(char for char in text if char.isprintable())
    return text.strip()

def scrape_website_content(url: str) -> str | None:
    """Scrapes the main textual content from a website using Playwright and BeautifulSoup."""
    st.write(f"Attempting to scrape: {url}")
    raw_text = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) # Use headless=False for debugging
            page = browser.new_page()
            # Go to URL with a timeout
            page.goto(url, timeout=60000) # 60 seconds timeout
            # Wait for network idle to ensure dynamic content is loaded
            page.wait_for_load_state("networkidle", timeout=30000)

            html_content = page.content()
            browser.close()

            soup = BeautifulSoup(html_content, 'lxml') # 'lxml' is generally faster

            # Attempt to extract meaningful text (adjust selectors as needed)
            # Prioritize main content areas, remove scripts/styles
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()

            # Get text from the body, trying common main content tags first
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

    except PlaywrightTimeoutError:
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
        # Fallback attempt with default model if a different one was selected? (Optional)
        # if model_name != DEFAULT_MODEL:
        #     st.warning(f"Trying fallback model: {DEFAULT_MODEL}")
        #     return generate_llm_pitch(scraped_content, business_url, DEFAULT_MODEL) # Be careful of infinite loops
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
                        st.markdown(f"```\n{generated_pitch}\n```") # Use markdown code block for better formatting
                        # st.text_area("Generated Email", generated_pitch, height=300) # Alternative display
                    else:
                        st.error("Failed to generate email pitch.")
                else:
                    st.error(f"Could not scrape content from {website_url}. Cannot generate pitch.")
    else:
        st.warning("Please enter a website URL.")

st.markdown("---")
st.markdown("Built with Streamlit, Playwright, BeautifulSoup, and Hugging Face Inference API.")
