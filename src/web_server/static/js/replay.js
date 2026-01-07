// ===== DOM ELEMENTS =====

// Core text display
const replayText = document.getElementById("replayText");
const rawReplayText = document.getElementById("rawReplayText");
const stats = document.getElementById("stats");

// Playback controls
const playPauseButton = document.getElementById("playPauseButton");
const speedSelect = document.getElementById("speedSelect");
const skipStartButton = document.getElementById("skipStart");
const rewindButton = document.getElementById("rewind");
const forwardButton = document.getElementById("forward");
const skipEndButton = document.getElementById("skipEnd");
const rawRewindButton = document.getElementById("rawRewind");
const rawForwardButton = document.getElementById("rawForward");
const adjustedToggle = document.getElementById("adjustedToggle");

// Mistakes / graph
const mistakesCard = document.getElementById("mistakesCard");
const mistakesList = document.getElementById("mistakesList");

// Typing log
const toggleButton = document.getElementById("toggleLog");
const logContent = document.getElementById("typingLogContent");
const copyLogButton = document.getElementById("copyLogButton");
const typingLogPre = document.getElementById("typingLog");

// Keyboard shortcuts
const shortcutsButton = document.getElementById("keyboardShortcutsButton");
const shortcutsModal = document.getElementById("shortcutsModal");
const shortcutsClose = document.querySelector(".shortcuts-close");


// ===== STATE VARIABLES =====

// Quote characters (ground truth)
const characters = quote.split("");

let actionIndex = 0;      // Index in actionList (current action)
let cleanIndex = 0;       // Number of correct characters typed so far
let lastCleanIndex = 0;   // Previous cleanIndex (for diffing spans)
let caretIndex = -1;      // Index of the caret span within spans[]
let isPlaying = false;    // Whether the replay is currently playing
let speedMultiplier = 1;  // Playback speed multiplier
let spans = [];           // <span> elements for each quote character

// Animation timing
let lastFrameTime = null; // Last rAF timestamp
let accumulatedTime = 0;  // Accumulated time toward next action (ms)


// ===== PRECOMPUTED STATS =====

// Cumulative times for each character (normal delays)
const cumulativeTimes = [];
{
    let sum = 0;
    for (let d of delays) {
        sum += d;
        cumulativeTimes.push(sum);
    }
}

// Cumulative times for each character (raw delays)
const cumulativeRawTimes = [];
{
    let rawSum = 0;
    for (let d of rawDelays) {
        rawSum += d;
        cumulativeRawTimes.push(rawSum);
    }
}

// Pre-calculate cumulative timestamp for every action (for O(1) lookup)
{
    let runningTime = 0;
    actionList.forEach(action => {
        runningTime += action.timeDelta;
        action.timestamp = runningTime;
    });
}

// Frame stats for live WPM computation
const startTimeMs = delays[0] || 0;
const startRawTimeMs = rawDelays[0] || 0;

const frameStats = [];
const adjustedFrameStats = [];

for (let i = 0; i <= characters.length; i++) {
    const elapsedSeconds = i > 0 ? cumulativeTimes[i - 1] / 1000 : 0;
    const elapsedRawSeconds = i > 0 ? cumulativeRawTimes[i - 1] / 1000 : 0;

    // Unadjusted WPM
    const wpm = elapsedSeconds > 0 ? (12 * i) / elapsedSeconds : 0;
    const rawWpm = elapsedRawSeconds > 0 ? (12 * i) / elapsedRawSeconds : 0;
    frameStats.push({ elapsedSeconds, wpm, rawWpm });

    // Adjusted WPM
    const adjSeconds = i > 0 ? (cumulativeTimes[i - 1] - startTimeMs) / 1000 : 0;
    const adjRawSeconds = i > 0 ? (cumulativeRawTimes[i - 1] - startRawTimeMs) / 1000 : 0;
    const adjWpm = adjSeconds > 0 ? (12 * Math.max(0, i - 1)) / adjSeconds : 0;
    const adjRawWpm = adjRawSeconds > 0 ? (12 * Math.max(0, i - 1)) / adjRawSeconds : 0;

    adjustedFrameStats.push({
        elapsedSeconds: adjSeconds,
        wpm: adjWpm,
        rawWpm: adjRawWpm
    });
}


