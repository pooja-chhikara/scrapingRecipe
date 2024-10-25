from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import time
from flask_cors import CORS

app = Flask(__name__)

# Enable CORS for all routes
# CORS(app)
CORS(app, resources={r"/scrape/*": {"origins": "http://localhost:3000"}})

app = Flask(__name__)

def search_and_scrape_recipe(query):
    # Initialize Selenium WebDriver
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Run in headless mode
    prefs = {"profile.default_content_setting_values.notifications": 2}
    options.add_experimental_option("prefs", prefs)

    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    recipe_data = {}

    # Step 1: Open AllRecipes homepage
    driver.get("https://www.allrecipes.com/")
    time.sleep(5)
    try:
        # Step 2: Locate the search bar and enter the query
        search_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "mntl-search-form--open__search-input"))
        )
        search_input.clear()
        search_input.send_keys(query)

        # Step 3: Find and click the search button
        search_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mntl-search-form__button'))
        )
        search_button.click()

        # Step 4: Wait for the search results page to load
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.mntl-search-results__list'))
        )

        # Step 5: Click on the first recipe link
        first_recipe_link = driver.find_element(By.CSS_SELECTOR, 'a.mntl-card-list-items')
        recipe_url = first_recipe_link.get_attribute('href')
        driver.get(recipe_url)

        # Step 6: Wait for the recipe page to load fully
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.ID, 'mntl-sc-block_6-0'))
        )

        # Step 7: Use BeautifulSoup to parse the recipe page HTML
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Step 8: Extract the recipe name
        h_tag = soup.find('h1', class_='article-heading type--lion')
        recipe_name = h_tag.get_text().strip()
        recipe_data["recipe_name"] = recipe_name

        # Step 9: Extract the ingredients
        ingredients_section = soup.find('ul', class_="mm-recipes-structured-ingredients__list")
        if ingredients_section:
            ingredients = [li.get_text(strip=True) for li in ingredients_section.find_all('li')]
            recipe_data["ingredients"] = ingredients
        else:
            recipe_data["ingredients"] = []

        # Step 10: Extract the instructions (directions)
        directions_section = soup.find('div', id='mm-recipes-steps__content_1-0')
        # print(directions_section)
        ol_tag = directions_section.find('ol')
        directions = [li.get_text(strip=True) for li in ol_tag.find_all('li')]
        recipe_data["directions"] = directions
        # if directions_section:
        #     # ol_tag = directions_section.find('ol')
        #     if ol_tag:
        #         directions = [li.get_text(strip=True) for li in ol_tag.find_all('li')]
        #         recipe_data["directions"] = directions
        #         print(directions)
        #     else:
        #         recipe_data["directions"] = []
        # else:
        #     recipe_data["directions"] = []

    except TimeoutException as e:
        recipe_data["error"] = "TimeoutException: {}".format(str(e))

    except Exception as e:
        recipe_data["error"] = "An error occurred: {}".format(str(e))
    finally:
        # Close the WebDriver
        driver.quit()

    return recipe_data


@app.route('/scrape', methods=['GET','OPTIONS'])
def scrape_recipe():
    if request.method == 'OPTIONS':
        # Handle the preflight OPTIONS request
        response = app.make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    result = search_and_scrape_recipe(query)
    print(result)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=3000)
