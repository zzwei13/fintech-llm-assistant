from supabase import create_client, Client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import csv
import os
import time
import random
from dotenv import load_dotenv
from fake_useragent import UserAgent

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Set the date range
start_date = datetime.strptime("2024-10-25", "%Y-%m-%d")
end_date = datetime.strptime("2024-11-08", "%Y-%m-%d")

# CSV file setup
csv_file = "china_news.csv"
file_exists = os.path.isfile(csv_file)

# Set up fake user agent
ua = UserAgent()

# Open CSV file for appending data
with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    
    # Write header if file does not already exist
    if not file_exists:
        writer.writerow(["StockID", "Date", "Content", "Link"])

    # Get stock data from Supabase
    stocks = (
        supabase
        .table("stock")
        .select("stockID, stock_name")
        .gte("stockID", 1101)
        .lte("stockID", 1200)
        .execute()
        .data
    )

    # Set up Selenium WebDriver with random User-Agent
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-agent={ua.random}")  # Set random User-Agent
    driver = webdriver.Chrome(options=options)

    # Iterate over each stock to fetch related news
    for stock in stocks:
        stock_id = stock["stockID"]
        stock_name = stock["stock_name"]
        global_url = f"https://www.chinatimes.com/search/{stock_name}?page="

        # Iterate over the first 3 pages for each stock
        for i in range(3):
            url = global_url + str(i + 1) + "&chdtv"
            driver.get(url)

            # Random delay to mimic human behavior
            time.sleep(random.uniform(3, 6))

            # Wait for the article list to load
            try:
                article_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "article-list"))
                )
            except:
                print(f"Error: Article list not found for stock {stock_name}.")
                continue

            # Find all article elements within the list
            articles = article_list.find_elements(By.TAG_NAME, "li")

            # Process each article
            for article in articles:
                try:
                    # Extract time and intro content
                    time_element = article.find_element(By.TAG_NAME, "time")
                    intro_element = article.find_element(By.CLASS_NAME, "intro")

                    time_text = time_element.get_attribute("datetime")
                    intro_text = intro_element.text
                    link = article.find_element(By.TAG_NAME, "a").get_attribute("href")
                    time_datetime = datetime.strptime(time_text, "%Y-%m-%d %H:%M")

                    # Skip articles outside of the specified date range
                    if not (start_date <= time_datetime <= end_date):
                        continue

                    # Format date for Supabase
                    supabase_date_format = time_datetime.strftime("%Y-%m-%d")

                    # Print detailed article information
                    print(f"\nStock Name: {stock_name}")
                    print(f"Date: {supabase_date_format}")
                    print(f"Content: {intro_text}")
                    print(f"Link: {link}")

                    # Insert data into Supabase
                    data = {
                        "stockID": stock_id,
                        "date": supabase_date_format,
                        "content": intro_text,
                        "gemini_signal": None,
                        "emotion": None,
                    }

                    response = supabase.table("news_content").insert(data).execute()

                    # Log success or failure of database insertion
                    if response.status_code == 201:
                        print(f"Data inserted successfully for {stock_name} on {supabase_date_format}")
                    else:
                        print(f"Failed to insert data for {stock_name}: {response}")

                    # Write data to CSV
                    writer.writerow([stock_id, stock_name, supabase_date_format, intro_text, link])

                except Exception as e:
                    print(f"Error processing article for {stock_name}: {e}")

            # Change User-Agent randomly for each page
            options.add_argument(f"user-agent={ua.random}")
            driver = webdriver.Chrome(options=options)

    # Close the driver after processing all stocks
    driver.quit()
