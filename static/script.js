const imageInput = document.getElementById("imageInput");
const dropZone = document.getElementById("dropZone");
const chooseButton = document.getElementById("chooseButton");
const replaceButton = document.getElementById("replaceButton");
const analyzeButton = document.getElementById("analyzeButton");
const previewWrap = document.getElementById("previewWrap");
const imagePreview = document.getElementById("imagePreview");
const videoPreview = document.getElementById("videoPreview");
const previewFallback = document.getElementById("previewFallback");
const emptyUpload = document.getElementById("emptyUpload");
const fileName = document.getElementById("fileName");
const messageBox = document.getElementById("messageBox");
const batchInput = document.getElementById("batchInput");
const analyzeBatchButton = document.getElementById("analyzeBatchButton");
const batchFileList = document.getElementById("batchFileList");
const batchProgress = document.getElementById("batchProgress");
const batchResultsBody = document.getElementById("batchResultsBody");
const batchTotal = document.getElementById("batchTotal");
const batchReal = document.getElementById("batchReal");
const batchUncertain = document.getElementById("batchUncertain");
const batchAi = document.getElementById("batchAi");
const feedbackPanel = document.getElementById("feedbackPanel");
const feedbackMessage = document.getElementById("feedbackMessage");
const feedbackButtons = document.querySelectorAll("[data-feedback]");
const learningWeights = document.getElementById("learningWeights");
const feedbackCount = document.getElementById("feedbackCount");
const verifiedExamplesCount = document.getElementById("verifiedExamplesCount");
const lastCalibrationUpdate = document.getElementById("lastCalibrationUpdate");
const calibrationBias = document.getElementById("calibrationBias");
const textDetectionInput = document.getElementById("textDetectionInput");
const analyzeTextButton = document.getElementById("analyzeTextButton");
const textDetectionMessage = document.getElementById("textDetectionMessage");
const textResultCard = document.getElementById("textResultCard");
const textProbabilityValue = document.getElementById("textProbabilityValue");
const textProbabilityBar = document.getElementById("textProbabilityBar");
const textVerdictBadge = document.getElementById("textVerdictBadge");
const textRiskValue = document.getElementById("textRiskValue");
const textExplanationList = document.getElementById("textExplanationList");

const probabilityGauge = document.getElementById("probabilityGauge");
const probabilityValue = document.getElementById("probabilityValue");
const verdictBadge = document.getElementById("verdictBadge");
const confidenceValue = document.getElementById("confidenceValue");
const riskValue = document.getElementById("riskValue");
const datasetAction = document.getElementById("datasetAction");
const detectorProvider = document.getElementById("detectorProvider");
const explanationList = document.getElementById("explanationList");
const externalScoreRow = document.getElementById("externalScoreRow");
const scoreChartCanvas = document.getElementById("scoreChart");
const scoreChartFallback = document.getElementById("scoreChartFallback");

const scoreElements = {
    external_ai_probability: {
        bar: document.getElementById("externalBar"),
        label: document.getElementById("externalScore"),
    },
    metadata_score: {
        bar: document.getElementById("metadataBar"),
        label: document.getElementById("metadataScore"),
    },
    texture_score: {
        bar: document.getElementById("textureBar"),
        label: document.getElementById("textureScore"),
    },
    frequency_score: {
        bar: document.getElementById("frequencyBar"),
        label: document.getElementById("frequencyScore"),
    },
    compression_score: {
        bar: document.getElementById("compressionBar"),
        label: document.getElementById("compressionScore"),
    },
    edge_score: {
        bar: document.getElementById("edgeBar"),
        label: document.getElementById("edgeScore"),
    },
    pattern_score: {
        bar: document.getElementById("patternBar"),
        label: document.getElementById("patternScore"),
    },
    color_score: {
        bar: document.getElementById("colorBar"),
        label: document.getElementById("colorScore"),
    },
};

let selectedFile = null;
let selectedBatchFiles = [];
let scoreChart = null;
let previewUrl = "";
let currentAnalysisResult = null;

const allowedExtensions = [
    "jpg",
    "jpeg",
    "jpe",
    "jfif",
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
    "mp4",
    "mov",
    "m4v",
    "webm",
    "avi",
    "mkv",
];
const allowedTypes = [
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
    "video/mp4",
    "video/quicktime",
    "video/x-m4v",
    "video/webm",
    "video/x-msvideo",
    "video/x-matroska",
];

