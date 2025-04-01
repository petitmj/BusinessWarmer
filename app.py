import streamlit as st
import os
import re # Added for LLM output parsing
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from huggingface_hub import InferenceClient
from urllib.parse import urlparse # Added for URL validation and subject refinement

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
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Initial cleanup (optional but can speed up processing) ---
        # Remove elements less likely to be part of main content early
        for element in soup(['script', 'style', 'aside', 'link', 'meta']):
             element.decompose()

        # --- Find the main content area ---
        main_content = soup.find('main') or soup.find('article') or soup.find('div', role='main')
        target_element = main_content or soup.find('body') # Fallback to body

        if target_element:
             # --- Clean *within* the target element ---
             # Remove common non-content tags that might be *inside* the main area
             elements_to_remove = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'button', 'form', 'iframe', 'img', 'figure', 'figcaption']
             for tag_name in elements_to_remove:
                 for element in target_element.find_all(tag_name):
                     element.decompose()

             # Extract text from the cleaned target element
             raw_text = target_element.get_text(separator=' ', strip=True)
             st.success(f"Successfully scraped content from {url}")
             return clean_text(raw_text) # Apply final cleaning
        else:
            # This case is less likely now with the body fallback, but good practice
            st.error(f"Could not find 'main', 'article', 'div[role=main]', or even 'body' tag in the page structure of {url}.")
            return None

    except requests.exceptions.Timeout:
        st.error(f"Timeout error when trying to load {url}. The page might be too slow or complex.")
        return None
    except requests.exceptions.HTTPError as e:
         st.error(f"Failed to fetch the webpage. Status code: {e.response.status_code}. Reason: {e.response.reason}. This might be due to access restrictions (like 403 Forbidden).")
         return None
    except requests.exceptions.RequestException as e:
        st.error(f"A network error occurred while trying to fetch {url}: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during scraping {url}: {e}")
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
        raw_output = response.strip()

        # --- Recommendation 1: More Robust LLM Output Parsing ---
        # Try to find the start of the email content (e.g., "Subject:")
        # Use regex for case-insensitivity and potential whitespace variations
        match = re.search(r"Subject:", raw_output, re.IGNORECASE | re.MULTILINE) # Added MULTILINE flag
        if match:
            # Extract from the start of "Subject:" onwards
            generated_email = raw_output[match.start():]
            st.success("Email pitch generated successfully!")
            return generated_email.strip() # Strip again just in case
        else:
            # Fallback if "Subject:" is not found
            st.warning("Could not specifically find 'Subject:' in the LLM output. Returning the full response as is.")
            st.success("Email pitch generated successfully (using fallback parsing)!")
            return raw_output # Return the original stripped output

    except Exception as e:
        st.error(f"Error during LLM generation with model {model_name}: {e}")
        return None


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("🤖 AI Business Warmer for Automation Services")
st.markdown("Enter a business owner's website URL. The AI will analyze it and generate a personalized cold outreach email pitching automation services.")

# --- Recommendation 3: Add Explicit Note on Scraping Limitations ---
st.info("ℹ️ **Note:** This tool works best with websites built primarily with static HTML. It may struggle to extract content from sites heavily reliant on JavaScript (Single Page Applications) or those with strong anti-scraping protections (like Cloudflare or CAPTCHAs).")

# Allow model selection
available_models = [
    "mistralai/Mistral-7B-Instruct-v0.1",
    "google/gemma-7b-it",
    "HuggingFaceH4/zephyr-7b-beta",
    # Add other instruction-tuned models available on Inference API if desired
]
if DEFAULT_MODEL not in available_models:
    available_models.insert(0, DEFAULT_MODEL)

selected_model = st.selectbox("Select LLM Model (requires compatibility with Inference API):", available_models, index=available_models.index(DEFAULT_MODEL))

website_url = st.text_input("Enter Business Website URL:", placeholder="https://www.examplebusiness.com")

if st.button("🚀 Generate Outreach Email"):
    if website_url:
        # --- Recommendation 4: Refine URL Validation ---
        try:
            parsed_url = urlparse(website_url)
            if not all([parsed_url.scheme in ['http', 'https'], parsed_url.netloc]):
                 raise ValueError("Invalid URL structure. Must include scheme (http/https) and domain.")

            # Basic startswith check is still okay as a quick filter but less critical now
            # if not (website_url.startswith('http://') or website_url.startswith('https://')):
            #      st.warning("Please double-check the URL format (should start with http:// or https://)")
            # else: # Proceed if valid structure found

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

                        # --- Recommendation 5: Fallback for Business Name in Subject ---
                        try:
                            # Use the already parsed URL
                            domain = parsed_url.netloc
                            # Basic cleaning of domain for display
                            if domain.startswith('www.'):
                                domain = domain[4:]
                            # Simple capitalization: example.com -> Example.com, my-domain.co.uk -> My-Domain.Co.Uk
                            display_name = '.'.join(part.capitalize() for part in domain.replace('-', ' ').split('.'))
                            display_name = display_name.replace(' ', '-') # Put dashes back if any

                            # Check for generic placeholder in the first line (subject) and replace
                            lines = generated_pitch.splitlines()
                            generic_subject_part = "at Your Business"
                            if lines and generic_subject_part in lines[0]:
                                lines[0] = lines[0].replace(generic_subject_part, f"at {display_name}")
                                generated_pitch = "\n".join(lines)
                                st.caption(f"(Subject line potentially customized with domain name: {display_name})")

                        except Exception as e:
                            st.caption(f"(Could not automatically parse domain/refine subject line: {e})")
                        # --- End subject refinement ---

                        st.markdown(f"\n{generated_pitch}\n") # Use markdown for potential formatting
                    else:
                        st.error("Failed to generate email pitch after scraping.") # More specific error context
                else:
                    st.error(f"Could not get usable content from {website_url}. Cannot generate pitch.") # More specific

        except ValueError as e:
             st.error(f"Invalid URL entered: {e}. Please ensure it includes http:// or https:// and a valid domain name (e.g., https://www.example.com)")

    else:
        st.warning("Please enter a website URL.")

st.markdown("---")
st.markdown("Built with Streamlit, BeautifulSoup, Requests, and Hugging Face Inference API.")
