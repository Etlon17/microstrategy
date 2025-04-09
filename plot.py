import os
import re
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from bs4 import BeautifulSoup
from io import StringIO
from dotenv import load_dotenv

# Selenium modules and webdriver-manager.
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import chromedriver_binary  # ensures chromedriver is in PATH

# Load environment variables from .env file.
load_dotenv()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
if not ALPHA_VANTAGE_API_KEY:
    raise Exception("Please set your ALPHA_VANTAGE_API_KEY in the .env file.")

# ---------------------------
# AlphaVantage API Retrieval Functions
# ---------------------------
def fetch_alphavantage_btc(api_key, outputsize="full"):
    url = (
        "https://www.alphavantage.co/query?"
        "function=DIGITAL_CURRENCY_DAILY&"
        "symbol=BTC&market=USD&"
        f"outputsize={outputsize}&apikey={api_key}"
    )
    print("Fetching AlphaVantage BTC data...")
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Error retrieving BTC data. Status code: " + str(response.status_code))
    data_json = response.json()
    time_series = data_json.get("Time Series (Digital Currency Daily)")
    if not time_series:
        raise Exception("Time Series data for BTC not found in API response.")
    btc_df = pd.DataFrame.from_dict(time_series, orient="index")
    btc_df.index = pd.to_datetime(btc_df.index)
    btc_df.sort_index(inplace=True)
    close_key = "4. close"
    if close_key not in btc_df.columns:
        raise KeyError(f"Expected key {close_key} not found. Available keys: {btc_df.columns.tolist()}")
    btc_df["BTC_USD_Close"] = pd.to_numeric(btc_df[close_key])
    print("BTC data fetched successfully.")
    return btc_df

def fetch_alphavantage_mstr_daily(api_key, symbol="MSTR", outputsize="full"):
    url = (
        "https://www.alphavantage.co/query?"
        "function=TIME_SERIES_DAILY_ADJUSTED&"
        f"symbol={symbol}&outputsize={outputsize}&apikey={api_key}"
    )
    print(f"Fetching AlphaVantage {symbol} daily stock data...")
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error retrieving {symbol} daily data. Status code: " + str(response.status_code))
    data_json = response.json()
    time_series = data_json.get("Time Series (Daily)")
    if not time_series:
        raise Exception(f"Time Series data for {symbol} not found in API response.")
    stock_df = pd.DataFrame.from_dict(time_series, orient="index")
    stock_df.index = pd.to_datetime(stock_df.index)
    stock_df.sort_index(inplace=True)
    for col in stock_df.columns:
        stock_df[col] = pd.to_numeric(stock_df[col], errors="coerce")
    print(f"{symbol} daily data fetched successfully.")
    return stock_df

def fetch_alphavantage_overview(api_key, symbol="MSTR"):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}"
    print(f"Fetching AlphaVantage {symbol} overview data...")
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error retrieving {symbol} overview. Status code: " + str(response.status_code))
    data_json = response.json()
    if not data_json:
        raise Exception(f"No data returned for {symbol} overview.")
    overview_df = pd.DataFrame([data_json])
    print("Overview data fetched successfully.")
    return overview_df

