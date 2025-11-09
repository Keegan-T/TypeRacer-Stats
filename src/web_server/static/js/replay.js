//const characters = "I know it's a mistake. But there are certain things in life where you know it's a mistake, but you don't really know it's a mistake, because the only way to really know it's a mistake is to make the mistake.".split("");
//const delays = [1.0, 81, 71, 18, 17, 47, 30, 59, 53, 82, 118, 41, 94, 83, 70, 42, 17, 53, 83, 0, 88, 53, 71, 65, 47, 59, 65, 64, 44, 32, 88, 48, 88, 64, 48, 48, 72, 75, 65, 76, 106, 59, 29, 47, 48, 47, 64, 24, 53, 796, 29, 35, 23, 36, 94, 41, 30, 35, 47, 41, 53, 41, 83, 65, 70, 12, 59, 23, 30, 76, 24, 12, 12, 70, 30, 53, 64, 36, 88, 53, 77, 88, 24, 46, 36, 47, 65, 23, 94, 48, 58, 77, 24, 58, 42, 53, 64, 18, 65, 47, 24, 29, 24, 64, 36, 100, 12, 35, 35, 88, 42, 47, 41, 24, 53, 35, 24, 76, 35, 77, 76, 36, 100, 71, 65, 52, 12, 100, 83, 47, 70, 71, 35, 77, 53, 53, 23, 59, 77, 18, 41, 29, 83, 29, 59, 47, 30, 41, 35, 47, 47, 47, 42, 41, 47, 76, 65, 65, 47, 41, 18, 94, 41, 53, 42, 17, 47, 42, 41, 53, 41, 47, 94, 25, 105, 59, 70, 24, 41, 41, 60, 35, 76, 65, 35, 65, 77, 41, 59, 82, 41, 59, 77, 65, 58, 36, 35, 65, 65, 11, 83, 23, 59, 83, 35, 83, 76]

console.log(characters);
console.log(delays);

const replayText = document.getElementById("replayText");
const stats = document.getElementById("stats");

const playPauseBtn = document.getElementById("playPauseBtn");
const speedSelect = document.getElementById("speedSelect");
const skipStartButton = document.getElementById("skip-start");
const rewindButton = document.getElementById("rewind");
const forwardButton = document.getElementById("forward");
const skipEndButton = document.getElementById("skip-end");

let index = 0;
let lastIndex = 0;
let isPlaying = false;
let speedMultiplier = 1;

const cumulativeTimes = [];
let sum = 0;
for (let d of delays) {
    sum += d;
    cumulativeTimes.push(sum);
}

function initReplay() {
    replayText.innerHTML = "";

    characters.forEach(ch => {
        const span = document.createElement("span");
        span.textContent = ch;
        span.classList.add("char");
        replayText.appendChild(span);
    });

    const endSpan = document.createElement("span");
    endSpan.classList.add("char", "caret-end");
    endSpan.textContent = "";
    replayText.appendChild(endSpan);

    index = 0;
    lastIndex = 0;
    isPlaying = false;
}

// On load
initReplay();

// Update caret, typed classes, stats
function updateDisplay() {
    const spans = replayText.querySelectorAll(".char");
    // Update typed classes
    if (index > lastIndex) {
        for (let i = lastIndex; i < index; i++) spans[i].classList.add("typed");
    } else if (index < lastIndex) {
        for (let i = index; i < lastIndex; i++) spans[i].classList.remove("typed");
    }
    // Update caret
    spans.forEach(span => span.classList.remove("caret"));
    if (index < spans.length) spans[index].classList.add("caret");
    lastIndex = index;

    // Stats
    const elapsedMs = index > 0 ? cumulativeTimes[index - 1] / speedMultiplier : 0;
    const elapsedSeconds = (elapsedMs / 1000) * speedMultiplier;
    const wpm = elapsedSeconds > 0 ? 12 * index / elapsedSeconds : 0;
    stats.textContent = `Time: ${elapsedSeconds.toFixed(3)}s | WPM: ${wpm.toFixed(2)}`;
}

// Animation loop
let lastFrameTime = null;
let accumulatedTime = 0;

function tick(timestamp) {
    if (!isPlaying) return;

    if (!lastFrameTime) lastFrameTime = timestamp;
    const delta = timestamp - lastFrameTime;
    lastFrameTime = timestamp;
    accumulatedTime += delta;

    while (index < characters.length && accumulatedTime >= delays[index] / speedMultiplier) {
        accumulatedTime -= delays[index] / speedMultiplier;
        index++;
        updateDisplay();
    }

    if (index >= characters.length) {
        isPlaying = false;
        playPauseBtn.textContent = "▶";
        return;
    }

    requestAnimationFrame(tick);
}

// Click-to-seek
replayText.addEventListener("click", (e) => {
    if (!e.target.classList.contains("char")) return;
    const spans = Array.from(replayText.querySelectorAll(".char"));
    const clickedIndex = spans.indexOf(e.target);
    const rect = e.target.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    index = clickX < rect.width / 2 ? clickedIndex : clickedIndex + 1;
    accumulatedTime = 0; // reset accumulator for new index
    updateDisplay();
});

// Play/pause
playPauseBtn.addEventListener("click", () => {
    if (!isPlaying) {
        isPlaying = true;
        playPauseBtn.textContent = "⏸";
        lastFrameTime = null;
        requestAnimationFrame(tick);
    } else {
        isPlaying = false;
        playPauseBtn.textContent = "▶";
    }
});

// Speed change
speedSelect.addEventListener("change", () => {
    speedMultiplier = parseFloat(speedSelect.value);
});

// Other controls
skipStartButton.addEventListener("click", () => {
    isPlaying = false;
    playPauseBtn.textContent = "▶";
    index = 0;
    accumulatedTime = 0;
    updateDisplay();
});

rewindButton.addEventListener("click", () => {
    isPlaying = false;
    playPauseBtn.textContent = "▶";
    if (index > 0) index--;
    accumulatedTime = 0;
    updateDisplay();
});

forwardButton.addEventListener("click", () => {
    isPlaying = false;
    playPauseBtn.textContent = "▶";
    if (index < characters.length) index++;
    accumulatedTime = 0;
    updateDisplay();
});

skipEndButton.addEventListener("click", () => {
    isPlaying = false;
    playPauseBtn.textContent = "▶";
    index = characters.length;
    accumulatedTime = 0;
    updateDisplay();
});

const toggleBtn = document.getElementById("toggleLog");
const logContent = document.getElementById("typingLogContent");

toggleBtn.addEventListener("click", () => {
    const isVisible = logContent.style.display === "block";
    logContent.style.display = isVisible ? "none" : "block";
    toggleBtn.textContent = isVisible ? "show" : "hide";
});