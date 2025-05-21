from supabase import create_client, Client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import os

# Supabase setup
url = "https://ifdyheuivlbmhsbpuyqf.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlmZHloZXVpdmxibWhzYnB1eXFmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyMTMxMTU2OSwiZXhwIjoyMDM2ODg3NTY5fQ.c6DehH3cUJrjHa22_ps0w32xCLRhS5AAQUqc1sHqoI0"
# 初始化 Supabase 客戶端
supabase: Client = create_client(url, key)

stock_id = "2317"
global_url = "https://www.chinatimes.com/search/鴻海?page="
page = 1


for i in range(3):
    # Request page content
    url = global_url + str(i + 1) + "&chdtv"
    driver = webdriver.Chrome()
    driver.get(url)

    # Wait for the elements to be loaded dynamically
    try:
        article_list = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "article-list"))
        )
    except:
        print("Error: Article list not found.")
        driver.quit()
        exit()

    # Find all article elements within the list
    articles = article_list.find_elements(By.TAG_NAME, "li")

    for article in articles:
        try:
            # Extract time and intro content
            time_element = article.find_element(By.TAG_NAME, "time")
            intro_element = article.find_element(By.CLASS_NAME, "intro")

            time_text = time_element.get_attribute("datetime")
            intro_text = intro_element.text
            time_datetime = datetime.strptime(time_text, "%Y-%m-%d %H:%M")
            formatted_date = time_datetime.strftime("%Y%m%d")
            supabase_date_format = time_datetime.strftime("%Y-%m-%d")

            # Print the extracted data
            print("Date:", supabase_date_format)

            # Insert data into Supabase
            # Insert data into Supabase
            data = {
                "stockID": int(stock_id),
                "date": supabase_date_format,
                "content": intro_text,
                "gemini_signal": None,  # Assuming this is to be filled later
                "emotion": None,  # Assuming this is to be filled later
            }

            response = supabase.table("news_content").insert(data).execute()

            if response.status_code == 201:
                print(f"Data inserted successfully for date: {supabase_date_format}")
            else:
                print(f"Failed to insert data: {response}")

        except Exception as e:
            print("Error:", e)

    # Close the browser
    driver.quit()
