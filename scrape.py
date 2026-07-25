import os
import time
import requests
import concurrent.futures
import random
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import urlparse
from webdriver_manager.chrome import ChromeDriverManager

# Global list to store all metadata
metadata_list = []

def download_image(args):
    """Download an image from URL to the specified folder"""
    url, folder_path, filename = args
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
    
    attempt = 0
    while True:
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return f"Downloaded: {filename}"
            elif response.status_code == 429:
                wait_time = random.uniform(10, 30) + (attempt * random.uniform(5, 15))
                print(f"Rate limited, waiting {wait_time:.1f}s for {filename}")
                time.sleep(wait_time)
                attempt += 1
                continue
            else:
                wait_time = random.uniform(2, 8)
                time.sleep(wait_time)
                attempt += 1
                if attempt > 10:
                    return f"Failed to download: {url} (Status code: {response.status_code})"
                continue
        except Exception as e:
            wait_time = random.uniform(3, 10)
            time.sleep(wait_time)
            attempt += 1
            if attempt > 10:
                return f"Error downloading {url}: {str(e)}"

def extract_photo_metadata(driver, photo_url):
    """Extract metadata from individual photo page"""
    metadata = {
        'title': 'Unknown',
        'author': 'Unknown',
        'upload_date': 'Unknown',
        'tags': '',
        'description': '',
        'url': photo_url,
        'photo_id': 'Unknown'
    }
    
    try:
        # Open the photo page in a new tab
        original_window = driver.current_window_handle
        driver.execute_script("window.open(arguments[0]);", photo_url)
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)
        
        try:
            # Extract title
            title_elem = driver.find_element(By.CSS_SELECTOR, "h1.title, span.photo-title, div.photo-title")
            metadata['title'] = title_elem.text.strip()
        except:
            pass
        
        try:
            # Extract author
            author_elem = driver.find_element(By.CSS_SELECTOR, "a.owner-name, span.owner-name, div.owner")
            metadata['author'] = author_elem.text.strip()
        except:
            pass
        
        try:
            # Extract upload date
            date_elem = driver.find_element(By.CSS_SELECTOR, "span.photo-date, time, abbr.published")
            metadata['upload_date'] = date_elem.text.strip()
        except:
            pass
        
        try:
            # Extract description
            desc_elem = driver.find_element(By.CSS_SELECTOR, "div.description, p.description, div.photo-description")
            metadata['description'] = desc_elem.text.strip()[:500]
        except:
            pass
        
        try:
            # Extract tags
            tags = []
            tag_elems = driver.find_elements(By.CSS_SELECTOR, "a.tag, span.tag")
            for tag in tag_elems[:10]:
                tags.append(tag.text.strip())
            metadata['tags'] = ', '.join(tags)
        except:
            pass
        
        try:
            # Extract photo ID from URL
            if 'photos' in photo_url:
                parts = photo_url.split('/')
                for i, part in enumerate(parts):
                    if part.isdigit() and len(part) > 5:
                        metadata['photo_id'] = part
                        break
        except:
            pass
        
        # Close the photo tab and return to original
        driver.close()
        driver.switch_to.window(original_window)
        
    except Exception as e:
        print(f"Error extracting metadata: {str(e)}")
        try:
            driver.close()
            driver.switch_to.window(original_window)
        except:
            pass
    
    return metadata

def export_metadata_to_csv(metadata_list, output_folder):
    """Export metadata to CSV file"""
    csv_path = os.path.join(output_folder, 'flickr_metadata.csv')
    
    if not metadata_list:
        print("No metadata to export")
        return
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['Image #', 'Filename', 'Title', 'Author', 'Upload Date', 'Description', 'Tags', 'Photo URL', 'Photo ID']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, data in enumerate(metadata_list, 1):
                writer.writerow({
                    'Image #': i,
                    'Filename': data.get('filename', ''),
                    'Title': data.get('title', ''),
                    'Author': data.get('author', ''),
                    'Upload Date': data.get('upload_date', ''),
                    'Description': data.get('description', ''),
                    'Tags': data.get('tags', ''),
                    'Photo URL': data.get('url', ''),
                    'Photo ID': data.get('photo_id', '')
                })
        
        print(f"✓ Metadata exported to {csv_path}")
    except Exception as e:
        print(f"Error exporting CSV: {str(e)}")