function setMessage(text, type = "") {
    messageBox.textContent = text;
    messageBox.className = `message-box ${type}`.trim();
}

function scoreColor(score) {
    if (score >= 70) return "#ff4d6d";
    if (score >= 40) return "#ffd166";
    return "#20f7a4";
}

function safeScore(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return 0;
    return Math.max(0, Math.min(100, Math.round(numeric)));
}

function verdictClass(verdict) {
    if (verdict === "Likely AI-Generated") return "ai";
    if (verdict === "Uncertain") return "uncertain";
    if (verdict === "Likely Real") return "real";
    return "neutral";
}

function datasetRecommendation(riskLevel) {
    if (riskLevel === "High") return "Quarantine";
    if (riskLevel === "Medium") return "Review";
    if (riskLevel === "Low") return "Approve";
    return "Hold";
}

function isVideoFile(file) {
    const extension = fileExtension(file.name);
    const type = (file.type || "").toLowerCase();
    return type.startsWith("video/") || ["mp4", "mov", "m4v", "webm", "avi", "mkv"].includes(extension);
}

function textVerdictClass(verdict) {
    if (verdict === "Likely AI-Generated") return "ai";
    if (verdict === "Uncertain") return "uncertain";
    if (verdict === "Likely Human") return "real";
    return "neutral";
}

function setTextMessage(text, type = "") {
    textDetectionMessage.textContent = text;
    textDetectionMessage.className = `message-box ${type}`.trim();
}

function setTextLoading(isLoading) {
    analyzeTextButton.disabled = isLoading;
    analyzeTextButton.classList.toggle("is-loading", isLoading);
}

function renderTextExplanations(explanations) {
    textExplanationList.innerHTML = "";
    const notes = explanations?.length ? explanations : ["No text explanation was returned."];
    notes.forEach((text) => {
        const li = document.createElement("li");
        li.textContent = text;
        textExplanationList.appendChild(li);
    });
}

function renderTextResult(result) {
    const probability = safeScore(result.ai_probability);
    textResultCard.hidden = false;
    textProbabilityValue.textContent = `${probability}%`;
    textProbabilityBar.style.width = "0%";
    textProbabilityBar.style.background = `linear-gradient(90deg, ${scoreColor(probability)}, #28d7ff)`;
    requestAnimationFrame(() => {
        textProbabilityBar.style.width = `${probability}%`;
    });
    textVerdictBadge.textContent = result.verdict;
    textVerdictBadge.className = `verdict-badge ${textVerdictClass(result.verdict)}`;
    textRiskValue.textContent = result.risk_level;
    renderTextExplanations(result.explanations || []);
}

async function analyzeText() {
    const text = textDetectionInput.value.trim();

    if (!text) {
        setTextMessage("Paste text before running AI text detection.", "error");
        return;
    }
    if (text.length < 30) {
        setTextMessage("Please enter at least 30 characters for a meaningful text scan.", "error");
        return;
    }

    setTextLoading(true);
    setTextMessage("Scanning text for AI-generated writing patterns...");

    try {
        const response = await fetch("/analyze-text", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "The server could not analyze this text.");
        }

        renderTextResult(data);
        setTextMessage("Text analysis complete. Use the result as dataset triage, not a final verdict.", "success");
    } catch (error) {
        setTextMessage(error.message, "error");
    } finally {
        setTextLoading(false);
    }
}

function setFeedbackMessage(text, type = "") {
    feedbackMessage.textContent = text;
    feedbackMessage.className = `feedback-message ${type}`.trim();
}

function setFeedbackLoading(isLoading) {
    feedbackButtons.forEach((button) => {
        button.disabled = isLoading;
    });
}

function formatCalibrationTime(value) {
    if (!value) return "Not yet";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Just now";

    return date.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    });
}

function renderLearningStatus(status) {
    feedbackCount.textContent = String(status.feedback_count ?? 0);
    verifiedExamplesCount.textContent = String(status.verified_examples_count ?? 0);
    lastCalibrationUpdate.textContent = formatCalibrationTime(status.last_updated);
    calibrationBias.textContent = `${Number(status.calibration_bias ?? 0).toFixed(1)}`;
    learningWeights.innerHTML = "";

    (status.weights || []).forEach((item) => {
        const row = document.createElement("div");
        row.className = "weight-row";

        const label = document.createElement("span");
        label.innerHTML = `<strong>${item.label}</strong><em>${item.percent}%</em>`;

        const track = document.createElement("div");
        track.className = "weight-track";

        const fill = document.createElement("div");
        fill.className = "weight-fill";
        fill.style.width = `${item.percent}%`;

        track.appendChild(fill);
        row.append(label, track);
        learningWeights.appendChild(row);
    });
}

