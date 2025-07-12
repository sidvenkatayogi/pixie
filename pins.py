import json
import os
import re
from pinterest_dl import PinterestDL

def download_board(url):
    pattern = r'(https?://)?(www\.)?pinterest\.com/([^/]+)/([^/]+)/?$'
    
    match = re.match(pattern, url)
    if not match:
        print("Invalid Pinterest URL. Must be in format: pinterest.com/username/boardname")
        return
    
    if not match.group(2):
        url = "www." + url
    if not match.group(1):
        url = "https://" + url

    username = match.group(3)
    board_name = match.group(4)
    
    

    try:
        # 1. Initialize PinterestDL with API.
        scraped_images = PinterestDL.with_api().scrape(
            url=url,  # URL of the Pinterest page
            num=100_000,  # Maximum number of images to scrape
            delay= 0.2
            # min_resolution=(512, 512),  # <- Only available to set in the API. Browser mode will have to pruned after download.
        )

        # 2. Save Scraped Data to JSON
        # Convert scraped data into a dictionary and save it to a JSON file for future access
        # images_data = [img.to_dict() for img in scraped_images]
        # with open("art.json", "w") as f:
        #     json.dump(images_data, f, indent=4)
        #TODO use alt text instead of embedding every image with clip

        # 3. Download Images
        # Download images to a specified directory
        output_dir = os.path.join("pinterest", username, board_name)
        #TODO if there is an existing directory make sure to delete it first
        downloaded_imgs = PinterestDL.download_images(images=scraped_images, output_dir=output_dir)

        return output_dir
    except Exception as e:
        print(e)

if __name__ == "__main__":
    download_board("pinterest.com/sidvenkatayogii/backgrounds/")