import os
from pathlib import Path
import google.generativeai as genai
from PIL import Image
import time
from datetime import datetime
import pandas as pd
import csv
import random
import hashlib

def setup_gemini():
    """Setup Gemini API with credentials"""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY environment variable")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

def encode_image(image_path):
    """Convert image to PIL Image for Gemini API"""
    try:
        with Image.open(image_path) as img:
            # Resize if image is too large (Gemini has size limits)
            if max(img.size) > 2048:
                ratio = 2048 / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            return img
    except Exception as e:
        print(f"Error processing image {image_path}: {str(e)}")
        return None

def analyze_photo(model, image_path):
    """Analyze a single photo using Gemini"""
    prompt = """
    Analyze this personal photo and provide:
    1. Event/Category (e.g., Wedding, Birthday, Screenshot, Family Gathering, Travel, etc.)
    2. If Wedding: Whose wedding? (e.g., "Your wedding", "Friend's wedding", "Unknown wedding")
    3. People present (e.g., You, Family members, Friends, Colleagues, etc.)
    4. Location type (e.g., Indoors, Outdoors, Beach, Restaurant, etc.)
    5. Brief description of the content
    
    Format your response exactly like this, with each item on a new line:
    Category: [category]
    Wedding: [whose wedding or "N/A"]
    People: [people present]
    Location: [location type]
    Description: [brief description]
    """
    
    try:
        image = encode_image(image_path)
        if image is None:
            return "Error", "N/A", "Unknown", "Unknown", "Failed to load image"
            
        response = model.generate_content([prompt, image])
        response.resolve()
        
        # Parse response
        lines = response.text.strip().split('\n')
        category = lines[0].replace('Category: ', '').strip()
        wedding = lines[1].replace('Wedding: ', '').strip()
        people = lines[2].replace('People: ', '').strip()
        location = lines[3].replace('Location: ', '').strip()
        description = lines[4].replace('Description: ', '').strip()
        
        return category, wedding, people, location, description
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return "Error", "N/A", "Unknown", "Unknown", f"Failed to process: {str(e)}"

def get_image_hash(image_path):
    """Create a hash of the image to identify it uniquely"""
    try:
        with open(image_path, 'rb') as f:
            # Use the first 8KB of the file for hashing
            # This is faster than hashing the entire file and sufficient for uniqueness
            return hashlib.md5(f.read(8192)).hexdigest()
    except Exception as e:
        print(f"Error hashing {image_path}: {str(e)}")
        # Use path as fallback (less reliable)
        return str(image_path)

def get_processed_images(csv_path):
    """Get dictionary of already processed image hashes and paths from CSV"""
    if not os.path.exists(csv_path):
        return {}, set()
    
    try:
        df = pd.read_csv(csv_path)
        # Create a dictionary mapping hashes to full rows for quick lookup
        hash_dict = {row['Image Hash']: True for _, row in df.iterrows()}
        path_set = set(df['Image Path'].values)
        return hash_dict, path_set
    except Exception as e:
        print(f"Error reading existing CSV: {str(e)}")
        return {}, set()

