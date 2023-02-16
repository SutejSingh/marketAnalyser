import praw
import os
from praw.models import MoreComments
from stocksymbol import StockSymbol
from rq.job import Job
import rq
import spacy
import requests
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import json


stockSet = set()
importantStockSet = set() #tickers
nameToTicker = {} #names to ticker
reddit = None
comments = []
analyzer = SentimentIntensityAnalyzer()


newsData = []

newsWeight = 1.5
job = rq.get_current_job()

def redditApiSetup(threadNum, commNum):
    print("QUERYING REDDIT")
    job.meta['progress'] = "Querying Reddit"
    job.save_meta()
    
    reddit = praw.Reddit(
        client_id= os.getenv('CLIENT_ID'),
        client_secret= os.getenv('CLIENT_SECRET'),
        user_agent="Comment Extraction (by u/USERNAME)",
    )    
    
    print("REDDIT QUERY COMPLETE")
    job.meta['progress'] = "Reddit Query Complete"
    job.save_meta()
    
    print("QUERYING WALLSTREETBETS")
    job.meta['progress'] = "Querying Wallstreetbets"
    job.save_meta()
    
    subreddit = reddit.subreddit("wallstreetbets")
    widgets = subreddit.widgets
    text_area = None
    for widget in widgets.sidebar:
        if isinstance(widget, praw.models.TextArea):
            text_area = widget
            break
    
    text = text_area.text.splitlines()

    for line in text[3:]:
        line = line.replace(' ', '').replace('|', '')
        stock = ''
        for i in range(len(line)):
            if line[i].isalpha():
                stock += line[i]
            else:
                if stock != '':
                    importantStockSet.add(stock.upper())
                    stock = ''
            i += 1
        

    for submission in subreddit.new(limit=threadNum):
        comments.append(submission.title)
        submission.comments.replace_more(limit=commNum)
        for comment in submission.comments.list():
            comments.append(comment.body)
    print("ANALYSING " + str(len(comments)) + " COMMENTS")
    print("WALLSTREETBETS QUERY COMPLETE")
    job.meta['progress'] = "Wallstreetbets Query Complete"
    job.save_meta()
            
def stockApiSetup():
    print("QUERYING STOCK API")
    job.meta['progress'] = "Querying Stock API"
    job.save_meta()
    
    ss = StockSymbol(os.getenv('STOCKAPI_KEY'))
    symbol_list_us = ss.get_symbol_list(market="US")
    
    for symbol in symbol_list_us:
        stockSet.add(symbol['symbol'].upper())
        stockSet.add(symbol['shortName'].upper())
        stockSet.add(symbol['longName'].upper())
        nameToTicker[symbol['shortName'].upper()] = symbol['symbol'].upper()
        nameToTicker[symbol['longName'].upper()] = symbol['symbol'].upper()
        nameToTicker[symbol['symbol'].upper()] = symbol['symbol'].upper()
    print("STOCK API QUERY COMPLETE")
    job.meta['progress'] = "Stock API Query Complete"
    job.save_meta()

def newsSetup():
    print("QUERYING NEWS")
    job.meta['progress'] = "Querying News"
    job.save_meta()

    urls = ["https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069",
            "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
            "https://www.investing.com/rss/market_overview.rss",
            "https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms",
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen"]
    
    
    for url in urls:
        feed_content = requests.get(url)
        feed = feedparser.parse(feed_content.text)
        
        for entry in feed.entries:
            text = entry.title
            # if "http" not in entry.summary:
            #     text += entry.summary
            newsData.append(text)
    print("ANALYSING " + str(len(newsData)) + " NEWS DATA POINTS")
    print("NEWS QUERY COMPLETE")
    job.meta['progress'] = "News Query Complete"
    job.save_meta()
    
def setup(threadNum, commNum):
    print("=====INITIALIZING")
    job.meta['progress'] = "Initializing"
    job.save_meta()
    
    stockApiSetup()
    redditApiSetup(threadNum, commNum)
    newsSetup()
    print("=====INITIALIZATION COMPLETE")
    job.meta['progress'] = "Initialization Complete"
    job.save_meta()
    
        
def numericSentiment(text):
    vs = analyzer.polarity_scores(text)
    return (vs['pos'] - vs['neg'])

def subject(text, nlp):
    doc = nlp(text)
    return [tok for tok in doc if (tok.dep_ == "nsubj") ]
    
def main(threadNum, commNum):
    
    threadNum = int(threadNum)
    commNum = int(commNum)
    
    setup(threadNum, commNum)
    print("LOADING SPACY")
    job.meta['progress'] = "Loading Spacy"
    job.save_meta()
    
    nlp = spacy.load("en_core_web_sm")
    print("SPACY LOADED")
    job.meta['progress'] = "Spacy Loaded"
    job.save_meta()
    
    occurrences = {}
    print("=====STARTING COMMENT ANALYSIS")
    job.meta['progress'] = "Starting Comment Analysis"
    job.save_meta()
    
    postData = []
    newsDataObjArr = []
    
    for comment in comments:
        sentiment = numericSentiment(comment)
        sub = subject(comment, nlp)
        
        postDatum = {}
        postDatum['comment'] = comment
        postDatum['sentiment'] = sentiment
        postDatum['subjects'] = []
        
        postData.append(postDatum)
        
        for item in sub:
            postDatum['subjects'].append(item.text)
            stockName = item.text.upper()
            if stockName in nameToTicker.keys():
                ticker = nameToTicker[stockName]
                if ticker in occurrences:
                    occurrences[ticker] += sentiment
                elif ticker in importantStockSet:
                    occurrences[ticker] = sentiment

            
    print("=====COMMENT ANALYSIS COMPLETE")
    job.meta['progress'] = "Comment Analysis Complete"
    job.save_meta()
    
    print("=====STARTING NEWS ANALYSIS")
    job.meta['progress'] = "Starting News Analysis"
    job.save_meta()
    
    for text in newsData:
        sentiment = numericSentiment(text)
        sub = subject(text, nlp)
        
        newsDatum = {}
        newsDatum['news'] = text
        newsDatum['subjects'] = []
        newsDatum['sentiment'] = sentiment
        
        newsDataObjArr.append(newsDatum)
        
        for item in sub:
            stockName = item.text.upper()
            newsDatum['subjects'].append(item.text)
            if stockName in nameToTicker.keys():
                ticker = nameToTicker[stockName]
                if ticker in occurrences:
                    occurrences[ticker] += sentiment
                elif ticker in importantStockSet:
                    occurrences[ticker] = sentiment
        
    print("=====NEWS ANALYSIS COMPLETE")
    job.meta['progress'] = "News Analysis Complete"
    job.save_meta()
    #sort occrrences by value
    occurrences = dict(sorted(occurrences.items(), key=lambda item: item[1], reverse=True))
    resObj = dict({  
            "result": occurrences,
            "newsData": newsDataObjArr,
            "postData": postData
        })
    print(occurrences)
    # resObj = json.dumps(resObj)
    
    # resObj = json.dumps(resObj, default=lambda resObj: resObj.__dict__)
    return resObj
 

if __name__ == "__main__":
    main()
    