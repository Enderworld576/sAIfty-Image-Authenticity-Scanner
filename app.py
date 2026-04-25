import io
import math
import os
import tempfile
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from PIL import ExifTags, Image, ImageFile, ImageOps, UnidentifiedImageError
from dotenv import load_dotenv

load_dotenv()

try:
    from pillow_heif import register_heif_opener

    register_heif_opener(thumbnails=False)
    HEIF_SUPPORT_ENABLED = True
except ImportError:
    HEIF_SUPPORT_ENABLED = False

try:
    import rawpy
except ImportError:
    rawpy = None


app = Flask(__name__)
CORS(app)

# Keep uploads reasonable for local laptops and free hosting tiers, while still
# allowing larger phone photos and many mobile RAW/DNG captures.
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

ImageFile.LOAD_TRUNCATED_IMAGES = True

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "jpe",
    "jfif",
    "pjpeg",
    "png",
    "webp",
    "heic",
    "heics",
    "heif",
    "heifs",
    "hif",
    "avif",
    "gif",
    "tif",
    "tiff",
    "bmp",
    "mpo",
    "dng",
}
RAW_EXTENSIONS = {"dng"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "AVIF", "GIF", "TIFF", "BMP", "MPO", "DNG"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heic-sequence",
    "image/x-heic",
    "image/heif",
    "image/heif-sequence",
    "image/x-heif",
    "image/avif",
    "image/avif-sequence",
    "image/gif",
    "image/tiff",
    "image/bmp",
    "image/x-ms-bmp",
    "image/dng",
    "image/x-dng",
    "image/x-adobe-dng",
    "application/dng",
    "application/x-dng",
    "application/octet-stream",
}
SUPPORTED_FORMAT_LABEL = "JPG, JPEG, PNG, WebP, HEIC, HEIF, AVIF, GIF, TIFF, BMP, MPO, or DNG"
MAX_ANALYSIS_DIMENSION = 1200
EXTERNAL_API_DIMENSION = 1600
SIGHTENGINE_API_URL = "https://api.sightengine.com/1.0/check.json"
SIGHTENGINE_TIMEOUT_SECONDS = 25

SUSPICIOUS_METADATA_TERMS = [
    "stable diffusion",
    "midjourney",
    "dall-e",
    "dall e",
    "dalle",
    "openai",
    "chatgpt",
    "comfyui",
    "automatic1111",
    "a1111",
    "adobe firefly",
    "firefly",
    "stability ai",
    "sdxl",
    "flux",
    "fooocus",
    "invokeai",
    "novelai",
    "civitai",
    "leonardo ai",
    "ideogram",
    "runway",
    "negative prompt",
    "cfg scale",
    "sampler",
    "seed",
    "steps",
    "prompt:",
    "ai generated",
    "ai-generated",
]

CAMERA_EXIF_FIELDS = {
    "Make",
    "Model",
    "LensModel",
    "DateTimeOriginal",
    "DateTimeDigitized",
    "ISOSpeedRatings",
    "FNumber",
    "ExposureTime",
    "FocalLength",
}


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    """Constrain a numeric score to the dashboard's 0-100 scale."""
    return max(low, min(high, value))


def file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def allowed_file(filename: str, mimetype: str = "") -> bool:
    extension = file_extension(filename)
    return extension in ALLOWED_EXTENSIONS or mimetype.lower() in ALLOWED_MIME_TYPES