def export_metadata_to_markdown(metadata_list, output_folder):
    """Export metadata to Markdown file"""
    md_path = os.path.join(output_folder, 'flickr_metadata.md')
    
    if not metadata_list:
        print("No metadata to export")
        return
    
    try:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Flickr Album Metadata\n\n")
            f.write(f"**Total Images:** {len(metadata_list)}\n")
            f.write(f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            for i, data in enumerate(metadata_list, 1):
                f.write(f"## Image {i}\n\n")
                f.write(f"**Filename:** {data.get('filename', 'Unknown')}\n\n")
                f.write(f"**Title:** {data.get('title', 'Unknown')}\n\n")
                f.write(f"**Author:** {data.get('author', 'Unknown')}\n\n")
                f.write(f"**Upload Date:** {data.get('upload_date', 'Unknown')}\n\n")
                f.write(f"**Photo ID:** {data.get('photo_id', 'Unknown')}\n\n")
                
                if data.get('description'):
                    f.write(f"**Description:** {data.get('description')}\n\n")
                
                if data.get('tags'):
                    f.write(f"**Tags:** {data.get('tags')}\n\n")
                
                f.write(f"**URL:** [{data.get('url', 'Link')}]({data.get('url', '')})\n\n")
                f.write("---\n\n")
        
        print(f"✓ Metadata exported to {md_path}")
    except Exception as e:
        print(f"Error exporting Markdown: {str(e)}")

def scrape_flickr_album(album_url, output_folder="downloaded_images", max_workers=10):
    """Scrape all images from a Flickr album"""
    global metadata_list
    metadata_list = []
    
    # Setup Chrome options for Chromium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    
    # Initialize the Chrome driver
    try:
        print("Initializing ChromeDriver...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
    except Exception as e:
        print(f"Error initializing Chrome: {str(e)}")
        print("Trying alternative setup...")
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e2:
            print(f"Failed to initialize Chrome: {str(e2)}")
            return
    
    try:
        # Navigate to the album URL
        print(f"\nNavigating to {album_url}")
        driver.get(album_url)
        
        # Wait for the page to load
        time.sleep(5)
        
        image_count = 0
        page_num = 1
        has_next_page = True
        
        # Create a thread pool executor
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while has_next_page:
                print(f"\n--- Processing page {page_num} ---")
                
                # Scroll down to load all images on current page
                last_height = driver.execute_script("return document.body.scrollHeight")
                scroll_count = 0
                while True:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                    scroll_count += 1
                    if scroll_count % 3 == 0:
                        print(f"  Scrolling to load more images... (scroll #{scroll_count})")
                
                # Find all image elements on current page
                images = driver.find_elements(By.CSS_SELECTOR, "div.photo img")
                print(f"  Found {len(images)} images on page {page_num}")
                
                # Prepare download tasks and metadata extraction
                download_tasks = []
                photo_links = []
                
                for i, img in enumerate(images):
                    img_url = img.get_attribute("src")
                    
                    # Convert thumbnail URL to larger version if needed
                    img_url = img_url.replace("_c.jpg", "_b.jpg").replace("_z.jpg", "_b.jpg")
                    
                    filename = f"flickr_image_{image_count + i + 1}.jpg"
                    download_tasks.append((img_url, output_folder, filename))
                    
                    # Try to get photo link
                    try:
                        photo_link_elem = img.find_element(By.XPATH, "./ancestor::a")
                        photo_link = photo_link_elem.get_attribute("href")
                        if photo_link:
                            photo_links.append({
                                'url': photo_link,
                                'filename': filename,
                                'index': image_count + i + 1
                            })
                    except:
                        pass
                
                # Submit all download tasks
                print(f"  Starting downloads with {max_workers} threads...")
                futures = [executor.submit(download_image, task) for task in download_tasks]
                download_count = 0
                for future in concurrent.futures.as_completed(futures):
                    download_count += 1
                    if download_count % 10 == 0:
                        print(f"    {download_count}/{len(futures)} downloads completed")
                
                print(f"  All {len(download_tasks)} images downloaded")
                
                # Extract metadata for each photo
                print(f"  Extracting metadata for {len(photo_links)} photos...")
                for idx, photo_info in enumerate(photo_links, 1):
                    print(f"    [{idx}/{len(photo_links)}] Extracting metadata...")
                    metadata = extract_photo_metadata(driver, photo_info['url'])
                    metadata['filename'] = photo_info['filename']
                    metadata_list.append(metadata)
                    time.sleep(1)
                
                image_count += len(images)
                
                # Try to find and click the "Next" button
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "i.page-arrow.right")
                    if next_button and next_button.is_displayed():
                        print(f"  Clicking 'Next' button to page {page_num + 1}...")
                        next_button.click()
                        time.sleep(5)
                        page_num += 1
                    else:
                        print("  ✓ Reached the last page")
                        has_next_page = False
                except NoSuchElementException:
                    print("  ✓ Reached the last page (no next button found)")
                    has_next_page = False
        
        # Export metadata after all downloads complete
        print("\n--- Exporting Metadata ---")
        export_metadata_to_csv(metadata_list, output_folder)
        export_metadata_to_markdown(metadata_list, output_folder)
        
        print(f"\n{'='*50}")
        print(f"✓ COMPLETE!")
        print(f"{'='*50}")
        print(f"Total images downloaded: {image_count}")
        print(f"Location: {os.path.abspath(output_folder)}")
        print(f"Files created:")
        print(f"  - {image_count} image files")
        print(f"  - flickr_metadata.csv")
        print(f"  - flickr_metadata.md")
        print(f"{'='*50}\n")
            
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("FLICKR ALBUM SCRAPER")
    print("="*50)
    
    album_url = input("\nEnter the Flickr album URL: ").strip()
    output_folder = input("Enter output folder name (default: downloaded_images): ").strip() or "downloaded_images"
    max_workers_input = input("Enter maximum number of download threads (default: 15): ").strip()
    max_workers = int(max_workers_input) if max_workers_input.isdigit() else 15
    
    print(f"\nSettings:")
    print(f"  URL: {album_url}")
    print(f"  Output folder: {output_folder}")
    print(f"  Download threads: {max_workers}")
    print(f"\nStarting scraper...\n")
    
    scrape_flickr_album(album_url, output_folder, max_workers)