// ===== UTILS =====

function getGraphTooltip() {
    let tooltip = document.querySelector(".graph-tooltip");
    if (!tooltip) {
        tooltip = document.createElement("div");
        tooltip.className = "graph-tooltip";
        document.body.appendChild(tooltip);
    }
    return tooltip;
}

function showCopied() {
    const button = copyLogButton;
    if (!button) return;

    button.classList.add("copied");
    setTimeout(() => {
        button.classList.remove("copied");
    }, 1000);
}


// ===== GRAPH RENDERING =====

let segmentCharOffsets = [];

if (typeof graphData !== "undefined" &&
    graphData &&
    Array.isArray(graphData.segments)) {
    let charOffset = 0;
    for (const seg of graphData.segments) {
        segmentCharOffsets.push(charOffset);
        if (typeof seg.text === "string") {
            charOffset += seg.text.length;
        }
    }
}

function renderSpeedGraph() {
    const container = document.getElementById("speedGraph");
    if (!container || !graphData || !Array.isArray(graphData.segments) || graphData.segments.length === 0) return;

    container.innerHTML = "";

    const svgNS = "http://www.w3.org/2000/svg";
    const svgWidth = 400;
    const svgHeight = 260;
    const margin = { top: 30, right: 20, bottom: 45, left: 50 };
    const innerWidth = svgWidth - margin.left - margin.right;
    const innerHeight = svgHeight - margin.top - margin.bottom;

    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", `0 0 ${svgWidth} ${svgHeight}`);
    svg.setAttribute("role", "img");
    container.appendChild(svg);

    const n = graphData.segments.length;
    const ymax = graphData.ymax || Math.max(...graphData.segments.map(s => Math.max(s.wpm, s.raw_wpm)));
    const yticks = (graphData.yticks && graphData.yticks.length)
        ? graphData.yticks
        : [0, 25, 50, 75, 100, 125, 150, 175, 200];

    const xBand = innerWidth / n;

    const plotGroup = document.createElementNS(svgNS, "g");
    plotGroup.setAttribute("transform", `translate(${margin.left},${margin.top})`);
    svg.appendChild(plotGroup);

    // ----- Y grid lines + labels -----
    yticks.forEach(tick => {
        const y = innerHeight - (tick / ymax) * innerHeight;

        const gridLine = document.createElementNS(svgNS, "line");
        gridLine.setAttribute("x1", 0);
        gridLine.setAttribute("y1", y);
        gridLine.setAttribute("x2", innerWidth);
        gridLine.setAttribute("y2", y);
        gridLine.setAttribute("class", "graph-grid");
        plotGroup.appendChild(gridLine);

        const tickLabel = document.createElementNS(svgNS, "text");
        tickLabel.textContent = tick;
        tickLabel.setAttribute("x", -6);
        tickLabel.setAttribute("y", y + 3);
        tickLabel.setAttribute("text-anchor", "end");
        tickLabel.setAttribute("class", "graph-tick-label");
        plotGroup.appendChild(tickLabel);
    });

    // ----- Axes -----
    const yAxis = document.createElementNS(svgNS, "line");
    yAxis.setAttribute("x1", 0);
    yAxis.setAttribute("y1", 0);
    yAxis.setAttribute("x2", 0);
    yAxis.setAttribute("y2", innerHeight);
    yAxis.setAttribute("class", "graph-axis");
    plotGroup.appendChild(yAxis);

    const xAxis = document.createElementNS(svgNS, "line");
    xAxis.setAttribute("x1", 0);
    xAxis.setAttribute("y1", innerHeight);
    xAxis.setAttribute("x2", innerWidth);
    xAxis.setAttribute("y2", innerHeight);
    xAxis.setAttribute("class", "graph-axis");
    plotGroup.appendChild(xAxis);

    // ----- Bars + X ticks -----
    const tooltip = getGraphTooltip();

    graphData.segments.forEach((seg, i) => {
        const centerX = xBand * (i + 0.5);
        const barWidth = xBand * 0.7;

        const rawHeight = (seg.raw_wpm / ymax) * innerHeight;
        const wpmHeight = (seg.wpm / ymax) * innerHeight;

        const rawY = innerHeight - rawHeight;
        const wpmY = innerHeight - wpmHeight;

        const rawBarWidth = barWidth * 0.97;
        const rawBar = document.createElementNS(svgNS, "rect");
        rawBar.setAttribute("x", centerX - rawBarWidth / 2);
        rawBar.setAttribute("y", rawY);
        rawBar.setAttribute("width", rawBarWidth);
        rawBar.setAttribute("height", rawHeight);
        rawBar.setAttribute("class", "graph-bar-raw");
        rawBar.style.cursor = "pointer";
        plotGroup.appendChild(rawBar);

        // WPM bar in front
        const wpmBar = document.createElementNS(svgNS, "rect");
        wpmBar.setAttribute("x", centerX - barWidth / 2);
        wpmBar.setAttribute("y", wpmY);
        wpmBar.setAttribute("width", barWidth);
        wpmBar.setAttribute("height", wpmHeight);
        wpmBar.setAttribute("class", "graph-bar-wpm");
        wpmBar.style.cursor = "pointer";
        plotGroup.appendChild(wpmBar);

        const showTooltip = (evt) => {
            const text = seg.text || "";
            tooltip.innerHTML = `
                <div style="max-width: 260px; white-space: normal;">${text}</div>
                <div>
                    <span class="tooltip-legend tooltip-legend-wpm"></span>
                    WPM: ${seg.wpm.toFixed(2)}
                </div>

                <div>
                    <span class="tooltip-legend tooltip-legend-raw"></span>
                    Raw: ${seg.raw_wpm.toFixed(2)}
                </div>
            `;
            tooltip.style.opacity = "1";
            tooltip.style.left = `${evt.pageX}px`;
            tooltip.style.top = `${evt.pageY - 12}px`;
        };

        const hideTooltip = () => {
            tooltip.style.opacity = "0";
        };

        const handleClick = () => {
            if (segmentCharOffsets[i] != null) {
                seekToChar(segmentCharOffsets[i]);
            }
        };

        // Hover & click bars
        [rawBar, wpmBar].forEach(bar => {
            bar.addEventListener("mouseenter", showTooltip);
            bar.addEventListener("mousemove", showTooltip);
            bar.addEventListener("mouseleave", hideTooltip);
            bar.addEventListener("click", handleClick);
        });

        // X tick line
        const tickLine = document.createElementNS(svgNS, "line");
        tickLine.setAttribute("x1", centerX);
        tickLine.setAttribute("y1", innerHeight);
        tickLine.setAttribute("x2", centerX);
        tickLine.setAttribute("y2", innerHeight + 5);
        tickLine.setAttribute("class", "graph-axis");
        plotGroup.appendChild(tickLine);

        // X tick label (segment number)
        const xLabel = document.createElementNS(svgNS, "text");
        xLabel.textContent = (i + 1).toString();
        xLabel.setAttribute("x", centerX);
        xLabel.setAttribute("y", innerHeight + 18);
        xLabel.setAttribute("text-anchor", "middle");
        xLabel.setAttribute("class", "graph-tick-label");
        plotGroup.appendChild(xLabel);
    });

    // Axis labels
    const yLabel = document.createElementNS(svgNS, "text");
    yLabel.textContent = "WPM";
    yLabel.setAttribute("x", -(innerHeight / 2));
    yLabel.setAttribute("y", -margin.left + 12);
    yLabel.setAttribute("transform", `rotate(-90)`);
    yLabel.setAttribute("text-anchor", "middle");
    yLabel.setAttribute("class", "graph-axis-label");
    plotGroup.appendChild(yLabel);

    const xLabel = document.createElementNS(svgNS, "text");
    xLabel.textContent = "Segment";
    xLabel.setAttribute("x", innerWidth / 2);
    xLabel.setAttribute("y", innerHeight + 35);
    xLabel.setAttribute("text-anchor", "middle");
    xLabel.setAttribute("class", "graph-axis-label");
    plotGroup.appendChild(xLabel);
}


