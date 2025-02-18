# Tattoo Style Classifier

A Python application that uses Google's Gemini AI to analyze tattoo images and classify their styles, providing detailed descriptions and multiple style interpretations.

## Features

- Analyzes tattoo images using Gemini AI
- Classifies primary and secondary tattoo styles
- Provides detailed descriptions of tattoo content
- Handles rate limiting for API requests
- Supports batch processing with resume capability
- Exports results to CSV format

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tattoo-classifier
cd tattoo-classifier
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Setting Up Environment Variables

### Windows

Temporary (current session only):
```powershell
$env:GOOGLE_API_KEY = "your-api-key-here"
```

Permanent (requires terminal restart):
```powershell
[System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'your-api-key-here', 'User')
```

### Linux/Mac

Temporary (current session only):
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

Permanent:
Add to ~/.bashrc or ~/.zshrc:
```bash
echo 'export GOOGLE_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

## Usage

1. Place your tattoo images in a directory
2. Update the `folder_path` in the script or use the current directory:
   ```python
   # Use specific path
   folder_path = r"C:\path\to\your\images"
   
   # Or use current directory
   folder_path = os.getcwd()
   ```
3. Run the script:
```bash
python tattoo_classifier.py
```

The script will:
- Process all images in the specified directory
- Skip previously processed images
- Create/append to tattoo_analysis.csv with results
- Respect API rate limits automatically

## Output Format

The script generates a CSV file with the following columns:
- Image Path: Full path to the processed image
- Primary Style: Main tattoo style identified
- Secondary Style: Alternative style interpretation
- Description: Detailed description of the tattoo
- Processed Date: Timestamp of when the image was analyzed

## Rate Limits

The free tier of Gemini API has the following limits:
- 15 requests per minute (RPM)
- 1 million tokens per minute (TPM)
- 1,500 requests per day (RPD)

The script automatically handles these limits by:
- Tracking requests per minute
- Implementing waiting periods when needed
- Adding safety buffers to prevent limit violations

## Error Handling

The script includes robust error handling for:
- Invalid image files
- API rate limiting
- Network issues
- Malformed responses
- File system errors

Failed processes are logged and can be retried in subsequent runs.

## Roadmap

### Version 1.1 (Next Release)
- Add support for custom prompt templates
- Implement concurrent processing for faster execution
- Add progress bar visualization
- Add error retry mechanism

### Version 1.2
- Add web interface for easier usage
- Implement result filtering and sorting
- Add support for bulk export formats
- Add image preprocessing options

### Version 2.0
- Add support for multiple AI providers
- Implement style confidence scores
- Add automated style categorization
- Add batch processing optimization

## Common Issues

1. **Rate Limiting**: If you receive rate limit errors, the script will automatically pause. No action needed.

2. **Environment Variable Not Found**: Make sure to restart your terminal after setting a permanent environment variable.

3. **Image Format Errors**: Ensure your images are in supported formats (jpg, jpeg, png, gif, webp).

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgments

- Google Gemini API for image analysis
- Python Pillow library for image processing
- Pandas for data handling

## Support

For issues and feature requests, please use the GitHub issue tracker.