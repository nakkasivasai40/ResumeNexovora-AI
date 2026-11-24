document.addEventListener("DOMContentLoaded", () => {
    // Animate circular conic-gradient gauges
    document.querySelectorAll(".gauge-ring[data-score]").forEach((ring) => {
        const score = parseInt(ring.getAttribute("data-score"), 10) || 0;
        const color = ring.getAttribute("data-color") || "#2563eb";
        ring.style.background = `conic-gradient(${color} ${score * 3.6}deg, #e2e8f0 0deg)`;
    });

    // Live dashboard quick search filter
    const quickSearch = document.getElementById("quickSearchInput");
    if (quickSearch) {
        quickSearch.addEventListener("keyup", (e) => {
            if (e.key === "Enter" && quickSearch.value.trim()) {
                window.location.href = `/student/jobs?q=${encodeURIComponent(quickSearch.value.trim())}`;
            }
        });
    }
});
