# sAIfty+ Image Authenticity Scanner

A polished Flask + HTML/CSS/JavaScript prototype for screening images before they enter AI training datasets. The goal is not novelty detection for fun; it is reducing AI inbreeding risk by flagging synthetic or suspicious images before they pollute future model training data.

## Supported Upload Formats

The scanner accepts common iPhone and Android image formats:

- JPEG family: `.jpg`, `.jpeg`, `.jpe`, `.jfif`, `.pjpeg`
- Screenshots and web exports: `.png`, `.webp`, `.avif`, `.gif`
- iPhone/Android high-efficiency photos: `.heic`, `.heics`, `.heif`, `.heifs`, `.hif`
- Additional phone/library exports: `.tif`, `.tiff`, `.bmp`, `.mpo`
- Mobile RAW / Apple ProRAW / Android RAW: `.dng`

Browser preview support varies by device. HEIC/HEIF/DNG files may show a fallback preview card, but the Flask backend can still analyze them.

Uploads are capped at 100 MB so large Apple ProRAW or Android RAW files can be accepted without allowing unlimited request sizes.

## File Structure

```text
.
├── app.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── .python-version
├── .env.example
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
├── .gitignore
└── README.md
```

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

If `python` is not on PATH, install Python 3.11+ from python.org first.

## Optional Trained Detector API

The app can use Sightengine's trained `genai` detector as the primary AI probability score, while keeping the local forensic scanner for explainability.

Create a `.env` file or set these environment variables:

```powershell
$env:SIGHTENGINE_API_USER="your_api_user_here"
$env:SIGHTENGINE_API_SECRET="your_api_secret_here"
```

When those variables are missing, the app falls back to the local educational detector.

## Run Locally

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

On the same Wi-Fi network, another device can usually open the app with your computer's local IP address:

```text
http://YOUR_LOCAL_IP:5000
```

## Render Deployment

1. Push this project to GitHub.
2. In Render, create a new Web Service and connect the repo.
3. Use `Python 3` as the environment.
4. Keep the included `.python-version` file so Render uses Python 3.12.13 instead of a newer default that may not have every scientific wheel available yet.
5. Set the build command to:

```text
pip install -r requirements.txt
```

6. Set the start command to:

```text
gunicorn app:app
```

The included `Procfile` uses the same command, and `app.py` reads Render's `PORT` environment variable when run directly.

7. Add environment variables in Render:

```text
SIGHTENGINE_API_USER=your_api_user_here
SIGHTENGINE_API_SECRET=your_api_secret_here
```

## Detection Scoring

The backend returns AI-risk scores from 0 to 100. Higher means more suspicious.

| Signal | Weight | What it checks |
|---|---:|---|
| Metadata | 20% | Missing camera EXIF, incomplete metadata, or generator terms like Stable Diffusion, Midjourney, DALL-E, OpenAI, ComfyUI, Automatic1111, SDXL, Flux, Firefly, or prompt/seed fields |
| Texture | 19% | Laplacian variance, local variance, and entropy for overly smooth or strange texture patterns |
| Frequency | 16% | FFT spectrum checks for synthetic smoothness, low high-frequency detail, or repeating spectral peaks |
| Edge consistency | 14% | Canny/Sobel edge density, edge distribution, and sharpness consistency |
| Compression/noise | 15% | Residual noise distribution and JPEG-like block boundary behavior |
| Pattern consistency | 9% | Repeated patch structures and unusually uniform local sharpness/noise/saturation |
| Color distribution | 7% | Saturation, brightness, clipping, and unusually polished color balance |

The scanner also applies a contextual boost when several visual signals look suspicious and the file lacks reliable camera EXIF. That makes phone-saved AI images more likely to be flagged while still giving real camera photos credit when camera metadata and visual signals agree.

Final verdict bands:

```text
0-39   Likely Real
40-69  Uncertain
70-100 Likely AI-Generated
```

Confidence is based on whether the individual signals agree or conflict.

## Presentation Angle

sAIfty+ protects dataset integrity. High-risk images should be quarantined, uncertain images should be manually reviewed, and lower-risk images can move forward with normal data quality checks. This helps prevent AI inbreeding, where models are trained on synthetic outputs from other models and gradually lose reliability.

## Limitations

- This is an educational prototype.
- It does not guarantee perfect detection.
- Some real photos lack metadata after sharing or editing.
- Some AI images may include fake metadata.
- Best results come from combining automated scoring with human review.

## Future Upgrades

- Add a real ML classifier trained on known real and AI-generated datasets.
- Add OCR checks for warped text, signs, labels, and watermarks.
- Add face/hand-specific artifact detectors.
- Store review history in SQLite or Postgres.
- Add batch upload for dataset audits.
- Export a CSV report for training-data curation teams.
- Add user accounts, reviewer comments, and audit trails.
