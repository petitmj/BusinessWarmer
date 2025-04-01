import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError
import validators
# Ensure Playwright browsers are installed before launching
from playwright.__main__ import main

main(["install"])


# Ensure set_page_config() is the FIRST Streamlit command
st.set_page_config(layout="wide")

# Streamlit UI
st.title("🤖 AI Business Warmer for Automation Services")
st.markdown("Enter a business owner's website URL. The AI will analyze it and provide insights on automation opportunities.")

# Input field for the user to enter a website URL
url = st.text_input("Enter Website URL", "")

# Function to fetch website content using Playwright
def fetch_website_content(url):
    # Validate URL
    if not validators.url(url):
        raise ValueError("Invalid URL format. Please enter a valid website URL.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        
        try:
            page.goto(url, timeout=10000)  # Set timeout to 10s
            content = page.content()
        except TimeoutError:
            raise TimeoutError("The website took too long to load. Try another URL.")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")
        finally:
            browser.close()
    
    return content

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