// ===== MISTAKES LIST =====

function generateMistakesList() {
    mistakesList.innerHTML = "";

    const uniqueMistakes = [];
    let currentlyInTypo = false;

    actionList.forEach((action, index) => {
        if (action.typoFlag && !currentlyInTypo) {
            currentlyInTypo = true;
            const displayWord = action.targetWord;

            // Avoid duplicates for the same word
            if (!uniqueMistakes.some(m => m.word === displayWord)) {
                uniqueMistakes.push({
                    word: displayWord,
                    index: index
                });
            }
        } else if (!action.typoFlag) {
            currentlyInTypo = false;
        }
    });

    if (uniqueMistakes.length > 0) {
        mistakesCard.style.display = "block";

        uniqueMistakes.forEach(m => {
            const li = document.createElement("li");
            li.style.cssText = "cursor: pointer; margin-bottom: 5px; transition: color 0.1s;";
            li.innerHTML = `• <span class="typo-link">${m.word}</span>`;
            li.onmouseover = () => li.style.color = "white";
            li.onmouseout = () => li.style.color = "#aaa";
            li.onclick = () => seekToAction(m.index + 1);
            mistakesList.appendChild(li);
        });
    }
}


// ===== REPLAY STATE =====

function resetState() {
    actionIndex = 0;
    cleanIndex = 0;
    lastCleanIndex = 0;
    caretIndex = -1;
    accumulatedTime = 0;
}