def process_folder(folder_path, output_csv, daily_limit=1000, sample_size=None):
    """Process images in a folder and save results to CSV with rate limiting
    
    Args:
        folder_path: Path to folder containing images
        output_csv: Path to output CSV file
        daily_limit: Maximum number of API calls per day (default 1000 for safety margin)
        sample_size: If not None, process only this many random images
    """
    try:
        print("Setting up Gemini API...")
        model = setup_gemini()
        print("Gemini API setup successful")
        
        # Get already processed images
        processed_hashes, processed_paths = get_processed_images(output_csv)
        print(f"Found {len(processed_hashes)} previously processed images")
        
        # Supported image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        
        # Create or append to CSV
        mode = 'a' if os.path.exists(output_csv) else 'w'
        with open(output_csv, mode, newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if mode == 'w':
                writer.writerow(['Image Path', 'Image Hash', 'Category', 'Wedding', 'People', 'Location', 'Description', 'Processed Date'])
            
            # Collect all valid image paths
            folder = Path(folder_path)
            all_images = []
            print("Scanning for images...")
            for image_path in folder.glob('**/*'):
                if image_path.suffix.lower() in image_extensions:
                    # Skip if already processed by path
                    if str(image_path) in processed_paths:
                        continue
                    all_images.append(image_path)
            
            print(f"Found {len(all_images)} images that haven't been processed yet")
            
            # If sample_size is specified, take a random sample
            if sample_size is not None and sample_size < len(all_images):
                print(f"Taking random sample of {sample_size} images")
                all_images = random.sample(all_images, sample_size)
            
            # Process rate limits
            total_processed = 0
            requests_this_minute = 0
            daily_requests = 0
            minute_start = time.time()
            day_start = time.time()
            
            for image_path in all_images:
                # Check if daily limit is reached
                if daily_requests >= daily_limit:
                    print(f"\nDaily limit of {daily_limit} requests reached. Stopping processing.")
                    break
                
                # Get image hash first to check if already processed
                image_hash = get_image_hash(image_path)
                if image_hash in processed_hashes:
                    print(f"Skipping already processed image (by hash): {image_path}")
                    continue
                
                # Rate limiting per minute
                current_time = time.time()
                if current_time - minute_start >= 60:
                    requests_this_minute = 0
                    minute_start = current_time
                
                if requests_this_minute >= 14:  # Leave buffer for safety (limit is 15 RPM)
                    wait_time = 60 - (current_time - minute_start)
                    print(f"\nRate limit approaching. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    requests_this_minute = 0
                    minute_start = time.time()
                
                print(f"\nProcessing ({total_processed + 1}/{len(all_images)}): {image_path}")
                try:
                    category, wedding, people, location, description = analyze_photo(model, image_path)
                    processed_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow([str(image_path), image_hash, category, wedding, people, location, description, processed_date])
                    
                    print(f"Results for {image_path}:")
                    print(f"- Category: {category}")
                    print(f"- Wedding: {wedding}")
                    print(f"- People: {people}")
                    print(f"- Location: {location}")
                    print(f"- Description: {description}")
                    
                    total_processed += 1
                    requests_this_minute += 1
                    daily_requests += 1
                    
                    # Small delay between requests
                    time.sleep(1)
                    
                    # Save progress more frequently (every 10 images)
                    if total_processed % 10 == 0:
                        f.flush()
                        
                except Exception as e:
                    print(f"Error processing {image_path}: {str(e)}")
                    continue
            
            print(f"\nProcessing complete. Total new images processed: {total_processed}")
    except Exception as e:
        print(f"An error occurred during processing: {str(e)}")

def analyze_results(csv_path):
    """Analyze the results and provide summary statistics"""
    if not os.path.exists(csv_path):
        print("No results file found.")
        return
    
    try:
        df = pd.read_csv(csv_path)
        
        # Basic statistics
        total_images = len(df)
        categories = df['Category'].value_counts()
        weddings = df['Wedding'].value_counts()
        
        print("\n=== ANALYSIS SUMMARY ===")
        print(f"Total images processed: {total_images}")
        
        print("\nTop Categories:")
        for category, count in categories.head(10).items():
            print(f"- {category}: {count} ({count/total_images*100:.1f}%)")
        
        print("\nWedding Distribution:")
        for wedding, count in weddings.head(10).items():
            print(f"- {wedding}: {count}")
        
        # Export category distribution to CSV
        analysis_file = csv_path.replace('.csv', '_analysis.csv')
        categories_df = pd.DataFrame({
            'Category': categories.index,
            'Count': categories.values,
            'Percentage': (categories.values / total_images * 100).round(1)
        })
        categories_df.to_csv(analysis_file, index=False)
        print(f"\nDetailed analysis saved to {analysis_file}")
        
    except Exception as e:
        print(f"Error analyzing results: {str(e)}")

if __name__ == "__main__":
    # Get current directory
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Use current directory as folder path
    # folder_path = current_dir
    # Uncomment and modify for a specific path:
    folder_path = r"C:\Users\james\OneDrive\Desktop\images_to_review"
    
    output_csv = "photo_analysis.csv"
    
    print(f"Looking for images in: {folder_path}")
    
    # Count image files before processing
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    image_files = [f for f in os.listdir(folder_path) 
                  if os.path.isfile(os.path.join(folder_path, f)) 
                  and os.path.splitext(f)[1].lower() in image_extensions]
    
    print(f"Found {len(image_files)} image files in root directory (not including subdirectories)")
    
    # Configure processing
    process_all = input("Do you want to process all images or a sample? (all/sample): ").lower()
    
    if process_all == 'sample':
        try:
            sample_size = int(input("How many random images to analyze? "))
        except ValueError:
            print("Invalid input. Using default sample size of 100.")
            sample_size = 100
    else:
        sample_size = None
    
    daily_limit = 1000  # Default for free tier (1500 with safety margin)
    
    # Ask for custom daily limit
    try:
        custom_limit = input("Enter daily API call limit (default 1000 for free tier): ")
        if custom_limit.strip():
            daily_limit = int(custom_limit)
    except ValueError:
        print("Invalid input. Using default daily limit of 1000.")
    
    # Process the folder
    print("\nStarting image processing...")
    process_folder(folder_path, output_csv, daily_limit=daily_limit, sample_size=sample_size)
    
    # Analyze the results
    print("\nAnalyzing results...")
    analyze_results(output_csv)