async function loadLearningStatus() {
    try {
        const response = await fetch("/learning-status");
        const status = await response.json();
        if (!response.ok) throw new Error(status.error || "Learning status failed to load.");
        renderLearningStatus(status);
    } catch (error) {
        learningWeights.innerHTML = `<p>${error.message}</p>`;
    }
}

function validateFile(file) {
    if (!file) return "No file selected.";
    const extension = fileExtension(file.name);
    const type = (file.type || "").toLowerCase();
    const knownType = allowedTypes.includes(type);
    const knownExtension = allowedExtensions.includes(extension);
    const imageTypeFromPhone = type.startsWith("image/") && type !== "image/svg+xml";
    const videoTypeFromPhone = type.startsWith("video/");

    if (!knownType && !knownExtension && !imageTypeFromPhone && !videoTypeFromPhone) {
        return "Please upload a phone image or video format such as JPEG, PNG, HEIC, DNG, MP4, MOV, M4V, WebM, AVI, or MKV.";
    }

    return "";
}

function fileExtension(name) {
    return name.includes(".") ? name.split(".").pop().toLowerCase() : "";
}

function selectFile(file) {
    const error = validateFile(file);
    if (error) {
        setMessage(error, "error");
        return;
    }

    selectedFile = file;
    fileName.textContent = file.name;

    if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
    }

    previewUrl = URL.createObjectURL(file);
    previewFallback.hidden = true;
    videoPreview.pause();
    videoPreview.removeAttribute("src");
    videoPreview.load();

    if (isVideoFile(file)) {
        imagePreview.hidden = true;
        imagePreview.removeAttribute("src");
        videoPreview.hidden = false;
        videoPreview.onloadeddata = () => {
            videoPreview.hidden = false;
            previewFallback.hidden = true;
        };
        videoPreview.onerror = () => {
            videoPreview.hidden = true;
            previewFallback.hidden = false;
            setMessage("Video ready. Preview may be unavailable, but the backend can analyze the first frame.", "success");
        };
        videoPreview.src = previewUrl;
    } else {
        videoPreview.hidden = true;
        imagePreview.hidden = false;
        imagePreview.onload = () => {
            imagePreview.hidden = false;
            previewFallback.hidden = true;
        };
        imagePreview.onerror = () => {
            imagePreview.hidden = true;
            previewFallback.hidden = false;
            setMessage("Image ready. This format may not preview in the browser, but the backend can still analyze it.", "success");
        };
        imagePreview.src = previewUrl;
    }

    previewWrap.hidden = false;
    emptyUpload.hidden = true;
    analyzeButton.disabled = false;
    setMessage(isVideoFile(file) ? "Video ready. The scanner will analyze the first frame." : "Image ready. Start analysis when you are ready.", "success");
}

function openFilePicker(event) {
    event.stopPropagation();
    imageInput.click();
}

function setLoading(isLoading) {
    analyzeButton.disabled = isLoading || !selectedFile;
    analyzeButton.classList.toggle("is-loading", isLoading);
}

function animateNumber(element, target, suffix = "") {
    const duration = 800;
    const start = performance.now();

    function frame(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        element.textContent = `${Math.round(target * eased)}${suffix}`;

        if (progress < 1) {
            requestAnimationFrame(frame);
        }
    }

    requestAnimationFrame(frame);
}

function updateGauge(score) {
    const safe = safeScore(score);
    const color = scoreColor(safe);
    probabilityGauge.style.setProperty("--gauge-color", color);
    probabilityGauge.style.setProperty("--score", safe);
    animateNumber(probabilityValue, safe, "%");
}

function updateScoreBar(key, value) {
    const item = scoreElements[key];
    if (!item) return;

    const safe = safeScore(value);
    item.bar.style.width = "0%";
    item.bar.style.background = `linear-gradient(90deg, ${scoreColor(safe)}, #28d7ff)`;
    item.label.textContent = `${safe}`;

    requestAnimationFrame(() => {
        item.bar.style.width = `${safe}%`;
    });
}