function initReplay() {
    // Build spans for each quote character
    replayText.innerHTML = "";
    characters.forEach(ch => {
        const span = document.createElement("span");
        span.textContent = ch;
        span.classList.add("char");
        replayText.appendChild(span);
    });

    // Trailing empty span acts as caret
    const endSpan = document.createElement("span");
    endSpan.classList.add("char", "caret-end");
    endSpan.textContent = "";
    replayText.appendChild(endSpan);

    spans = Array.from(replayText.querySelectorAll(".char"));

    // Raw replay height matches clean replay box
    const replayRect = replayText.getBoundingClientRect();
    const padding = parseInt(window.getComputedStyle(replayText).padding) || 0;
    rawReplayText.setAttribute("style", `height: ${Math.round(replayRect.height - padding * 2)}px`);

    // Restore Adjusted toggle from localStorage
    const savedAdjusted = localStorage.getItem("useAdjustedWPM");
    if (savedAdjusted !== null) {
        adjustedToggle.checked = (savedAdjusted === "true");
    }

    resetState();
    updateDisplay();
    generateMistakesList();
    renderSpeedGraph();
}


// ===== DISPLAY STATE =====

function updateDisplay() {
    let currentInput = "";
    let currentActionTimestamp = 0;
    const isAtEnd = actionIndex >= actionList.length;

    // Use last executed action's input and cumulative timestamp
    if (actionIndex > 0) {
        const currentAction = actionList[Math.min(actionIndex - 1, actionList.length - 1)];
        currentInput = currentAction.input;
        currentActionTimestamp = currentAction.timestamp;
    }

    // ----- Raw replay view with typo highlighting -----
    let firstMismatch = 0;
    while (
        firstMismatch < currentInput.length &&
        firstMismatch < quote.length &&
        currentInput[firstMismatch] === quote[firstMismatch]
    ) {
        firstMismatch++;
    }

    if (firstMismatch < currentInput.length) {
        const correctPart = currentInput.slice(0, firstMismatch);
        const typoPart = currentInput.slice(firstMismatch);

        rawReplayText.innerHTML = "";
        rawReplayText.appendChild(document.createTextNode(correctPart));

        const typoSpan = document.createElement("span");
        typoSpan.className = "typo-highlight";
        typoSpan.textContent = typoPart;
        rawReplayText.appendChild(typoSpan);
    } else {
        rawReplayText.textContent = currentInput;
    }

    // ----- Clean index = length of correct prefix -----
    cleanIndex = firstMismatch;

    // ----- Update green "typed" spans -----
    if (cleanIndex > lastCleanIndex) {
        for (let i = lastCleanIndex; i < cleanIndex; i++) {
            spans[i].classList.add("typed");
        }
    } else if (cleanIndex < lastCleanIndex) {
        for (let i = cleanIndex; i < lastCleanIndex; i++) {
            spans[i].classList.remove("typed");
        }
    }

    // ----- Move caret -----
    if (caretIndex !== cleanIndex) {
        if (caretIndex >= 0 && caretIndex < spans.length) {
            spans[caretIndex].classList.remove("caret");
        }
        if (cleanIndex < spans.length) {
            spans[cleanIndex].classList.add("caret");
        }
        caretIndex = cleanIndex;
    }

    lastCleanIndex = cleanIndex;

    // ----- WPM / Time Stats -----
    const useAdjusted = adjustedToggle.checked;

    // If we're at the end, don't add partial delay to lock final WPM
    const partialDelay = isAtEnd ? 0 : (accumulatedTime * speedMultiplier);
    const totalLogTimeMs = currentActionTimestamp + partialDelay;

    let displayTime = 0;
    let liveWpm = 0;
    let liveRawWpm = 0;
    let flow = 0;

    if (useAdjusted) {
        displayTime = Math.max(0, (totalLogTimeMs - startTimeMs) / 1000);

        if (displayTime > 0) {
            liveWpm = (12 * Math.max(0, cleanIndex - 1)) / displayTime;
        }

        if (cleanIndex < adjustedFrameStats.length) {
            liveRawWpm = adjustedFrameStats[cleanIndex].rawWpm;
        }

        if (displayTime === 0 && caretIndex === 1) {
            liveWpm = Infinity;
            liveRawWpm = Infinity;
        }
    } else {
        displayTime = totalLogTimeMs / 1000;

        if (displayTime > 0) {
            liveWpm = (12 * cleanIndex) / displayTime;
        }

        if (cleanIndex < frameStats.length) {
            liveRawWpm = frameStats[cleanIndex].rawWpm;
        }
    }

    // Calculate flow (raw time for correct chars / cumulative action time)
    if (cleanIndex > 0 && cleanIndex <= cumulativeRawTimes.length) {
        const rawTime = cumulativeRawTimes[cleanIndex - 1];
        const elapsedTime = currentActionTimestamp;
        if (elapsedTime > 0) {
            flow = (rawTime / elapsedTime) * 100;
        }
    }

    stats.innerHTML = `Time: ${displayTime.toFixed(3)}s | WPM: ${liveWpm.toFixed(2)} | Raw: ${liveRawWpm.toFixed(2)} | Flow: ${flow.toFixed(1)}% <span class="flow-help" title="Typing Efficiency&#10;Percentage of total time spent typing correctly">ⓘ</span> |`;
}


