# AI Business Warmer 🤖

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

An AI-powered tool to generate personalized cold outreach emails for automation services by analyzing a business's website.

## Overview

This tool helps streamline the initial phase of business development and prospecting for automation service providers. You enter a target business's website URL, and the application:

1.  **Scrapes** the website using Playwright and BeautifulSoup to extract textual content about their services and operations.
2.  **Analyzes** the scraped text using a Hugging Face Language Model (LLM) to identify potential inefficiencies or areas where automation could be beneficial.
3.  **Generates** a concise, personalized cold outreach email draft highlighting these potential opportunities and introducing your automation services.
4.  Provides a simple **Streamlit interface** for easy input and output viewing.

**🔥 Why is this useful?**

* **Effortless Prospecting:** Quickly generate initial contact points.
* **Tailored Messaging:** Move beyond generic templates with AI-driven personalization based on the prospect's own website.
* **Warm Leads:** Identify potential needs and frame your outreach accordingly, making the first contact more relevant.
* **Demonstration:** Easily showcase a practical AI application for lead generation.

## Features

* Accepts any public website URL as input.
* Uses Playwright for robust scraping of potentially dynamic websites.
* Leverages BeautifulSoup for efficient HTML parsing.
* Connects to Hugging Face Inference API for powerful text analysis and generation.
* Generates personalized email drafts including subject lines.
* Simple and interactive UI built with Streamlit.
* Configurable LLM model selection via the UI.
* Secure API key management using `.env` file.

## Tech Stack

* **Python** 3.9+
* **Streamlit:** Web application framework for the UI.
* **Playwright:** Browser automation and dynamic web scraping.
* **BeautifulSoup4 (bs4) + lxml:** HTML parsing.
* **Hugging Face Hub (`huggingface_hub`):** Client for interacting with the Hugging Face Inference API.
* **Python Dotenv (`python-dotenv`):** Environment variable management.

## Setup & Installation

1.  **Prerequisites:**
    * Python 3.9 or later installed.
    * `pip` package installer.
    * Git (optional, for cloning).

2.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url> # Replace with your repo URL
    cd ai-business-warmer # Or your chosen directory name
    ```

3.  **Set up Hugging Face API Token:**
    * Get a free API token from [Hugging Face Settings](https://huggingface.co/settings/tokens) (requires an account). Create a token with `read` access.
    * Create a file named `.env` in the project's root directory.
    * Add your token to the `.env` file:
        ```env
        HUGGINGFACEHUB_API_TOKEN=<YOUR_HUGGING_FACE_TOKEN>
        ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Install Playwright Browsers:**
    * Playwright needs browser binaries to function. Run this command once:
    ```bash
    playwright install
    ```
    *(This might take a few minutes as it downloads browser executables).*

## Running the Application

1.  Navigate to the project directory in your terminal.
2.  Run the Streamlit application:
    ```bash
    streamlit run app.py
    ```
3.  The application should automatically open in your web browser, usually at `http://localhost:8501`.

## Configuration

* **Hugging Face API Token:** Must be set in the `.env` file as `HUGGINGFACEHUB_API_TOKEN`.
* **LLM Model:** You can select the Hugging Face Inference API model to use directly within the Streamlit UI. Tested models include:
    * `mistralai/Mistral-7B-Instruct-v0.1` (Default)
    * `google/gemma-7b-it`
    * `HuggingFaceH4/zephyr-7b-beta`
    * *Note: Ensure the selected model is compatible with the free tier or your Hugging Face plan.*
* **Scraping Limits:** The `MAX_SCRAPED_TEXT_LENGTH` variable in `app.py` limits the amount of text sent to the LLM to prevent excessive token usage.

## Usage

1.  Launch the application (`streamlit run app.py`).
2.  Enter the full URL (including `http://` or `https://`) of the target business website into the input field.
3.  (Optional) Select a different LLM model from the dropdown if desired.
4.  Click the "🚀 Generate Outreach Email" button.
5.  Wait for the scraping and analysis process to complete (indicated by spinners).
6.  Review the "Scraped Content Summary" to verify text extraction.
7.  Review the "Generated Email Pitch" which contains the AI-generated outreach message. Copy and adapt it as needed before sending.

## Limitations & Potential Improvements

* **Scraping Accuracy:** Website structures vary significantly. The current scraping logic might not extract relevant content perfectly from all sites, especially complex Single Page Applications (SPAs) or sites with heavy anti-scraping measures.
* **LLM Variability:** The quality and relevance of the generated email depend heavily on the chosen LLM, the prompt quality, and the information available on the target website. Results may vary.
* **Rate Limits:** Free Hugging Face Inference API tiers have rate limits. Heavy usage might require a paid plan.
* **Contextual Understanding:** The AI only analyzes the text found on the page. It lacks deeper context about the business, market conditions, or specific personnel.
* **Ethical Use:** Use this tool responsibly. Ensure your outreach is relevant and provides potential value. Avoid spamming.

**Future Improvements:**

* More robust scraping selectors and strategies.
* Option to scrape multiple pages (e.g., 'About Us', 'Services').
* More sophisticated prompt engineering options.
* Integration with CRM tools.
* Error handling improvements.
* Caching results for previously scraped URLs.

## License

(Optional but recommended)
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
