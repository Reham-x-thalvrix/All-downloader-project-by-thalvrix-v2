
const form = document.getElementById("downloadForm");
const urlInput = document.getElementById("videoUrl");
const statusBox = document.getElementById("status");
const result = document.getElementById("result");
const submitBtn = document.getElementById("submitBtn");

function showStatus(message, isError = false) {
    statusBox.textContent = message;
    statusBox.classList.remove("hidden", "error");

    if (isError) {
        statusBox.classList.add("error");
    }
}

document.getElementById("pasteBtn").addEventListener("click", async () => {
    try {
        urlInput.value = await navigator.clipboard.readText();
    } catch {
        showStatus("Clipboard unavailable. Paste manually.", true);
    }
});

function formatTime(seconds) {
    if (!Number.isFinite(Number(seconds))) return "";

    const s = Math.max(0, Math.floor(Number(seconds)));

    return [
        Math.floor(s / 3600),
        Math.floor((s % 3600) / 60),
        s % 60
    ].map((v, i) => i === 0 ? String(v) : String(v).padStart(2, "0"))
     .filter((v, i) => i > 0 || v !== "0")
     .join(":");
}

function sizeText(bytes) {
    if (!bytes) return "Size unknown";

    const units = ["B", "KB", "MB", "GB"];
    let n = bytes;
    let i = 0;

    while (n >= 1024 && i < 3) {
        n /= 1024;
        i++;
    }

    return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const url = urlInput.value.trim();

    if (!url) return;

    result.classList.add("hidden");

    showStatus("Getting video information...");

    submitBtn.disabled = true;
    submitBtn.querySelector("span").textContent = "Please wait...";

    try {
        const response = await fetch(
            `/api/download?url=${encodeURIComponent(url)}`
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "Download failed.");
        }

        document.getElementById("videoTitle").textContent =
            data.title || "Untitled video";

        document.getElementById("uploader").textContent =
            data.uploader ? `By ${data.uploader}` : "Unknown uploader";

        const thumbnail = document.getElementById("thumbnail");

        thumbnail.src = data.thumbnail || "";
        thumbnail.style.visibility = data.thumbnail ? "visible" : "hidden";

        document.getElementById("duration").textContent =
            formatTime(data.duration);

        document.getElementById("extension").textContent =
            (data.ext || "MEDIA").toUpperCase();

        document.getElementById("resolution").textContent =
            data.resolution || "Quality varies";

        const formats = document.getElementById("formats");

        formats.innerHTML = "";

        const items = (data.formats || []).slice(0, 20);

        document.getElementById("formatCount").textContent =
            `${items.length} Options`;

        items.forEach((f) => {
            const row = document.createElement("div");
            row.className = "format-row";

            const info = document.createElement("div");
            info.className = "format-info";

            const strong = document.createElement("strong");

            strong.textContent =
                `${f.resolution || "Available"} · ${(f.ext || "file").toUpperCase()}`;

            const small = document.createElement("small");

            small.textContent =
                f.filesize ? sizeText(f.filesize) :
                f.filesize_approx ? `About ${sizeText(f.filesize_approx)}` :
                "Size unknown";

            info.append(strong, small);

            const link = document.createElement("a");

            link.className = "download-link";
            link.href = f.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "DOWNLOAD ↗";

            row.append(info, link);

            formats.append(row);
        });

        statusBox.classList.add("hidden");
        result.classList.remove("hidden");

        result.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {
        showStatus(error.message || "Something went wrong.", true);
    } finally {
        submitBtn.disabled = false;
        submitBtn.querySelector("span").textContent = "Get Download Links";
    }
});
