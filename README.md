# PIXIE: PIcture eXploration and Inference Engine
![logo](https://github.com/sidvenkatayogi/pixie/blob/20ed0e6b62ee6d6cd428d4e9826f708d476d604b/assets/logo.png) Pixie lets you view and explore your saved images by various indices. It's perfect for visual creatives looking for a novel, intuitive visual method to browse/search for inspiration and reference. [Demo]()
![screenshot](https://github.com/sidvenkatayogi/pixie/blob/20ed0e6b62ee6d6cd428d4e9826f708d476d604b/assets/screenshot.jpeg)
## Installation
### Released Version
Currently, Pixie is only supported on Windows. You can download the app from the [latest release]().

### For Development
To get the current development version:
1. Clone the repository:
   ```bash
   git clone https://github.com/sidvenkatayogi/pixie.git
   cd pixie
   ```
2. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   .venv/Scripts/activate
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
    ```bash
    python pixie.py
    ```

## Features
- View Images
- Search by:
    - Color
    - Visual Similarity (DINO)
    - Semantic/Content Similarity (CLIP)
- Import collections from Pinterest
- Open an image with default image viewer or in folder
- Get a image's color palette
- And more!

## Privacy
Your images are safe. The pictures you open in Pixie never leave your computer.