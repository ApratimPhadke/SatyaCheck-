# SatyaCheck:

## Overview
SatyaCheck is a web application designed to verify the credibility of news articles. It analyzes the content using  cross-references social media sources such as Social Media Platforms to assess the article's authenticity.

## Features
- Extracts text from a provided URL or directly pasted content.
- Uses spaCy for keyword extraction and importance ranking.
- Fetches relevant posts from Reddit and YouTube.
- Computes keyword match percentage to evaluate credibility.
- Provides a credibility assessment with a confidence score and status description.

## Technologies Used
- **Python**: Primary programming language.
- **Streamlit**: Web application framework.
- **spaCy**: NLP for keyword extraction.
- **praw**: Reddit API wrapper.
- **Google YouTube API**: Fetches relevant videos.
- **BeautifulSoup**: Extracts text from web pages.
- **scikit-learn**: Implements TF-IDF vectorization and cosine similarity.

## Installation & Setup
1. Clone the repository:
   ```sh
   git clone <repository-url>
   cd SatyaCheck
   ```
2. Setup Virtual Environment
   using command
   python -m venv venv
   and  venv\Scripts\activate
4. Run the application:
   ```sh
   streamlit run app.py
   ```

## Usage
1. **Choose input method**: Paste an article or provide a URL.
2. **Extract Keywords**: The app will process the article text and extract key terms.
3. **Fetch Matching Posts**: SatyaCheck searches Reddit and YouTube for relevant posts.
4. **Assess Credibility**: Displays a credibility score based on keyword match analysis.

## Output
- **Credibility Status**: Reliable / Uncertain / Likely False.
- **Visualization**: Displays keyword match percentages and top related posts.

## License
This project is open-source and available under the MIT License.

## Disclaimer
SatyaCheck provides an automated assessment of credibility using social media signals. Users should independently verify results before drawing conclusions.

