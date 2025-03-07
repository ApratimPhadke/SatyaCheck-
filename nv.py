import streamlit as st
import requests
from bs4 import BeautifulSoup
import spacy
import praw
from googleapiclient.discovery import build
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
import re
from datetime import datetime, timedelta

# Initialize spaCy model
nlp = spacy.load("en_core_web_sm")

# API Configurations (Note: Replace with your own API keys in production)
REDDIT_CLIENT_ID = "zUm08w-ffHWzi9jim_eq7w"
REDDIT_CLIENT_SECRET = "zjvo8yfii4iEHRLBXbC2-55gQf3LAQ"
REDDIT_USER_AGENT = "script:news_verifier_app:1.0 (by /u/Shlong_up )"
YOUTUBE_API_KEY = "AIzaSyCvlwp0klXfpxMag9YX-6nTdRdoiQNxGwY"

# Initialize Reddit and YouTube clients
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def extract_text_from_url(url: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text from paragraphs
        paragraphs = soup.find_all('p')
        text = "\n".join(p.get_text(strip=True) for p in paragraphs)
        
        return ' '.join(text.split())
    except Exception as e:
        st.error(f"Error extracting text from URL: {e}")
        return ""

def extract_comprehensive_keywords(article_text: str) -> dict:
    """
    Extract comprehensive keywords with their importance and context
    """
    doc = nlp(article_text)
    keywords = {}
    
    # Extract noun chunks and their frequency
    for chunk in doc.noun_chunks:
        keyword = chunk.text.strip().lower()
        if 1 <= len(keyword.split()) <= 4:
            keywords[keyword] = keywords.get(keyword, 0) + 2
    
    # Named entities with higher weight
    entity_types = ['PERSON', 'ORG', 'GPE', 'EVENT']
    for ent in doc.ents:
        if ent.label_ in entity_types:
            keyword = ent.text.strip().lower()
            keywords[keyword] = keywords.get(keyword, 0) + 3
    
    # Add important verbs and nouns
    for token in doc:
        if token.pos_ in ['NOUN', 'PROPN', 'VERB'] and len(token.text) > 3:
            keyword = token.lemma_.lower()
            keywords[keyword] = keywords.get(keyword, 0) + 1
    
    # Sort keywords by their weighted importance
    return dict(sorted(keywords.items(), key=lambda x: x[1], reverse=True))

def calculate_keyword_match(post_text: str, original_keywords: dict) -> float:
    """
    Calculate the percentage of keywords matched in a post
    """
    post_text = post_text.lower()
    total_keyword_weight = sum(original_keywords.values())
    matched_weight = 0
    
    for keyword, weight in original_keywords.items():
        if keyword.lower() in post_text:
            matched_weight += weight
    
    # Calculate match percentage
    match_percentage = (matched_weight / total_keyword_weight) * 100
    return round(match_percentage, 2)

def assess_news_credibility(posts: list) -> dict:
    """
    Assess news credibility based on individual post keyword matches
    """
    if not posts:
        return {
            'credibility_score': 0,
            'max_keyword_match': 0,
            'credibility_status': 'No Matching Posts',
            'status_description': 'Insufficient data to verify the news.',
            'color': 'gray'
        }
    
    # Get match percentages
    match_percentages = [post['keyword_match_percentage'] for post in posts]
    
    # Maximum keyword match percentage
    max_keyword_match = max(match_percentages)
    
    # Determine credibility status and color based on max keyword match
    if max_keyword_match >= 70:
        return {
            'credibility_score': max_keyword_match,
            'max_keyword_match': max_keyword_match,
            'credibility_status': 'Reliable News',
            'status_description': 'The news appears to be well-supported by social media sources. High confidence in its accuracy.',
            'color': 'blue'
        }
    elif max_keyword_match >= 50:
        return {
            'credibility_score': max_keyword_match,
            'max_keyword_match': max_keyword_match,
            'credibility_status': 'Uncertain News',
            'status_description': 'Limited social media corroboration. More investigation recommended.',
            'color': 'grey'
        }
    else:
        return {
            'credibility_score': max_keyword_match,
            'max_keyword_match': max_keyword_match,
            'credibility_status': 'there are high chances that new is not true',
            'status_description': 'Minimal social media support. High likelihood of inaccuracy.',
            'color': 'black'
        }

def fetch_comprehensive_posts(keywords: dict, max_posts: int = 100, hours_back: int = 120) -> list:
    """
    Fetch comprehensive posts from Reddit and YouTube with detailed keyword matching
    """
    posts = []
    try:
        # Calculate the timestamp for posts within the last 5 days
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Prepare keyword query
        keyword_list = list(keywords.keys())
        query = " ".join(keyword_list)
        
        # Fetch Reddit posts
        for submission in reddit.subreddit('all').search(query, limit=max_posts, sort='new'):
            post_time = datetime.fromtimestamp(submission.created_utc)
            
            if post_time > time_threshold:
                full_text = f"{submission.title} {submission.selftext}"
                keyword_match = calculate_keyword_match(full_text, keywords)
                
                if keyword_match > 0:
                    post_info = {
                        'platform': 'Reddit',
                        'title': submission.title,
                        'text': submission.selftext,
                        'score': submission.score,
                        'num_comments': submission.num_comments,
                        'url': submission.url,
                        'timestamp': post_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'keyword_match_percentage': keyword_match
                    }
                    posts.append(post_info)
        
        # Fetch YouTube posts
        search_response = youtube.search().list(
            q=query,
            part="id,snippet",
            maxResults=max_posts,
            type="video",
            order="date"
        ).execute()
        
        for item in search_response.get("items", []):
            video_id = item["id"]["videoId"]
            video_response = youtube.videos().list(
                part="statistics,snippet",
                id=video_id
            ).execute()
            
            if video_response.get("items"):
                video = video_response["items"][0]
                published_time = datetime.strptime(
                    video['snippet']['publishedAt'], 
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                
                if published_time > time_threshold:
                    full_text = f"{video['snippet']['title']} {video['snippet']['description']}"
                    keyword_match = calculate_keyword_match(full_text, keywords)
                    
                    if keyword_match > 0:
                        post_info = {
                            'platform': 'YouTube',
                            'title': video['snippet']['title'],
                            'description': video['snippet']['description'],
                            'views': int(video['statistics'].get('viewCount', 0)),
                            'likes': int(video['statistics'].get('likeCount', 0)),
                            'url': f"https://youtu.be/{video_id}",
                            'timestamp': published_time.strftime("%Y-%m-%d %H:%M:%S"),
                            'keyword_match_percentage': keyword_match
                        }
                        posts.append(post_info)
        
        return sorted(posts, key=lambda x: x['keyword_match_percentage'], reverse=True)
    
    except Exception as e:
        st.error(f"Error fetching comprehensive posts: {e}")
        return []

def main():
    st.set_page_config(page_title="SatyaCheck", page_icon="🔍")
    
    st.title("🕵️ SatyaCheck")
    st.subheader("Deep Social Media Cross-Verification")
    
    # Input method selection
    input_method = st.radio(
        "How would you like to input the article?", 
        ["Paste Text", "Enter URL"], 
        horizontal=True
    )
    
    # Input text based on method
    if input_method == "Paste Text":
        input_text = st.text_area(
            "Paste full article text", 
            height=200, 
            placeholder="Paste your article content here..."
        )
    else:
        input_text = st.text_input(
            "Enter Article URL", 
            placeholder="https://example.com/news-article"
        )
    
    # Verification button
    if st.button("Verify Article", type="primary"):
        with st.spinner("Performing in-depth analysis..."):
            # Extract article text
            if input_text.startswith("http"):
                article_text = extract_text_from_url(input_text)
            else:
                article_text = input_text
            
            if not article_text:
                st.error("Could not retrieve article text.")
                return
            
            # Extract comprehensive keywords
            keywords = extract_comprehensive_keywords(article_text)
            
            # Display extracted keywords with their weights
            st.subheader("Extracted Keywords (with importance)")
            keyword_display = [f"{k} (weight: {v})" for k, v in keywords.items()]
            st.write(", ".join(keyword_display))
            
            # Fetch and analyze posts
            posts = fetch_comprehensive_posts(keywords)
            
            # Assess credibility
            credibility = assess_news_credibility(posts)
            
            # Display credibility assessment
            st.subheader("Credibility Assessment")
            
            # Color-coded credibility status
            st.markdown(f"""
            <div style="background-color:{credibility['color']}; color:white; padding:15px; border-radius:10px;">
            Credibility Status: {credibility['credibility_status']}
            
            Credibility Score: {credibility['credibility_score']}%
            
            **Max Keyword Match:** {credibility['max_keyword_match']}%
            
            **Description:** {credibility['status_description']}
            </div>
            """, unsafe_allow_html=True)
            
            # Analysis and statistics
            st.subheader("Verification Results")
            
            # Basic statistics
            total_posts = len(posts)
            st.metric("Total Relevant Posts", total_posts)
            
            # Keyword Match Distribution
            if posts:
                match_percentages = [post['keyword_match_percentage'] for post in posts]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Avg Keyword Match", 
                        f"{sum(match_percentages)/len(match_percentages):.2f}%")
                with col2:
                    st.metric("Max Keyword Match", 
                        f"{max(match_percentages):.2f}%")
                with col3:
                    st.metric("Matched Posts", 
                        f"{len([p for p in posts if p['keyword_match_percentage'] > 20])} / {total_posts}")
                
                # Detailed post view
                st.subheader("Matched Posts")
                for post in posts[:10]:  # Show top 10 matched posts
                    st.markdown(f"""
                    **Platform:** {post['platform']} | 
                    **Keyword Match:** {post['keyword_match_percentage']}% | 
                    **Title:** {post['title']}
                    
                    **URL:** {post.get('url', 'N/A')}
                    """)
            else:
                st.warning("No relevant posts found matching the article's keywords.")

if __name__ == "__main__":
    main()