// ===== ANIMATION LOOP (requestAnimationFrame) =====

function tick(timestamp) {
    if (!isPlaying) return;

    if (!lastFrameTime) lastFrameTime = timestamp;
    const delta = timestamp - lastFrameTime;
    lastFrameTime = timestamp;

    accumulatedTime += delta;

    // Consume as many actions as fit in accumulatedTime at current speed
    while (actionIndex < actionList.length) {
        const nextDelay = actionList[actionIndex].timeDelta;
        const adjustedDelay = nextDelay / speedMultiplier;

        if (accumulatedTime >= adjustedDelay) {
            accumulatedTime -= adjustedDelay;
            actionIndex++;

            // End-of-log: stop playback, finalize display
            if (actionIndex >= actionList.length) {
                isPlaying = false;
                playPauseButton.textContent = "▶";
                updateDisplay();
                return;
            }
        } else {
            break;
        }
    }

    updateDisplay();
    requestAnimationFrame(tick);
}


// ===== SEEKING HELPERS =====

// Seek to a specific index in the action list
function seekToAction(newIndex) {
    actionIndex = Math.max(0, Math.min(newIndex, actionList.length));
    accumulatedTime = 0;

    updateDisplay();
}

// Seek to the action where the clean prefix reaches target charIndex
function seekToChar(charIndex) {
    if (charIndex == 0) {
        seekToAction(0);
        return;
    }

    let targetActionIndex = 0;

    for (let i = 0; i < actionList.length; i++) {
        const input = actionList[i].input;
        let validLen = 0;

        while (
            validLen < input.length &&
            validLen < quote.length &&
            input[validLen] === quote[validLen]
        ) {
            validLen++;
        }

        if (validLen >= charIndex) {
            targetActionIndex = i + 1;
            break;
        }
    }

    seekToAction(targetActionIndex);
}

