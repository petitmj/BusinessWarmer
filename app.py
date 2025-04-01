import streamlit as st
import requests
from bs4 import BeautifulSoup
import validators

# Ensure set_page_config() is the FIRST Streamlit command
st.set_page_config(layout="wide")

# Streamlit UI
st.title("🤖 AI Business Warmer for Automation Services")
st.markdown("Enter a business owner's website URL. The AI will analyze it and provide insights on automation opportunities.")

# Input field for the user to enter a website URL
url = st.text_input("Enter Website URL", "")

# Function to fetch website content using requests & BeautifulSoup
def fetch_website_content(url):
    # Validate URL
    if not validators.url(url):
        raise ValueError("Invalid URL format. Please enter a valid website URL.")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for failed responses (e.g., 404, 500)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.prettify()
    except requests.Timeout:
        raise TimeoutError("The website took too long to load. Try another URL.")
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch webpage: {e}")

# Button to trigger website analysis
if st.button("Analyze Website"):
    if url:
        try:
            st.write("Fetching website content...")
            website_content = fetch_website_content(url)
            st.success("Website analysis completed!")
            st.text_area("Extracted HTML Content", website_content, height=300)
        except ValueError as ve:
            st.warning(f"Input Error: {ve}")
        except TimeoutError as te:
            st.error(f"Timeout Error: {te}")
        except RuntimeError as re:
            st.error(f"An error occurred: {re}")
        except Exception as e:
            st.error(f"General Error: {e}")
    else:
        st.warning("Please enter a valid website URL.")
