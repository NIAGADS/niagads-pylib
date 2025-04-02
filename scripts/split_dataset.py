import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

def split_articles():
    try:
        print("Reading articles from new_alzheimer_articles.csv...")
        df = pd.read_csv('new_alzheimer_articles.csv')
        
        total_articles = len(df)
        print(f"Total articles found: {total_articles}")
        
        train_df, test_df = train_test_split(df, test_size=0.2)
        
        train_df.to_csv('alzheimer_articles_train.csv', index=False)
        print(f"Saved {len(train_df)} articles to alzheimer_articles_train.csv")
        
        test_df.to_csv('alzheimer_articles_test.csv', index=False)
        print(f"Saved {len(test_df)} articles to alzheimer_articles_test.csv")
        
        print("\nDataset Split Summary:")
        print(f"Training set size: {len(train_df)} articles ({len(train_df)/total_articles*100:.1f}%)")
        print(f"Testing set size: {len(test_df)} articles ({len(test_df)/total_articles*100:.1f}%)")
        
    except FileNotFoundError:
        print("Error: new_alzheimer_articles.csv not found. Please run keyword_article_finder.py first.")
    except Exception as e:
        print(f"Error splitting articles: {str(e)}")

if __name__ == "__main__":
    split_articles() 