def safe_string(value) -> str:
    """Convert metadata values into searchable text without crashing on bytes."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    if isinstance(value, (tuple, list)):
        return " ".join(safe_string(item) for item in value[:12])
    return str(value)


def extract_metadata(image: Image.Image) -> Dict[str, str]:
    """Read EXIF and text metadata from common image formats."""
    metadata: Dict[str, str] = {}

    try:
        exif = image.getexif()
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            text = safe_string(value).strip()
            if text:
                metadata[tag_name] = text
    except Exception:
        # Corrupt or unusual EXIF blocks should not break the scanner.
        pass

    for key, value in image.info.items():
        # PNG/WebP generators often store prompts/workflows here.
        if key.lower() == "exif":
            continue
        text = safe_string(value).strip()
        if text:
            metadata[f"info:{key}"] = text[:500]

    return metadata


def metadata_traits(metadata: Dict[str, str]) -> Dict:
    """Summarize metadata into flags used by scoring and final fusion."""
    combined_text = " ".join(f"{key} {value}" for key, value in metadata.items()).lower()
    suspicious_hits = [term for term in SUSPICIOUS_METADATA_TERMS if term in combined_text]
    camera_hits = [field for field in CAMERA_EXIF_FIELDS if metadata.get(field)]

    return {
        "combined_text": combined_text,
        "suspicious_hits": suspicious_hits,
        "camera_hits": camera_hits,
        "has_camera_metadata": bool(len(camera_hits) >= 4 or metadata.get("MobileRawFormat")),
        "has_partial_camera_metadata": bool(camera_hits),
        "is_mobile_raw": bool(metadata.get("MobileRawFormat")),
        "has_metadata": bool(metadata),
    }


def open_raw_image(image_bytes: bytes, extension: str) -> Image.Image:
    """Decode mobile RAW/DNG photos into an RGB Pillow image for analysis."""
    if rawpy is None:
        raise UnidentifiedImageError("RAW/DNG support is not installed.")

    suffix = f".{extension or 'dng'}"
    with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
        temp_file.write(image_bytes)
        temp_file.flush()

        with rawpy.imread(temp_file.name) as raw:
            rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=8)

    image = Image.fromarray(rgb, "RGB")
    image.format = "DNG"
    image.info["MobileRawFormat"] = "DNG RAW / Apple ProRAW / Android RAW"
    return image


def open_uploaded_image(image_bytes: bytes, filename: str) -> Image.Image:
    """Open regular phone images with Pillow and RAW/DNG images with rawpy."""
    extension = file_extension(filename)

    if extension in RAW_EXTENSIONS:
        return open_raw_image(image_bytes, extension)

    image = Image.open(io.BytesIO(image_bytes))
    if getattr(image, "is_animated", False) or image.format == "MPO":
        image.seek(0)
    image.load()
    return image


def analyze_metadata(image: Image.Image) -> Tuple[int, List[str], Dict[str, str]]:
    """Estimate AI risk from camera metadata and generator fingerprints."""
    metadata = extract_metadata(image)
    traits = metadata_traits(metadata)
    suspicious_hits = traits["suspicious_hits"]
    camera_hits = traits["camera_hits"]
    explanations: List[str] = []

    if metadata.get("MobileRawFormat"):
        score = 18
        explanations.append("The file was decoded as a mobile RAW/DNG photo, lowering metadata risk.")
    elif suspicious_hits:
        score = 95
        readable_hits = ", ".join(sorted(set(suspicious_hits))[:3])
        explanations.append(f"Metadata references known image-generation tools: {readable_hits}.")
    elif len(camera_hits) >= 4:
        score = 12
        explanations.append("Camera EXIF fields were present, lowering metadata risk.")
    elif camera_hits:
        score = 32
        explanations.append("Some camera metadata was present, but the record was incomplete.")
    elif metadata:
        score = 72
        explanations.append("Non-camera metadata was present, but key camera fields were missing.")
    else:
        score = 88
        explanations.append("Camera metadata was missing or incomplete.")

    return int(round(score)), explanations, metadata


def prepare_image(image: Image.Image) -> Image.Image:
    """Normalize orientation, resize large images, and convert to RGB."""
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    if max(image.size) > MAX_ANALYSIS_DIMENSION:
        image.thumbnail((MAX_ANALYSIS_DIMENSION, MAX_ANALYSIS_DIMENSION), Image.Resampling.LANCZOS)

    return image


def prepare_external_api_image(image: Image.Image) -> Tuple[bytes, str]:
    """Convert any phone format into a compact JPEG for API detectors."""
    api_image = ImageOps.exif_transpose(image).convert("RGB")
    if max(api_image.size) > EXTERNAL_API_DIMENSION:
        api_image.thumbnail((EXTERNAL_API_DIMENSION, EXTERNAL_API_DIMENSION), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    api_image.save(output, format="JPEG", quality=94, optimize=True)
    output.seek(0)
    return output.read(), "saifty_scan.jpg"


def grid_values(array: np.ndarray, grid_size: int = 8) -> np.ndarray:
    """Split an image-like array into grid cells and return each cell's mean."""
    height, width = array.shape[:2]
    cell_h = max(1, height // grid_size)
    cell_w = max(1, width // grid_size)
    values = []

    for y in range(0, height, cell_h):
        for x in range(0, width, cell_w):
            cell = array[y : min(y + cell_h, height), x : min(x + cell_w, width)]
            if cell.size:
                values.append(float(np.mean(cell)))

    return np.array(values, dtype=np.float32)


def analyze_texture(gray: np.ndarray) -> Tuple[int, List[str]]:
    """Score smoothness and local detail using Laplacian/local variance."""
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian_variance = float(laplacian.var())

    gray_float = gray.astype(np.float32)
    mean = cv2.blur(gray_float, (9, 9))
    mean_sq = cv2.blur(gray_float * gray_float, (9, 9))
    local_variance = np.maximum(mean_sq - mean * mean, 0)
    local_mean = float(np.mean(local_variance))
    local_std = float(np.std(local_variance))

    # Low Laplacian/local variance means the image is unusually smooth.
    laplacian_risk = 100 - clamp((math.log1p(laplacian_variance) - 3.6) / 3.4 * 100)
    local_risk = 100 - clamp((math.log1p(local_mean) - 3.4) / 3.4 * 100)
    uniformity_ratio = local_std / (local_mean + 1e-6)
    uniformity_risk = clamp((0.85 - uniformity_ratio) / 0.85 * 100)

    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    probabilities = hist / (hist.sum() + 1e-6)
    entropy = -float(np.sum(probabilities * np.log2(probabilities + 1e-12)))
    entropy_risk = max(
        clamp((6.35 - entropy) / 1.35 * 100),
        clamp((entropy - 7.92) / 0.35 * 100) * 0.55,
    )

    score = int(round(clamp(0.42 * laplacian_risk + 0.28 * local_risk + 0.15 * uniformity_risk + 0.15 * entropy_risk)))
    explanations: List[str] = []

    if score >= 58:
        explanations.append("Texture smoothness was higher than expected for a natural photo.")
    if entropy_risk >= 62:
        explanations.append("Pixel entropy was outside the normal range expected from camera photos.")
    elif score <= 28:
        explanations.append("Texture detail looked consistent with natural camera capture.")

    return score, explanations


def analyze_frequency(gray: np.ndarray) -> Tuple[int, List[str]]:
    """Look for synthetic smoothness or spectral peaks in the frequency domain."""
    height, width = gray.shape[:2]
    scale = min(1.0, 512 / max(height, width))
    if scale < 1.0:
        gray_small = cv2.resize(gray, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    else:
        gray_small = gray.copy()

    gray_float = gray_small.astype(np.float32)
    gray_float -= float(np.mean(gray_float))

    win_y = np.hanning(gray_float.shape[0])
    win_x = np.hanning(gray_float.shape[1])
    window = np.outer(win_y, win_x).astype(np.float32)
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(gray_float * window))) ** 2

    rows, cols = gray_float.shape
    y, x = np.indices((rows, cols))
    center_y, center_x = rows / 2, cols / 2
    radius = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    radius /= max(1.0, float(radius.max()))

    usable = radius > 0.025
    total_energy = float(np.sum(spectrum[usable])) + 1e-6
    low_ratio = float(np.sum(spectrum[(radius >= 0.025) & (radius < 0.12)]) / total_energy)
    mid_ratio = float(np.sum(spectrum[(radius >= 0.12) & (radius < 0.32)]) / total_energy)
    high_ratio = float(np.sum(spectrum[radius >= 0.32]) / total_energy)

    smooth_frequency_risk = clamp((0.11 - high_ratio) / 0.10 * 100)
    over_sharpened_risk = clamp((high_ratio - 0.42) / 0.26 * 100)
    low_frequency_bias_risk = clamp((low_ratio / (mid_ratio + high_ratio + 1e-6) - 3.0) / 5.0 * 100)

    annulus = spectrum[(radius > 0.05) & (radius < 0.48)]
    if annulus.size:
        peak_ratio = float(np.percentile(annulus, 99.85) / (np.percentile(annulus, 95) + 1e-6))
    else:
        peak_ratio = 1.0
    periodic_peak_risk = clamp((peak_ratio - 10.0) / 34.0 * 100)

    score_value = clamp(
        0.42 * smooth_frequency_risk
        + 0.18 * over_sharpened_risk
        + 0.25 * low_frequency_bias_risk
        + 0.15 * periodic_peak_risk
    )
    if periodic_peak_risk >= 65:
        score_value = max(score_value, 58)
    if smooth_frequency_risk >= 72 and low_frequency_bias_risk >= 55:
        score_value = max(score_value, 64)

    score = int(round(clamp(score_value)))
    explanations: List[str] = []

    if score >= 58:
        explanations.append("Frequency analysis found overly smooth or synthetic-looking spectral patterns.")
    elif periodic_peak_risk >= 65:
        explanations.append("Frequency analysis found repeating spectral peaks that can indicate generated texture.")
    elif score <= 24:
        explanations.append("Frequency detail looked closer to natural camera output.")

    return score, explanations


def analyze_edges(gray: np.ndarray) -> Tuple[int, List[str]]:
    """Score edge density and consistency with Canny + Sobel statistics."""
    median = float(np.median(gray))
    lower = int(max(0, 0.66 * median))
    upper = int(min(255, 1.33 * median))
    edges = cv2.Canny(gray, lower, upper)
    edge_density = float(np.mean(edges > 0))

    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient = np.sqrt(sobel_x * sobel_x + sobel_y * sobel_y)
    edge_strengths = gradient[edges > 0]

    block_density = grid_values((edges > 0).astype(np.float32), 8)
    block_mean = float(np.mean(block_density)) + 1e-6
    block_cv = float(np.std(block_density) / block_mean)

    if edge_strengths.size:
        strength_cv = float(np.std(edge_strengths) / (np.mean(edge_strengths) + 1e-6))
    else:
        strength_cv = 2.0

    density_risk = clamp(abs(edge_density - 0.085) / 0.12 * 100)
    if edge_density < 0.015:
        density_risk = max(density_risk, 78)
    block_risk = clamp(abs(block_cv - 0.9) / 1.1 * 100)
    strength_risk = clamp((strength_cv - 0.72) / 0.85 * 100)

    score = int(round(clamp(0.35 * density_risk + 0.4 * block_risk + 0.25 * strength_risk)))
    explanations: List[str] = []

    if score >= 58:
        explanations.append("Edge sharpness was inconsistent across the image.")
    elif score <= 28:
        explanations.append("Edge density and sharpness looked relatively consistent.")

    return score, explanations


def analyze_compression(gray: np.ndarray) -> Tuple[int, List[str]]:
    """Estimate suspicious noise/compression patterns from residual maps."""
    gray_float = gray.astype(np.float32)
    blurred = cv2.GaussianBlur(gray_float, (5, 5), 0)
    residual = np.abs(gray_float - blurred)
    noise_mean = float(np.mean(residual))

    region_noise = grid_values(residual, 8)
    region_cv = float(np.std(region_noise) / (np.mean(region_noise) + 1e-6))

    diff_x = np.abs(np.diff(gray_float, axis=1))
    diff_y = np.abs(np.diff(gray_float, axis=0))
    vertical_boundary = diff_x[:, 7::8]
    horizontal_boundary = diff_y[7::8, :]
    boundary_mean = float(np.mean([vertical_boundary.mean() if vertical_boundary.size else 0, horizontal_boundary.mean() if horizontal_boundary.size else 0]))
    general_mean = float(np.mean([diff_x.mean(), diff_y.mean()])) + 1e-6
    block_ratio = boundary_mean / general_mean

    low_noise_risk = 100 - clamp((noise_mean - 1.6) / 5.2 * 100)
    uniform_noise_risk = clamp((0.42 - region_cv) / 0.42 * 100)
    uneven_noise_risk = clamp((region_cv - 1.35) / 1.0 * 100)
    blockiness_risk = clamp(abs(block_ratio - 1.0) / 0.75 * 100)

    score = int(round(clamp(0.4 * low_noise_risk + 0.25 * uniform_noise_risk + 0.2 * uneven_noise_risk + 0.15 * blockiness_risk)))
    explanations: List[str] = []

    if score >= 58:
        explanations.append("Compression and noise patterns were unusual.")
    elif score <= 28:
        explanations.append("Noise distribution looked typical for compressed camera output.")

    return score, explanations


def analyze_color(rgb: np.ndarray) -> Tuple[int, List[str]]:
    """Use saturation/brightness statistics as a small supporting signal."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1].astype(np.float32)
    value = hsv[:, :, 2].astype(np.float32)

    saturation_mean = float(np.mean(saturation))
    saturation_std = float(np.std(saturation))
    value_std = float(np.std(value))
    clipped_ratio = float(np.mean((value < 4) | (value > 251)))

    saturation_extreme_risk = clamp(abs(saturation_mean - 82) / 95 * 100)
    polished_risk = clamp((36 - saturation_std) / 36 * 100) * 0.55 + clamp((42 - value_std) / 42 * 100) * 0.45
    clipping_risk = clamp((clipped_ratio - 0.04) / 0.12 * 100)

    score = int(round(clamp(0.35 * saturation_extreme_risk + 0.4 * polished_risk + 0.25 * clipping_risk)))
    explanations: List[str] = []

    if score >= 58:
        explanations.append("Color balance appeared unusually polished or clipped.")

    return score, explanations


def analyze_pattern_consistency(rgb: np.ndarray, gray: np.ndarray) -> Tuple[int, List[str]]:
    """Search for repeated patches and overly uniform local image statistics."""
    small = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    grid_size = 8
    cell_size = small.shape[0] // grid_size
    features = []
    positions = []

    for row in range(grid_size):
        for col in range(grid_size):
            patch = small[row * cell_size : (row + 1) * cell_size, col * cell_size : (col + 1) * cell_size]
            patch_std = float(np.std(patch))
            if patch_std < 8:
                continue

            feature = cv2.resize(patch, (12, 12), interpolation=cv2.INTER_AREA).astype(np.float32)
            feature = (feature - float(np.mean(feature))) / (float(np.std(feature)) + 1e-6)
            features.append(feature.flatten())
            positions.append((row, col))

    repeated_patch_risk = 0.0
    if len(features) >= 5:
        feature_array = np.vstack(features)
        similarity = (feature_array @ feature_array.T) / feature_array.shape[1]
        repeated_pairs = 0
        possible_pairs = 0
        max_similarity = 0.0

        for i in range(len(features)):
            for j in range(i + 1, len(features)):
                row_i, col_i = positions[i]
                row_j, col_j = positions[j]
                if abs(row_i - row_j) <= 1 and abs(col_i - col_j) <= 1:
                    continue

                possible_pairs += 1
                pair_similarity = float(similarity[i, j])
                max_similarity = max(max_similarity, pair_similarity)
                if pair_similarity > 0.90:
                    repeated_pairs += 1

        repeat_ratio = repeated_pairs / max(1, possible_pairs)
        repeated_patch_risk = max(
            clamp((repeat_ratio - 0.025) / 0.11 * 100),
            clamp((max_similarity - 0.93) / 0.06 * 100) * 0.7,
        )

    laplacian_abs = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    blurred = cv2.GaussianBlur(gray.astype(np.float32), (5, 5), 0)
    residual = np.abs(gray.astype(np.float32) - blurred)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    local_sharpness = grid_values(laplacian_abs, grid_size)
    local_noise = grid_values(residual, grid_size)
    local_saturation = grid_values(hsv[:, :, 1].astype(np.float32), grid_size)

    sharpness_cv = float(np.std(local_sharpness) / (np.mean(local_sharpness) + 1e-6))
    noise_cv = float(np.std(local_noise) / (np.mean(local_noise) + 1e-6))
    saturation_cv = float(np.std(local_saturation) / (np.mean(local_saturation) + 1e-6))

    overly_uniform_risk = (
        0.46 * clamp((0.48 - sharpness_cv) / 0.48 * 100)
        + 0.34 * clamp((0.36 - noise_cv) / 0.36 * 100)
        + 0.20 * clamp((0.32 - saturation_cv) / 0.32 * 100)
    )

    score = int(round(clamp(0.58 * repeated_patch_risk + 0.42 * overly_uniform_risk)))
    explanations: List[str] = []

    if repeated_patch_risk >= 58:
        explanations.append("Patch analysis found repeated texture structures in different parts of the image.")
    if overly_uniform_risk >= 64:
        explanations.append("Local sharpness, noise, and saturation were unusually uniform across the image.")
    if score <= 24:
        explanations.append("Patch-level detail looked less repetitive than many generated images.")

    return score, explanations


def weighted_probability(scores: Dict[str, int]) -> int:
    weights = {
        "metadata_score": 0.20,
        "texture_score": 0.19,
        "frequency_score": 0.16,
        "edge_score": 0.14,
        "compression_score": 0.15,
        "pattern_score": 0.09,
        "color_score": 0.07,
    }
    probability = sum(scores[key] * weight for key, weight in weights.items())
    return int(round(clamp(probability)))


def apply_contextual_adjustments(
    ai_probability: int,
    scores: Dict[str, int],
    metadata: Dict[str, str],
    image_size: Tuple[int, int],
) -> Tuple[int, List[str]]:
    """Fuse metadata and visual signals the way a reviewer would reason about them."""
    traits = metadata_traits(metadata)
    visual_keys = ["texture_score", "frequency_score", "edge_score", "compression_score", "pattern_score"]
    visual_scores = np.array([scores[key] for key in visual_keys], dtype=np.float32)
    visual_average = float(np.mean(visual_scores))
    strong_visuals = int(np.sum(visual_scores >= 56))
    notes: List[str] = []
    adjusted = float(ai_probability)

    if traits["suspicious_hits"]:
        adjusted = max(adjusted, 88)
        notes.append("Generator-related metadata was strong enough to override weaker visual signals.")
    elif not traits["has_camera_metadata"] and visual_average >= 58 and strong_visuals >= 3:
        adjusted += 18
        notes.append("Multiple visual signals looked synthetic and the file lacked reliable camera metadata.")
    elif not traits["has_camera_metadata"] and visual_average >= 48 and strong_visuals >= 2:
        adjusted += 12
        notes.append("Several visual signals were suspicious while camera metadata was missing.")
    elif not traits["has_camera_metadata"] and visual_average >= 40 and strong_visuals >= 2:
        adjusted += 7
        notes.append("The missing camera metadata increased risk because visual signals were not clean.")

    width, height = image_size
    aspect_ratio = width / max(1, height)
    near_square = abs(aspect_ratio - 1.0) <= 0.025
    common_generated_canvas = near_square and (
        width in {512, 640, 768, 896, 1024, 1152, 1280, 1536, 1792, 2048}
        or (width % 64 == 0 and height % 64 == 0 and max(width, height) <= 2048)
    )

    if common_generated_canvas and not traits["has_camera_metadata"] and visual_average >= 36:
        adjusted += 6
        notes.append("The image uses a square, generator-style canvas size and lacks camera metadata.")

    if traits["has_camera_metadata"] and not traits["suspicious_hits"] and visual_average < 42:
        adjusted -= 7
        notes.append("Camera metadata and low visual-risk signals reduced the final AI probability.")

    if traits["is_mobile_raw"] and not traits["suspicious_hits"]:
        adjusted -= 8
        notes.append("Mobile RAW/DNG decoding reduced risk because the source resembles direct camera capture.")

    return int(round(clamp(adjusted))), notes


def analyze_with_sightengine(image: Image.Image) -> Optional[Dict]:
    """Call Sightengine's trained genai detector when API keys are configured."""
    api_user = os.environ.get("SIGHTENGINE_API_USER", "").strip()
    api_secret = os.environ.get("SIGHTENGINE_API_SECRET", "").strip()

    if not api_user or not api_secret:
        return None

    media_bytes, media_name = prepare_external_api_image(image)
    params = {
        "models": "genai",
        "api_user": api_user,
        "api_secret": api_secret,
    }
    files = {
        "media": (media_name, media_bytes, "image/jpeg"),
    }

    response = requests.post(SIGHTENGINE_API_URL, data=params, files=files, timeout=SIGHTENGINE_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "success":
        error_message = payload.get("error", {}).get("message") or "Sightengine returned a failed response."
        raise RuntimeError(error_message)

    type_result = payload.get("type", {})
    probability = int(round(clamp(float(type_result.get("ai_generated", 0)) * 100)))
    generators = type_result.get("ai_generators") or {}
    top_generators = sorted(
        ((name, float(score)) for name, score in generators.items() if isinstance(score, (int, float))),
        key=lambda item: item[1],
        reverse=True,
    )[:3]

    return {
        "provider": "Sightengine genai",
        "ai_probability": probability,
        "raw_response": payload,
        "top_generators": [
            {"name": name.replace("_", " ").title(), "score": int(round(clamp(score * 100)))}
            for name, score in top_generators
            if score > 0.01
        ],
    }


def apply_external_detector(local_result: Dict, external_result: Optional[Dict]) -> Dict:
    """Prefer the trained API detector when available, keeping local scores as explainability."""
    if not external_result:
        local_result["detector_provider"] = "Local forensic prototype"
        local_result["external_ai_probability"] = None
        local_result["external_top_generators"] = []
        return local_result

    local_probability = int(local_result["ai_probability"])
    external_probability = int(external_result["ai_probability"])
    fused_probability = int(round(clamp(0.82 * external_probability + 0.18 * local_probability)))

    if external_probability >= 88:
        fused_probability = max(fused_probability, external_probability - 3)
    elif external_probability <= 12:
        fused_probability = min(fused_probability, external_probability + 6)

    local_result["ai_probability"] = fused_probability
    verdict, confidence, risk_level = classify_result(fused_probability, {
        "metadata_score": local_result["metadata_score"],
        "texture_score": local_result["texture_score"],
        "frequency_score": local_result["frequency_score"],
        "edge_score": local_result["edge_score"],
        "compression_score": local_result["compression_score"],
        "pattern_score": local_result["pattern_score"],
        "color_score": local_result["color_score"],
        "external_score": external_probability,
    })
    if external_probability >= 85 or external_probability <= 15:
        confidence = "High"

    local_result["verdict"] = verdict
    local_result["confidence"] = confidence
    local_result["risk_level"] = risk_level
    local_result["detector_provider"] = "Sightengine genai + local explainability"
    local_result["external_ai_probability"] = external_probability
    local_result["external_top_generators"] = external_result["top_generators"]

    generator_text = ""
    if external_result["top_generators"]:
        generator_text = " Top generator matches: " + ", ".join(
            f"{item['name']} {item['score']}%" for item in external_result["top_generators"]
        ) + "."

    local_result["explanations"].insert(
        0,
        f"Trained API detector estimated {external_probability}% AI probability using pixel-level model evidence.{generator_text}",
    )
    return local_result


def classify_result(ai_probability: int, scores: Dict[str, int]) -> Tuple[str, str, str]:
    if ai_probability >= 70:
        verdict = "Likely AI-Generated"
        risk_level = "High"
    elif ai_probability >= 40:
        verdict = "Uncertain"
        risk_level = "Medium"
    else:
        verdict = "Likely Real"
        risk_level = "Low"

    signal_values = np.array(list(scores.values()), dtype=np.float32)
    disagreement = float(np.std(signal_values))
    distance_from_boundary = min(abs(ai_probability - 40), abs(ai_probability - 70))

    visual_scores = np.array(
        [scores[key] for key in ["texture_score", "frequency_score", "edge_score", "compression_score", "pattern_score"]],
        dtype=np.float32,
    )
    strong_visuals = int(np.sum(visual_scores >= 56))

    if disagreement < 18 and (ai_probability < 32 or ai_probability > 78):
        confidence = "High"
    elif ai_probability >= 78 and strong_visuals >= 3:
        confidence = "High"
    elif disagreement < 30 or distance_from_boundary > 10:
        confidence = "Medium"
    else:
        confidence = "Low"

    return verdict, confidence, risk_level


def analyze_image(image: Image.Image) -> Dict:
    metadata_score, metadata_notes, metadata = analyze_metadata(image)
    normalized = prepare_image(image)
    analysis_size = normalized.size
    rgb = np.array(normalized)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    texture_score, texture_notes = analyze_texture(gray)
    frequency_score, frequency_notes = analyze_frequency(gray)
    edge_score, edge_notes = analyze_edges(gray)
    compression_score, compression_notes = analyze_compression(gray)
    color_score, color_notes = analyze_color(rgb)
    pattern_score, pattern_notes = analyze_pattern_consistency(rgb, gray)

    scores = {
        "metadata_score": metadata_score,
        "texture_score": texture_score,
        "frequency_score": frequency_score,
        "edge_score": edge_score,
        "compression_score": compression_score,
        "pattern_score": pattern_score,
        "color_score": color_score,
    }
    ai_probability = weighted_probability(scores)
    ai_probability, context_notes = apply_contextual_adjustments(ai_probability, scores, metadata, analysis_size)
    verdict, confidence, risk_level = classify_result(ai_probability, scores)

    explanations = metadata_notes + texture_notes + frequency_notes + edge_notes + compression_notes + pattern_notes + color_notes + context_notes
    if risk_level == "Medium":
        explanations.append("Signals were mixed, so this image should be manually reviewed before entering a training dataset.")
    if risk_level == "High":
        explanations.append("High-risk images should be excluded from training data until reviewed.")
    if not explanations:
        explanations.append("The available signals did not show strong AI-generation indicators.")

    return {
        "verdict": verdict,
        "ai_probability": ai_probability,
        "confidence": confidence,
        "risk_level": risk_level,
        "metadata_score": metadata_score,
        "texture_score": texture_score,
        "frequency_score": frequency_score,
        "compression_score": compression_score,
        "edge_score": edge_score,
        "pattern_score": pattern_score,
        "color_score": color_score,
        "explanations": explanations,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": f"No image was uploaded. Choose a supported phone image file ({SUPPORTED_FORMAT_LABEL}) and try again."}), 400

    uploaded_file = request.files["image"]
    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"error": "No image was selected. Choose an image before scanning."}), 400

    if not allowed_file(uploaded_file.filename, uploaded_file.mimetype):
        return jsonify({"error": f"Unsupported file type. Please upload {SUPPORTED_FORMAT_LABEL}."}), 400

    try:
        image_bytes = uploaded_file.read()
        image = open_uploaded_image(image_bytes, uploaded_file.filename)
    except UnidentifiedImageError:
        return jsonify({"error": f"The uploaded file could not be read as an image. Supported formats: {SUPPORTED_FORMAT_LABEL}."}), 400
    except Exception:
        return jsonify({"error": "The image appears to be corrupted or unsupported."}), 400

    if image.format not in ALLOWED_FORMATS:
        return jsonify({"error": f"Unsupported image format. Please upload {SUPPORTED_FORMAT_LABEL}."}), 400

    try:
        result = analyze_image(image)
        try:
            external_result = analyze_with_sightengine(image)
            result = apply_external_detector(result, external_result)
        except Exception:
            result["detector_provider"] = "Local forensic prototype"
            result["external_ai_probability"] = None
            result["external_top_generators"] = []
            result["explanations"].insert(
                0,
                "External trained detector was unavailable, so this result used the local educational scanner only.",
            )
    except Exception:
        return jsonify({"error": "The scanner could not process this image. Try a smaller or different file."}), 500

    return jsonify(result)


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({"error": "The uploaded image is too large. Please use a file smaller than 100 MB."}), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