// Seek one character backward
function seekBackOneChar() {
    const currentClean = cleanIndex;
    let tempAction = actionIndex;

    while (tempAction > 0) {
        tempAction--;
        const inp = actionList[tempAction > 0 ? tempAction - 1 : 0].input;
        let vLen = 0;
        while (vLen < inp.length && vLen < quote.length && inp[vLen] === quote[vLen]) vLen++;
        if (vLen < currentClean) break;
    }

    while (tempAction > 0 && actionList[tempAction - 1].typoFlag) {
        tempAction -= 1;
    }

    seekToAction(tempAction);
}

// Seek one character forward
function seekForwardOneChar() {
    const currentClean = cleanIndex;
    let tempAction = actionIndex;

    while (tempAction < actionList.length) {
        const inp = actionList[tempAction].input;
        let vLen = 0;
        while (vLen < inp.length && vLen < quote.length && inp[vLen] === quote[vLen]) vLen++;
        tempAction++;
        if (vLen > currentClean) break;
    }

    seekToAction(tempAction);
}


// ===== EVENT HANDLERS =====

// Play / Pause button
playPauseButton.addEventListener("click", () => {
    if (!isPlaying) {
        if (actionIndex >= actionList.length) return;

        isPlaying = true;
        playPauseButton.textContent = "⏸";
        lastFrameTime = null;
        requestAnimationFrame(tick);
    } else {
        isPlaying = false;
        playPauseButton.textContent = "▶";
    }
});

// Playback speed change
speedSelect.addEventListener("change", () => {
    speedMultiplier = parseFloat(speedSelect.value);
});

// Skip to start / end
skipStartButton.addEventListener("click", () => seekToAction(0));
skipEndButton.addEventListener("click", () => seekToAction(actionList.length));

// Jump to peak WPM
function jumpToPeakWpm() {
    const useAdjusted = adjustedToggle.checked;
    const stats = useAdjusted ? adjustedFrameStats : frameStats;

    // Find maximum
    let peakIndex = 0;
    let peakWpm = 0;

    for (let i = 0; i < stats.length; i++) {
        if (stats[i].wpm > peakWpm) {
            peakWpm = stats[i].wpm;
            peakIndex = i;
        }
    }

    seekToChar(peakIndex);
}

// Rewind and forward by 10% of quote length (min 25, max 50 characters)
rewindButton.addEventListener("click", () => {
    const jumpSize = Math.max(25, Math.min(Math.floor(quote.length * 0.1), 50));
    const targetIndex = Math.max(0, cleanIndex - jumpSize);
    seekToChar(targetIndex);
});

forwardButton.addEventListener("click", () => {
    const jumpSize = Math.max(25, Math.min(Math.floor(quote.length * 0.1), 50));
    const targetIndex = Math.min(quote.length, cleanIndex + jumpSize);
    seekToChar(targetIndex);
});

// Raw replay per-action step buttons
if (rawRewindButton) {
    rawRewindButton.addEventListener("click", () => seekToAction(actionIndex - 1));
}
if (rawForwardButton) {
    rawForwardButton.addEventListener("click", () => seekToAction(actionIndex + 1));
}

