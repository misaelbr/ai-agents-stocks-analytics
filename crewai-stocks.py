import json
import os
from datetime import datetime

import yfinance as yf

from crewai import Agent, Task, Crew
from crewai.process import Process

from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchResults
from dotenv import load_dotenv

import streamlit as st

load_dotenv()

def fetch_stock_prince( ticket:str ):
    stock = yf.download(ticket, start='2023-08-08', end=datetime.now().strftime("%Y-%m-%d"), progress=False)
    return stock
yahoo_finance_tool = Tool(
    name = 'yahoo_finance',
    description = 'Fetch stock price from Yahoo Finance',
    func = lambda ticket: fetch_stock_prince(ticket)
)

llm = ChatOpenAI(model="gpt-3.5-turbo")

stockPriceAnalyst = Agent(
    role="Senior Stock Price Analyst",
    goal="Find the {ticket} stock price and analyse trends",
    backstory="""You're a Senior Stock Price Analyst at a major investment firm. You've been asked to analyze the stock price of {ticket} and provide a detailed report on the trends you observe. You have access to the latest stock price data and are expected to provide a comprehensive analysis of the stock's performance.""",
    verbose=True,
    llm=llm,
    max_iter=5,
    memory=True,
    tools=[yahoo_finance_tool]
)

getStockPrice = Task(
    description="Analyse the stock price of {ticket} and create a trend analysis report of, down or sideways",
    agent=stockPriceAnalyst,
    expected_output="""Specify the stock price of {ticket} and provide a detailed analysis of the trends you observe. Include information on the stock's performance over the past year, as well as any notable patterns or fluctuations. Be sure to provide a comprehensive analysis that highlights the key factors influencing the stock's price movement.
    
    eg. Stock='APPL, price UP'
    """
)

search_tool = DuckDuckGoSearchResults(backend='news', num_results=10)

newsAnalyst = Agent(
    role="Senior News Analyst",
    goal="""Find the latest news about {ticket} and provide a summary.
        Specify the current trend of the stock price, up, down or sideways with the news context. For each request stock asset, specify a number between 0 and 100, where 0 is extreme fear and 100 is extreme greed.
    """,
    backstory="""You're a Senior News Analyst at a major investment firm. You've been asked to find the latest news about {ticket} and provide a summary of the key points. You have access to a wide range of news sources and are expected to deliver a concise and informative summary of the most relevant information.
    You understand that the stock market is influenced by a variety of factors, including news events, economic indicators, and market sentiment. Your analysis should take into account the current trend of the stock price and provide context for the news you present.
    """,
    verbose=True,
    llm=llm,
    max_iter=10,
    memory=True,
    tools=[search_tool]
)

get_news = Task(
    description=f"""Take the stoke and always include BTC to it (if not request). Use the search tool to search each one individually.
    
    The current date is {datetime.now().strftime("%Y-%m-%d")}
    
    Compose the results into a helpfull report.""",
    expected_output="""A summary of the overal market and one sentence summary for each request asset. 
    Include a fear/greed score for each asset based on the news. Use the follow format:
    <STOCK_ASSET>
    <SUMMARY BASED ON NEWS>
    <TREND PREDICTION>
    <FEAR/GREED SCORE>
    """,
    agent=newsAnalyst
)

stockAnalystWriter = Agent(
    role = "Senior Stock Analyts Writer",
    goal= """"Analyze the trends price and news and write an insighfull compelling and informative 3 paragraph long newsletter based on the stock report and price trend. """,
    backstory= """You're widely accepted as the best stock analyst in the market. You understand complex concepts and create compelling stories
    and narratives that resonate with wider audiences. 

    You understand macro factors and combine multiple theories - eg. cycle theory and fundamental analyses. 
    You're able to hold multiple opinions when analyzing anything.
""",
    verbose=True,
    llm=llm,
    max_iter=5,
    memory=True,
    allow_delegation = True
)

writeAnalysis = Task(
    description = """Use the stock price trend and the stock news report to create an analyses and write the newsletter about the {ticket} company that is brief and highlights the most important points.
    Focus on the stock price trend, news and fear/greed score. What are the near future considerations?
    Include the previous analyses of stock trend and news summary.
""",
    expected_output= """"Write in portuguese an eloquent 3 paragraphs newsletter formated as markdown in an easy readable manner. It should contain:

    - 3 bullets executive summary 
    - Introduction - set the overall picture and spike up the interest
    - main part provides the meat of the analysis including the news summary and fead/greed scores
    - summary - key facts and concrete future trend prediction - up, down or sideways.
""",
    agent= stockAnalystWriter,
    context = [getStockPrice, get_news]
)

crew = Crew(
    agents = [stockPriceAnalyst, newsAnalyst, stockAnalystWriter],
    tasks = [getStockPrice, get_news, writeAnalysis],
    verbose = False,
    process= Process.hierarchical,
    full_output=True,
    share_crew=False,
    manager_llm=llm,
    max_iter=15
)

with st.sidebar:
    st.header('Informe o papel para análise')
    
    with st.form(key='research_form'):
        topic = st.text_input('Selecione a ação')
        submit_button = st.form_submit_button(label='Iniciar análise')
        
if submit_button:
    if not topic:
        st.error('Digite o título da ação para análise:')
    else:
        results = crew.kickoff(inputs={"ticket": topic})
        
        st.subheader('Resultado da análise:')
        st.write(results['final_output'])
        