# HumanEval PWA Setup

This Progressive Web App (PWA) provides a web interface for the HumanEval code evaluation system.

## Features

- 📱 **Progressive Web App** - Installable on mobile and desktop
- 🔍 **Browse Problems** - View all HumanEval problems with search
- 📊 **View Results** - Browse and inspect evaluation results
- ⚡ **Run Evaluations** - Execute evaluations through the web interface
- 🌐 **Offline Support** - Works offline with service worker caching

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate PWA icons (optional):**
   ```bash
   pip install Pillow
   python generate_icons.py
   ```
   
   Or manually add `icon-192.png` and `icon-512.png` to the `static/` directory.

3. **Set up environment variables:**
   Create a `.env` file with:
   ```
   OPENAI_API_KEY=your_api_key_here
   PWD=/workspace
   ```

4. **Run the Flask server:**
   ```bash
   python app.py
   ```

5. **Access the PWA:**
   Open your browser to `http://localhost:5000`

## PWA Installation

- **Chrome/Edge**: Click the install button in the address bar or use the "Install App" button
- **Safari (iOS)**: Use "Add to Home Screen" from the share menu
- **Firefox**: Use "Install" from the menu

## API Endpoints

- `GET /api/problems` - Get all HumanEval problems
- `GET /api/problems/<task_id>` - Get a specific problem
- `GET /api/results` - List available result files
- `GET /api/results/<filename>` - Get contents of a result file
- `POST /api/evaluate` - Run an evaluation

## Project Structure

```
/workspace
├── app.py                 # Flask backend API
├── static/
│   ├── index.html        # Main PWA page
│   ├── styles.css        # Styling
│   ├── app.js           # Frontend JavaScript
│   ├── sw.js            # Service worker
│   ├── manifest.json    # PWA manifest
│   └── icon-*.png       # PWA icons
├── generate_icons.py    # Icon generation script
└── requirements.txt     # Python dependencies
```