// Clicking on replay text to seek caret
replayText.addEventListener("click", (e) => {
    if (!e.target.classList.contains("char")) return;

    const clickedSpanIndex = spans.indexOf(e.target);
    const rect = e.target.getBoundingClientRect();
    const clickX = e.clientX - rect.left;

    const targetCharIndex = clickX < rect.width / 2
        ? clickedSpanIndex
        : clickedSpanIndex + 1;

    seekToChar(targetCharIndex);
});

// Typing log show/hide toggle
toggleButton.addEventListener("click", () => {
    const isVisible = logContent.style.display === "block";
    logContent.style.display = isVisible ? "none" : "block";
    toggleButton.textContent = isVisible ? "show" : "hide";
});

// Typing log copy button
copyLogButton.addEventListener("click", () => {
    const text = typingLogPre.textContent || "";
    if (!text) return;

    navigator.clipboard?.writeText(text).then(() => {
        showCopied();
    });
});

// Adjusted WPM toggle (persist preference)
adjustedToggle.addEventListener("change", () => {
    localStorage.setItem("useAdjustedWPM", adjustedToggle.checked);
    updateDisplay();
});

// Keyboard shortcuts modal

shortcutsButton.addEventListener("click", () => {
    shortcutsModal.classList.add("show");
});

shortcutsClose.addEventListener("click", () => {
    shortcutsModal.classList.remove("show");
});

// Close modal when clicking outside of it
shortcutsModal.addEventListener("click", (e) => {
    if (e.target === shortcutsModal) {
        shortcutsModal.classList.remove("show");
    }
});

// Keyboard controls
document.addEventListener("keydown", (e) => {
    // Close modal with Escape key
    if (e.key === "Escape" && shortcutsModal.classList.contains("show")) {
        shortcutsModal.classList.remove("show");
        return;
    }

    // Skip other keyboard shortcuts if modal is open
    if (shortcutsModal.classList.contains("show")) {
        return;
    }

    // Spacebar: play/pause
    if (e.key === " " || e.key === "Spacebar") {
        e.preventDefault();
        playPauseButton.click();
    }
    // Shift + Comma/Period (</>): adjust playback speed
    else if (e.key === "<" || (e.shiftKey && e.key === ",")) {
        e.preventDefault();
        const speeds = [0.25, 0.5, 1, 2];
        const currentIndex = speeds.indexOf(speedMultiplier);
        if (currentIndex > 0) {
            speedSelect.value = speeds[currentIndex - 1];
            speedMultiplier = speeds[currentIndex - 1];
        }
    }
    else if (e.key === ">" || (e.shiftKey && e.key === ".")) {
        e.preventDefault();
        const speeds = [0.25, 0.5, 1, 2];
        const currentIndex = speeds.indexOf(speedMultiplier);
        if (currentIndex < speeds.length - 1) {
            speedSelect.value = speeds[currentIndex + 1];
            speedMultiplier = speeds[currentIndex + 1];
        }
    }
    // Comma/Period: frame step in raw replay
    else if (e.key === ",") {
        e.preventDefault();
        if (rawRewindButton) rawRewindButton.click();
    }
    else if (e.key === ".") {
        e.preventDefault();
        if (rawForwardButton) rawForwardButton.click();
    }
    // Ctrl + Arrow keys: jump by segments
    else if (e.ctrlKey && e.key === "ArrowLeft") {
        e.preventDefault();
        rewindButton.click();
    }
    else if (e.ctrlKey && e.key === "ArrowRight") {
        e.preventDefault();
        forwardButton.click();
    }
    // Arrow keys: step one character
    else if (e.key === "ArrowLeft") {
        e.preventDefault();
        seekBackOneChar();
    }
    else if (e.key === "ArrowRight") {
        e.preventDefault();
        seekForwardOneChar();
    }
    // P: jump to peak WPM
    else if (e.key === "p" || e.key === "P") {
        e.preventDefault();
        jumpToPeakWpm();
    }
});


// ===== ENTRY POINT =====

initReplay();