function updateExplanations(explanations) {
    explanationList.innerHTML = "";
    const notes = explanations?.length ? explanations : ["No major reason was returned for this scan."];
    notes.forEach((text) => {
        const li = document.createElement("li");
        li.textContent = text;
        explanationList.appendChild(li);
    });
}

function detectionLayerValues(result) {
    return {
        labels: ["Metadata", "Texture", "Frequency", "Compression", "Edges", "Patterns", "Color"],
        values: [
            safeScore(result.metadata_score),
            safeScore(result.texture_score),
            safeScore(result.frequency_score),
            safeScore(result.compression_score),
            safeScore(result.edge_score),
            safeScore(result.pattern_score),
            safeScore(result.color_score),
        ],
    };
}

function updateChartFallback(labels, values) {
    scoreChartFallback.innerHTML = "";

    labels.forEach((label, index) => {
        const value = values[index];
        const row = document.createElement("div");
        row.className = "chart-fallback-row";

        const name = document.createElement("span");
        name.textContent = label;

        const track = document.createElement("div");
        track.className = "chart-fallback-track";

        const fill = document.createElement("div");
        fill.className = "chart-fallback-fill";
        fill.style.width = `${value}%`;
        fill.style.background = `linear-gradient(90deg, ${scoreColor(value)}, #28d7ff)`;
        track.appendChild(fill);

        const number = document.createElement("strong");
        number.textContent = `${value}`;

        row.append(name, track, number);
        scoreChartFallback.appendChild(row);
    });
}

