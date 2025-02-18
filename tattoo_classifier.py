import os
from pathlib import Path
import base64
import csv
import google.generativeai as genai
from PIL import Image
import io
import time
from datetime import datetime
import pandas as pd

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

def analyze_tattoo(model, image_path):
    """Analyze a single tattoo image using Gemini"""
    prompt = """
    Analyze this tattoo image and provide:
    1. Primary tattoo style (most likely style)
    2. Secondary tattoo style (another possible style)
    3. Detailed description of the tattoo's content and special features
    
    Format your response exactly like this, with each item on a new line:
    Primary: [style]
    Secondary: [style]
    Description: [detailed description]
    """
    
    try:
        image = encode_image(image_path)
        if image is None:
            return "Error", "Error", "Failed to load image"
            
        response = model.generate_content([prompt, image])
        response.resolve()
        
        # Parse response
        lines = response.text.strip().split('\n')
        primary = lines[0].replace('Primary: ', '').strip()
        secondary = lines[1].replace('Secondary: ', '').strip()
        description = lines[2].replace('Description: ', '').strip()
        
        return primary, secondary, description
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return "Error", "Error", f"Failed to process: {str(e)}"

def get_processed_images(csv_path):
    """Get list of already processed image paths from CSV"""
    if not os.path.exists(csv_path):
        return set()
    
    try:
        df = pd.read_csv(csv_path)
        return set(df['Image Path'].values)
    except Exception as e:
        print(f"Error reading existing CSV: {str(e)}")
        return set()

def process_folder(folder_path, output_csv):
    """Process all images in a folder and save results to CSV"""
    try:
        print("Setting up Gemini API...")
        model = setup_gemini()
        print("Gemini API setup successful")
        
        # Get already processed images
        processed_images = get_processed_images(output_csv)
        print(f"Found {len(processed_images)} previously processed images")
        
        # Supported image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        
        # Create or append to CSV
        mode = 'a' if os.path.exists(output_csv) else 'w'
        with open(output_csv, mode, newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if mode == 'w':
                writer.writerow(['Image Path', 'Primary Style', 'Secondary Style', 'Description', 'Processed Date'])
            
            # Process each image
            folder = Path(folder_path)
            total_processed = 0
            requests_this_minute = 0
            minute_start = time.time()
            
            for image_path in folder.glob('**/*'):
                if image_path.suffix.lower() in image_extensions:
                    # Skip if already processed
                    if str(image_path) in processed_images:
                        print(f"Skipping already processed image: {image_path}")
                        continue
                    
                    # Rate limiting
                    current_time = time.time()
                    if current_time - minute_start >= 60:
                        requests_this_minute = 0
                        minute_start = current_time
                    
                    if requests_this_minute >= 14:  # Leave buffer for safety
                        wait_time = 60 - (current_time - minute_start)
                        print(f"\nRate limit approaching. Waiting {wait_time:.1f} seconds...")
                        time.sleep(wait_time)
                        requests_this_minute = 0
                        minute_start = time.time()
                    
                    print(f"\nProcessing ({total_processed + 1}): {image_path}")
                    try:
                        primary, secondary, description = analyze_tattoo(model, image_path)
                        processed_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        writer.writerow([str(image_path), primary, secondary, description, processed_date])
                        print(f"Results for {image_path}:")
                        print(f"- Primary Style: {primary}")
                        print(f"- Secondary Style: {secondary}")
                        print(f"- Description: {description}")
                        total_processed += 1
                        requests_this_minute += 1
                        
                        # Small delay between requests
                        time.sleep(1)
                    except Exception as e:
                        print(f"Error processing {image_path}: {str(e)}")
                        continue
            
            print(f"\nProcessing complete. Total new images processed: {total_processed}")
    except Exception as e:
        print(f"An error occurred during processing: {str(e)}")

if __name__ == "__main__":
    # Get current directory
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Use current directory as folder path
    folder_path = current_dir
    # code for a specific path
    # folder_path = r"C:\Users\james\Downloads\rich photos"
    output_csv = "tattoo_analysis.csv"
    
    print(f"Looking for images in: {folder_path}")
    
    # Count image files before processing
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    image_files = [f for f in os.listdir(folder_path) 
                  if os.path.isfile(os.path.join(folder_path, f)) 
                  and os.path.splitext(f)[1].lower() in image_extensions]
    
    print(f"Found {len(image_files)} image files:")
    for file in image_files:
        print(f"- {file}")
    
    # Process the folder
    print("\nStarting image processing...")
    process_folder(folder_path, output_csv)