# ---------------------------
# Selenium Scraper for Cumulative BTC Holdings from Strategy.com
# ---------------------------
def get_mstr_cumulative_btc_holdings():
    url = "https://www.strategy.com/purchases"
    print("Scraping cumulative MSTR BTC holdings from Strategy.com via Selenium...")
    
    options = Options()
    options.add_argument("window-size=1200x800")
    
    service = Service(ChromeDriverManager(driver_version="135.0.7049.84").install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        page_source = driver.page_source
        driver.quit()
        
        soup = BeautifulSoup(page_source, "html.parser")
        table = soup.find("table")
        if not table:
            raise Exception("Could not find the acquisitions table on Strategy.com")
        
        df = pd.read_html(StringIO(str(table)))[0]
        print("Acquisition table found. Columns:", df.columns.tolist())
        
        cumulative_col = None
        for col in df.columns:
            if "btc holdings" in str(col).lower():
                cumulative_col = col
                break
        
        if not cumulative_col:
            raise Exception("Could not find the 'BTC Holdings' column in the acquisition table.")
        
        print("Using column:", cumulative_col)
        df[cumulative_col] = df[cumulative_col].astype(str)
        df[cumulative_col] = df[cumulative_col].str.replace(',', '')
        df[cumulative_col] = df[cumulative_col].str.extract(r"([\d\.]+)")[0]
        df[cumulative_col] = pd.to_numeric(df[cumulative_col], errors='coerce')
        
        cumulative_holdings = df[cumulative_col].max()
        print("Cumulative BTC holdings computed from table:", cumulative_holdings)
        return int(cumulative_holdings)
        
    except Exception as e:
        driver.quit()
        raise Exception("Error in Selenium scraping for cumulative holdings: " + str(e))

# ---------------------------
# Selenium Scraper for Total Debt from Strategy.com
# ---------------------------
def get_mstr_total_debt_from_strategy():
    url = "https://www.strategy.com/debt"
    print("Scraping MSTR Total Debt from Strategy.com via Selenium...")
    
    options = Options()
    options.add_argument("window-size=1200x800")
    
    service = Service(ChromeDriverManager(driver_version="135.0.7049.84").install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        page_source = driver.page_source
        driver.quit()
        
        soup = BeautifulSoup(page_source, "html.parser")
        table = soup.find("table")
        if not table:
            raise Exception("Could not find the debt table on Strategy.com.")
        
        df = pd.read_html(StringIO(str(table)))[0]
        print("Debt table found. Columns:", df.columns.tolist())
        
        # We'll use the "Notional ($M)" column as our candidate for total debt.
        debt_col = None
        for col in df.columns:
            if "notional" in str(col).lower():
                debt_col = col
                break
        if not debt_col:
            raise Exception("Could not find a column for Notional debt in the table.")
        print("Using column:", debt_col)
        
        df[debt_col] = df[debt_col].astype(str).str.replace(',', '')
        df[debt_col] = df[debt_col].str.extract(r"([\d\.]+)")[0]
        df[debt_col] = pd.to_numeric(df[debt_col], errors='coerce')
        
        # Sum up all notional debt (in millions) and convert to USD.
        total_debt_millions = df[debt_col].sum()
        total_debt = total_debt_millions * 1e6
        print("Total Debt computed from table (in USD):", total_debt)
        return total_debt
    except Exception as e:
        driver.quit()
        raise Exception("Error in Selenium scraping for Total Debt: " + str(e))

# ---------------------------
# Selenium Scraper for Shares Outstanding from Strategy.com
# ---------------------------
def get_mstr_shares_outstanding_from_strategy():
    url = "https://www.strategy.com/shares"
    print("Scraping MSTR Shares Outstanding from Strategy.com via Selenium...")
    
    options = Options()
    options.add_argument("window-size=1200x800")
    
    service = Service(ChromeDriverManager(driver_version="135.0.7049.84").install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        page_source = driver.page_source
        driver.quit()
        
        soup = BeautifulSoup(page_source, "html.parser")
        table = soup.find("table")
        if not table:
            raise Exception("Could not find the shares table on Strategy.com.")
        
        df = pd.read_html(StringIO(str(table)))[0]
        print("Shares table found. Columns:", df.columns.tolist())
        
        shares_col = None
        for col in df.columns:
            if "shares outstanding" in str(col).lower() or "shares" in str(col).lower():
                shares_col = col
                break
        if not shares_col:
            raise Exception("Could not find a column for shares outstanding.")
        print("Using column:", shares_col)
        
        df[shares_col] = df[shares_col].astype(str).str.replace(',', '')
        df[shares_col] = df[shares_col].str.extract(r"([\d\.]+)")[0]
        df[shares_col] = pd.to_numeric(df[shares_col], errors="coerce")
        
        shares_outstanding = df[shares_col].max()
        print("Shares Outstanding computed from table:", shares_outstanding)
        return shares_outstanding
    except Exception as e:
        driver.quit()
        raise Exception("Error in Selenium scraping for Shares Outstanding: " + str(e))

# ---------------------------
# Utility Function to Save DataFrames to CSV
# ---------------------------
def save_df_to_csv(df, filepath, index=True):
    dirname = os.path.dirname(filepath)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    df.to_csv(filepath, index=index)
    print(f"Saved data to {filepath}")

# ---------------------------
# MAIN EXECUTION
# ---------------------------
def main():
    raw_data_dir = "alphavantage_data"
    os.makedirs(raw_data_dir, exist_ok=True)
    
    try:
        btc_df = fetch_alphavantage_btc(ALPHA_VANTAGE_API_KEY, outputsize="full")
        print("BTC data date range:", btc_df.index.min(), "to", btc_df.index.max())
    except Exception as e:
        print("Error fetching BTC data:", e)
        return
    
    try:
        mstr_daily_df = fetch_alphavantage_mstr_daily(ALPHA_VANTAGE_API_KEY, symbol="MSTR", outputsize="full")
    except Exception as e:
        print("Error fetching MSTR daily data:", e)
        return
    
    try:
        mstr_overview_df = fetch_alphavantage_overview(ALPHA_VANTAGE_API_KEY, symbol="MSTR")
    except Exception as e:
        print("Error fetching MSTR overview data:", e)
        return

    save_df_to_csv(btc_df, os.path.join(raw_data_dir, "btc_time_series.csv"))
    save_df_to_csv(mstr_daily_df, os.path.join(raw_data_dir, "mstr_daily.csv"))
    save_df_to_csv(mstr_overview_df, os.path.join(raw_data_dir, "mstr_overview.csv"), index=False)
    
    try:
        btc_holdings = get_mstr_cumulative_btc_holdings()
    except Exception as e:
        print("Error fetching cumulative BTC holdings from Strategy.com:", e)
        btc_holdings_input = input("Enter the current BTC holdings for MSTR (integer): ")
        try:
            btc_holdings = int(btc_holdings_input.replace(",", "").strip())
        except ValueError:
            print("Invalid input. Exiting.")
            return

    holdings_df = pd.DataFrame({"BTC_Holdings": [btc_holdings]})
    holdings_filepath = os.path.join(raw_data_dir, "mstr_btc_holdings.csv")
    save_df_to_csv(holdings_df, holdings_filepath, index=False)
    
    try:
        if "TotalDebt" in mstr_overview_df.columns and mstr_overview_df["TotalDebt"].iloc[0]:
            total_debt = float(mstr_overview_df["TotalDebt"].iloc[0])
        else:
            print("TotalDebt not found in overview data. Attempting to scrape from Strategy.com...")
            total_debt = get_mstr_total_debt_from_strategy()
    except Exception as e:
        print("Error fetching Total Debt from Strategy.com:", e)
        total_debt_input = input("Enter the Total Debt for MSTR (in USD): ")
        try:
            total_debt = float(total_debt_input.replace(",", "").strip())
        except ValueError:
            print("Invalid input. Exiting.")
            return
            
    try:
        if "SharesOutstanding" in mstr_overview_df.columns and mstr_overview_df["SharesOutstanding"].iloc[0]:
            shares_outstanding = float(mstr_overview_df["SharesOutstanding"].iloc[0])
        else:
            print("SharesOutstanding not found in overview data. Attempting to scrape from Strategy.com...")
            shares_outstanding = get_mstr_shares_outstanding_from_strategy()
    except Exception as e:
        print("Error fetching Shares Outstanding from Strategy.com:", e)
        shares_input = input("Enter the Shares Outstanding for MSTR: ")
        try:
            shares_outstanding = float(shares_input.replace(",", "").strip())
        except ValueError:
            print("Invalid input. Exiting.")
            return
    
    print("Key Fundamentals:")
    print(f"  BTC Holdings: {btc_holdings} BTC")
    print(f"  Total Debt: {total_debt:,.0f} USD")
    print(f"  Shares Outstanding: {shares_outstanding:,.0f}")
    
    mstr_daily_sorted = mstr_daily_df.sort_index().reset_index()
    btc_sorted = btc_df[["BTC_USD_Close"]].sort_index().reset_index()
    merged_df = pd.merge_asof(mstr_daily_sorted, btc_sorted, left_on="index", right_on="index", direction="backward")
    merged_df = merged_df.set_index("index")
    merged_df.index.name = "date"
    
    merged_df["NAV_total"] = btc_holdings * merged_df["BTC_USD_Close"] - total_debt
    merged_df["NAV_per_share"] = merged_df["NAV_total"] / shares_outstanding
    
    if "5. adjusted close" in merged_df.columns:
        merged_df["MSTR_market_price"] = merged_df["5. adjusted close"]
    elif "4. close" in merged_df.columns:
        merged_df["MSTR_market_price"] = merged_df["4. close"]
    else:
        raise Exception("Neither '5. adjusted close' nor '4. close' found in MSTR daily data.")
    
    merged_df["premium_multiple"] = merged_df["MSTR_market_price"] / merged_df["NAV_per_share"]
    
    analysis_filepath = os.path.join(raw_data_dir, "analysis_merged_data.csv")
    save_df_to_csv(merged_df, analysis_filepath)
    
    plt.figure(figsize=(12, 6))
    plt.plot(merged_df.index, merged_df["MSTR_market_price"], label="MSTR Market Price", color="blue")
    plt.plot(merged_df.index, merged_df["NAV_per_share"], label="NAV per Share", color="green")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.title("MSTR Market Price vs. NAV per Share")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    
    plt.figure(figsize=(12, 6))
    plt.plot(merged_df.index, merged_df["premium_multiple"], label="Premium Multiple", color="red")
    plt.xlabel("Date")
    plt.ylabel("Premium Multiple")
    plt.title("MSTR Premium Multiple Over Time")
    plt.axhline(y=1.0, color="black", linestyle="--", label="Parity (1x)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