function updateChart(result) {
    const { labels, values } = detectionLayerValues(result);

    updateChartFallback(labels, values);

    if (typeof Chart === "undefined") {
        scoreChartCanvas.hidden = true;
        scoreChartFallback.hidden = false;
        return;
    }

    if (scoreChart) {
        scoreChart.data.datasets[0].data = values;
        scoreChart.data.datasets[0].backgroundColor = values.map(scoreColor);
        scoreChart.update();
        scoreChartCanvas.hidden = false;
        scoreChartFallback.hidden = true;
        return;
    }

    scoreChart = new Chart(scoreChartCanvas, {
        type: "radar",
        data: {
            labels,
            datasets: [{
                label: "AI-risk signal",
                data: values,
                borderColor: "#28d7ff",
                backgroundColor: "rgba(40, 215, 255, 0.18)",
                pointBackgroundColor: values.map(scoreColor),
                pointBorderColor: "#f4fbff",
                pointRadius: 5,
                pointHoverRadius: 7,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    suggestedMin: 0,
                    suggestedMax: 100,
                    angleLines: { color: "rgba(157, 180, 201, 0.18)" },
                    grid: { color: "rgba(157, 180, 201, 0.18)" },
                    pointLabels: { color: "#d6e8f5", font: { size: 12, weight: "700" } },
                    ticks: {
                        backdropColor: "transparent",
                        color: "#9db4c9",
                        stepSize: 20,
                    },
                },
            },
            plugins: {
                legend: {
                    labels: { color: "#d6e8f5", font: { weight: "700" } },
                },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.raw}% AI-risk signal`,
                    },
                },
            },
        },
    });
    scoreChartCanvas.hidden = false;
    scoreChartFallback.hidden = true;
}

function renderResults(result) {
    try {
        currentAnalysisResult = result;
        feedbackPanel.hidden = false;
        setFeedbackMessage("");
        updateGauge(result.ai_probability);

        verdictBadge.textContent = result.verdict;
        verdictBadge.className = `verdict-badge ${verdictClass(result.verdict)}`;
        confidenceValue.textContent = result.confidence;
        riskValue.textContent = result.risk_level;
        datasetAction.textContent = datasetRecommendation(result.risk_level);
        detectorProvider.textContent = result.detector_provider?.includes("Sightengine") ? "API + Local" : "Local";

        const hasExternalScore =
            result.external_ai_probability !== null &&
            result.external_ai_probability !== undefined &&
            Number.isFinite(Number(result.external_ai_probability));
        externalScoreRow.hidden = !hasExternalScore;
        if (hasExternalScore) {
            updateScoreBar("external_ai_probability", result.external_ai_probability);
        }

        Object.keys(scoreElements)
            .filter((key) => key !== "external_ai_probability")
            .forEach((key) => updateScoreBar(key, result[key] ?? 0));
        updateExplanations(result.explanations || []);
        updateChart(result);
    } catch (error) {
        updateExplanations(result.explanations || ["The scan completed, but one dashboard widget could not render."]);
        updateChartFallback(...Object.values(detectionLayerValues(result)));
        scoreChartCanvas.hidden = true;
        scoreChartFallback.hidden = false;
        console.error("Dashboard render fallback used:", error);
    }
}

async function analyzeImage() {
    if (!selectedFile) {
        setMessage("Choose an image before starting the scan.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("image", selectedFile);

    setLoading(true);
    setMessage(isVideoFile(selectedFile) ? "Extracting the first video frame, then scanning image authenticity signals..." : "Scanning metadata, texture, frequency, repeated patterns, edges, compression, and color distribution...");

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "The server could not analyze this image.");
        }

        renderResults(data);
        setMessage(data.input_type === "video" ? "Video first-frame analysis complete. Use the report as a dataset triage signal." : "Analysis complete. Use the report to decide whether this image belongs in a training dataset.", "success");
    } catch (error) {
        setMessage(error.message, "error");
    } finally {
        setLoading(false);
    }
}

chooseButton.addEventListener("click", openFilePicker);
replaceButton.addEventListener("click", openFilePicker);
dropZone.addEventListener("click", () => imageInput.click());
dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        imageInput.click();
    }
});

imageInput.addEventListener("change", (event) => {
    selectFile(event.target.files[0]);
});

["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add("is-dragging");
    });
});

["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove("is-dragging");
    });
});

dropZone.addEventListener("drop", (event) => {
    selectFile(event.dataTransfer.files[0]);
});

analyzeButton.addEventListener("click", analyzeImage);
analyzeTextButton.addEventListener("click", analyzeText);

async function submitFeedback(correction) {
    if (!currentAnalysisResult) {
        setFeedbackMessage("Run a scan before submitting feedback.", "error");
        return;
    }

    setFeedbackLoading(true);
    setFeedbackMessage("Updating calibration weights...");

    try {
        const response = await fetch("/feedback", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                correction,
                result: currentAnalysisResult,
            }),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Feedback could not be saved.");
        }

        renderResults(data.updated_result);
        renderLearningStatus(data.learning_status);
        setFeedbackMessage(data.message || "Model calibration updated.");
        setMessage("Model calibration updated. The final probability was recalculated with the new weights.", "success");
    } catch (error) {
        setFeedbackMessage(error.message, "error");
    } finally {
        setFeedbackLoading(false);
    }
}

feedbackButtons.forEach((button) => {
    button.addEventListener("click", () => {
        submitFeedback(button.dataset.feedback);
    });
});

function batchVerdictClass(verdict) {
    if (verdict === "Likely AI-Generated") return "ai";
    if (verdict === "Uncertain") return "uncertain";
    if (verdict === "Likely Real") return "real";
    return "error";
}

function resetBatchSummary() {
    batchTotal.textContent = "0";
    batchReal.textContent = "0";
    batchUncertain.textContent = "0";
    batchAi.textContent = "0";
}

function updateBatchSummary(results) {
    const realCount = results.filter((result) => result.verdict === "Likely Real").length;
    const uncertainCount = results.filter((result) => result.verdict === "Uncertain").length;
    const aiCount = results.filter((result) => result.verdict === "Likely AI-Generated").length;

    batchTotal.textContent = String(results.length);
    batchReal.textContent = String(realCount);
    batchUncertain.textContent = String(uncertainCount);
    batchAi.textContent = String(aiCount);
}

function renderBatchFileList(files) {
    batchFileList.innerHTML = "";

    files.forEach((file) => {
        const item = document.createElement("li");
        item.textContent = file.name;
        batchFileList.appendChild(item);
    });
}

function setBatchEmptyRow(text) {
    batchResultsBody.innerHTML = "";
    const row = document.createElement("tr");
    row.className = "batch-empty-row";
    row.innerHTML = `<td colspan="5">${text}</td>`;
    batchResultsBody.appendChild(row);
}

function addBatchResultRow(result) {
    const row = document.createElement("tr");
    const reason = result.reason || "No reason returned.";
    const probability = Number.isFinite(result.aiProbability) ? `${result.aiProbability}%` : "--";

    const fileCell = document.createElement("td");
    fileCell.className = "batch-file-cell";
    fileCell.title = result.fileName;
    fileCell.textContent = result.fileName;

    const probabilityCell = document.createElement("td");
    probabilityCell.textContent = probability;

    const verdictCell = document.createElement("td");
    const verdictPill = document.createElement("span");
    // The verdict class controls the row pill color: green, yellow, red, or error.
    verdictPill.className = `batch-verdict ${batchVerdictClass(result.verdict)}`;
    verdictPill.textContent = result.verdict;
    verdictCell.appendChild(verdictPill);

    const confidenceCell = document.createElement("td");
    confidenceCell.textContent = result.confidence || "--";

    const reasonCell = document.createElement("td");
    reasonCell.textContent = reason;

    row.append(fileCell, probabilityCell, verdictCell, confidenceCell, reasonCell);

    batchResultsBody.appendChild(row);
}

async function analyzeBatchFile(file) {
    const formData = new FormData();
    formData.append("image", file);

    const response = await fetch("/analyze", {
        method: "POST",
        body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Analysis failed.");
    }

    return data;
}

batchInput.addEventListener("change", (event) => {
    selectedBatchFiles = Array.from(event.target.files || []);
    renderBatchFileList(selectedBatchFiles);
    resetBatchSummary();

    if (!selectedBatchFiles.length) {
        analyzeBatchButton.disabled = true;
        batchProgress.textContent = "No batch selected.";
        setBatchEmptyRow("Batch results will appear here.");
        return;
    }

    analyzeBatchButton.disabled = false;
    batchProgress.textContent = `${selectedBatchFiles.length} image${selectedBatchFiles.length === 1 ? "" : "s"} selected.`;
    setBatchEmptyRow("Ready to analyze selected images.");
});

analyzeBatchButton.addEventListener("click", async () => {
    if (!selectedBatchFiles.length) return;

    const results = [];
    analyzeBatchButton.disabled = true;
    batchResultsBody.innerHTML = "";
    resetBatchSummary();

    // Keep the backend simple by reusing the existing single-image endpoint
    // once per file instead of creating a separate batch endpoint.
    for (let index = 0; index < selectedBatchFiles.length; index += 1) {
        const file = selectedBatchFiles[index];
        batchProgress.textContent = `Analyzing ${index + 1} of ${selectedBatchFiles.length} images...`;

        try {
            const data = await analyzeBatchFile(file);
            const result = {
                fileName: file.name,
                aiProbability: data.ai_probability,
                verdict: data.verdict,
                confidence: data.confidence,
                reason: (data.explanations || [])[0] || "No major reason flagged.",
            };
            results.push(result);
            addBatchResultRow(result);
        } catch (error) {
            addBatchResultRow({
                fileName: file.name,
                aiProbability: null,
                verdict: "Error",
                confidence: "--",
                reason: error.message,
            });
        }

        updateBatchSummary(results);
    }

    batchProgress.textContent = `Finished analyzing ${selectedBatchFiles.length} image${selectedBatchFiles.length === 1 ? "" : "s"}.`;
    analyzeBatchButton.disabled = false;
});

const chatToggle = document.getElementById("chatToggle");
const chatWindow = document.getElementById("chatWindow");
const chatClose = document.getElementById("chatClose");
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const quickQuestionButtons = document.querySelectorAll("[data-question]");

const unrelatedChatResponse = "I’m designed to answer questions about AI detection and training data safety.";
const chatTopicKeywords = [
    "ai",
    "generated",
    "synthetic",
    "scanner",
    "detect",
    "detection",
    "image",
    "photo",
    "inbreeding",
    "training",
    "dataset",
    "data",
    "metadata",
    "exif",
    "texture",
    "smooth",
    "edge",
    "canny",
    "compression",
    "artifact",
    "frequency",
    "pixel",
    "confidence",
    "probability",
    "score",
    "risk",
    "limitation",
    "wrong",
    "false",
    "real",
    "camera",
    "review",
    "safety",
];

function toggleChat(open) {
    const shouldOpen = open ?? !chatWindow.classList.contains("is-open");
    chatWindow.classList.toggle("is-open", shouldOpen);
    chatWindow.setAttribute("aria-hidden", String(!shouldOpen));
    chatToggle.classList.toggle("is-open", shouldOpen);
    chatToggle.setAttribute("aria-expanded", String(shouldOpen));
    chatToggle.setAttribute("aria-label", shouldOpen ? "Close sAIfty Assistant" : "Open sAIfty Assistant");
    chatToggle.innerHTML = shouldOpen ? '<i class="fa-solid fa-xmark"></i>' : '<i class="fa-solid fa-message"></i>';

    if (shouldOpen) {
        chatInput.focus();
    } else {
        chatToggle.focus();
    }
}

function addChatMessage(text, sender) {
    const message = document.createElement("div");
    message.className = `chat-message ${sender}`;

    const bubble = document.createElement("span");
    bubble.textContent = text;
    message.appendChild(bubble);
    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function isDetectionTopic(question) {
    const normalized = question.toLowerCase();
    return chatTopicKeywords.some((keyword) => {
        if (keyword.length <= 3) {
            return new RegExp(`\\b${keyword}\\b`, "i").test(normalized);
        }

        return normalized.includes(keyword);
    });
}

function assistantReply(question) {
    const normalized = question.toLowerCase();

    if (!isDetectionTopic(normalized)) {
        return unrelatedChatResponse;
    }

    if (normalized.includes("inbreeding")) {
        return "AI inbreeding happens when future models are trained on AI-generated images instead of clean human/camera data. Over time, that can amplify mistakes, reduce realism, and make training datasets less trustworthy.";
    }

    if (normalized.includes("how") && (normalized.includes("work") || normalized.includes("scanner"))) {
        return "The scanner combines a trained AI-image detector when configured with local explainability signals: metadata, texture, frequency patterns, edges, compression noise, repeated patches, and color distribution.";
    }

    if (normalized.includes("wrong") || normalized.includes("limitation") || normalized.includes("false") || normalized.includes("accurate")) {
        return "Yes. It can be wrong. Real photos can lose metadata, edited photos can look synthetic, and AI images can be post-processed. High-risk results should be removed or reviewed, while uncertain results should get human review.";
    }

    if (normalized.includes("metadata") || normalized.includes("exif")) {
        return "Metadata matters because real camera photos often include EXIF fields like camera model, lens, exposure, ISO, and capture time. AI images often lack that data or contain generator clues like prompts, seeds, or model names.";
    }

    if (normalized.includes("texture") || normalized.includes("smooth")) {
        return "Texture analysis checks whether local detail looks too smooth, too uniform, or statistically unusual. Generated images can have polished surfaces or repeated micro-patterns that differ from camera noise.";
    }

    if (normalized.includes("edge") || normalized.includes("canny")) {
        return "Edge detection looks at object boundaries and sharpness consistency. AI images can have strange edge behavior around hands, text, hair, reflections, and background details.";
    }

    if (normalized.includes("compression") || normalized.includes("artifact") || normalized.includes("noise")) {
        return "Compression analysis checks residual noise and JPEG-like artifacts. Camera photos often have natural sensor noise and compression patterns, while generated or heavily processed images can have unusual noise distribution.";
    }

    if (normalized.includes("training") || normalized.includes("dataset") || normalized.includes("safety") || normalized.includes("data")) {
        return "For training data safety, high-risk images should be quarantined, uncertain images should be manually reviewed, and only clean verified images should enter the dataset. That helps reduce AI inbreeding.";
    }

    if (normalized.includes("probability") || normalized.includes("confidence") || normalized.includes("score") || normalized.includes("risk")) {
        return "The AI probability estimates how synthetic the image appears. Confidence reflects whether the detector signals agree. Risk level translates the score into a dataset action: approve, review, or quarantine.";
    }

    if (normalized.includes("real") || normalized.includes("camera") || normalized.includes("photo")) {
        return "A likely real result usually means the image has camera-like metadata or visual signals. It still is not a guarantee, especially if the photo was edited, compressed, screenshotted, or stripped of EXIF data.";
    }

    return "The safest workflow is to treat the scanner as a dataset triage tool: remove high-risk images, manually review uncertain images, and preserve clean camera-origin data for model training.";
}

function submitChatQuestion(question) {
    const trimmed = question.trim();
    if (!trimmed) return;

    addChatMessage(trimmed, "user");
    chatInput.value = "";

    window.setTimeout(() => {
        addChatMessage(assistantReply(trimmed), "bot");
    }, 180);
}

chatToggle.addEventListener("click", () => toggleChat());
chatClose.addEventListener("click", () => toggleChat(false));

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && chatWindow.classList.contains("is-open")) {
        toggleChat(false);
    }
});

toggleChat(false);
loadLearningStatus();

chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitChatQuestion(chatInput.value);
});

quickQuestionButtons.forEach((button) => {
    button.addEventListener("click", () => {
        submitChatQuestion(button.dataset.question || "");
    });
});
