// Cloud Ultra Downloader - Client Application

let socket = null;
let currentBatchItems = [];
let reconnectTimer = null;

// DOM Elements
const urlInput = document.getElementById("url-input");
const subfolderInput = document.getElementById("subfolder-input");
const btnPaste = document.getElementById("btn-paste");
const btnInspect = document.getElementById("btn-inspect");
const btnDownloadDirect = document.getElementById("btn-download-direct");
const torrentFileInput = document.getElementById("torrent-file-input");
const btnClearHistory = document.getElementById("btn-clear-history");

const statSpeed = document.getElementById("stat-speed");
const statActive = document.getElementById("stat-active");
const statWaiting = document.getElementById("stat-waiting");
const statStopped = document.getElementById("stat-stopped");
const badgeFreeSpace = document.getElementById("badge-free-space");
const statusAriaBadge = document.getElementById("status-aria-badge");
const activeCountBadge = document.getElementById("active-count-badge");
const stoppedCountBadge = document.getElementById("stopped-count-badge");

const activeTasksContainer = document.getElementById("active-tasks-container");
const stoppedTasksContainer = document.getElementById("stopped-tasks-container");

// Modal Elements
const batchModal = document.getElementById("batch-modal");
const modalTitle = document.getElementById("modal-title");
const modalSubtitle = document.getElementById("modal-subtitle");
const batchItemsList = document.getElementById("batch-items-list");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnCancelBatch = document.getElementById("btn-cancel-batch");
const btnSelectAll = document.getElementById("btn-select-all");
const btnDeselectAll = document.getElementById("btn-deselect-all");
const selectedSummary = document.getElementById("selected-summary");
const btnConfirmDownloadBatch = document.getElementById("btn-confirm-download-batch");

// Toast Notification
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    
    const bgClass = type === "success" 
        ? "bg-emerald-950/90 border-emerald-500/50 text-emerald-200" 
        : (type === "error" ? "bg-rose-950/90 border-rose-500/50 text-rose-200" : "bg-indigo-950/90 border-indigo-500/50 text-indigo-200");
    
    const icon = type === "success" ? "✓" : (type === "error" ? "✕" : "ℹ");

    toast.className = `flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-xl text-xs font-semibold ${bgClass} transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto`;
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove("translate-y-2", "opacity-0");
    }, 10);

    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-2");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// WebSocket Connection
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log("WebSocket connected");
        statusAriaBadge.innerHTML = `
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Aria2c متصل</span>
        `;
        statusAriaBadge.className = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateUI(data);
        } catch (e) {
            console.error("Error parsing WS data:", e);
        }
    };

    socket.onclose = () => {
        console.warn("WebSocket closed, attempting reconnect in 2s...");
        statusAriaBadge.innerHTML = `
            <span class="w-2 h-2 rounded-full bg-rose-400"></span>
            <span>جاري إعادة الاتصال...</span>
        `;
        statusAriaBadge.className = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20";
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(connectWebSocket, 2000);
    };

    socket.onerror = (err) => {
        console.error("WebSocket error:", err);
        socket.close();
    };
}

// Update UI with Data
function updateUI(data) {
    if (!data.aria2_alive) {
        statusAriaBadge.innerHTML = `
            <span class="w-2 h-2 rounded-full bg-amber-400"></span>
            <span>Aria2c غير متاح</span>
        `;
        statusAriaBadge.className = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20";
    }

    // Global Stats
    const g = data.global_stat || {};
    statSpeed.textContent = g.downloadSpeed || "0 B/s";
    statActive.textContent = g.numActive || 0;
    statWaiting.textContent = g.numWaiting || 0;
    statStopped.textContent = g.numStopped || 0;

    activeCountBadge.textContent = (data.active || []).length;
    stoppedCountBadge.textContent = (data.stopped || []).length;

    // Storage
    if (data.storage && badgeFreeSpace) {
        badgeFreeSpace.textContent = data.storage.free || "--";
    }

    // Render Active Tasks
    renderActiveTasks(data.active || []);

    // Render Stopped Tasks
    renderStoppedTasks(data.stopped || []);
}

function renderActiveTasks(tasks) {
    if (!tasks || tasks.length === 0) {
        activeTasksContainer.innerHTML = `
            <div class="p-8 rounded-2xl bg-dark-900/30 border border-dashed border-slate-800/80 text-center text-slate-500 text-sm">
                لا توجد تحميلات جارية حالياً. الصق رابطاً في الأعلى وانقر على بدء التحميل!
            </div>
        `;
        return;
    }

    activeTasksContainer.innerHTML = tasks.map(task => {
        const isPaused = task.status === "paused";
        const isError = task.status === "error";

        let statusBadge = `<span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">جاري التحميل</span>`;
        if (isPaused) {
            statusBadge = `<span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">متوقف مؤقتاً</span>`;
        } else if (isError) {
            statusBadge = `<span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">خطأ</span>`;
        }

        return `
            <div class="p-4 sm:p-5 rounded-2xl bg-dark-900/80 border border-slate-800 shadow-lg space-y-3">
                <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2">
                            <span class="text-base">📄</span>
                            <h3 class="text-sm font-bold text-white truncate font-mono" dir="ltr" title="${task.name}">${task.name}</h3>
                        </div>
                        <div class="flex items-center gap-2 mt-1 text-xs text-slate-400">
                            ${statusBadge}
                            <span class="font-mono text-slate-300 font-semibold">${task.completed_formatted} / ${task.total_formatted}</span>
                            <span>•</span>
                            <span class="font-mono text-cyan-400 font-bold">⚡ ${task.download_speed}</span>
                            <span>•</span>
                            <span class="text-slate-400">⏱️ ${task.eta}</span>
                        </div>
                    </div>

                    <!-- Controls -->
                    <div class="flex items-center gap-1.5 shrink-0">
                        ${isPaused 
                            ? `<button onclick="controlTask('unpause', '${task.gid}')" title="استئناف" class="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-400 transition text-xs">▶️</button>`
                            : `<button onclick="controlTask('pause', '${task.gid}')" title="إيقاف مؤقت" class="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-400 transition text-xs">⏸️</button>`
                        }
                        <button onclick="controlTask('remove', '${task.gid}')" title="إلغاء وحذف" class="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-rose-400 transition text-xs">❌</button>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div class="space-y-1">
                    <div class="w-full h-2.5 rounded-full bg-dark-950/80 border border-slate-800 overflow-hidden">
                        <div class="h-full bg-gradient-to-r from-brand-600 via-indigo-500 to-cyan-400 progress-animated transition-all duration-300"
                             style="width: ${task.progress}%"></div>
                    </div>
                    <div class="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                        <span>التقدم: <strong class="text-white">${task.progress}%</strong></span>
                        <span>16 اتصالات نشطة</span>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function renderStoppedTasks(tasks) {
    if (!tasks || tasks.length === 0) {
        stoppedTasksContainer.innerHTML = `
            <div class="p-6 rounded-2xl bg-dark-900/30 border border-slate-800/60 text-center text-slate-500 text-xs">
                لم يكتمل أي ملف بعد في هذه الجلسة.
            </div>
        `;
        return;
    }

    stoppedTasksContainer.innerHTML = tasks.slice(0, 15).map(task => {
        const isComplete = task.status === "complete";
        return `
            <div class="p-3.5 rounded-xl bg-dark-900/60 border border-slate-800/80 flex items-center justify-between gap-3 text-xs">
                <div class="flex items-center gap-3 min-w-0">
                    <span class="text-emerald-400 text-base">${isComplete ? "✅" : "⚠️"}</span>
                    <div class="min-w-0">
                        <div class="font-bold text-white truncate font-mono" dir="ltr">${task.name}</div>
                        <div class="text-[11px] text-slate-400 mt-0.5">
                            الحجم: <span class="font-mono text-slate-300">${task.total_formatted}</span>
                            ${isComplete ? ` • <span class="text-emerald-400">محفوظ في Google Drive</span>` : ` • <span class="text-rose-400">خطأ: ${task.error_message || "توقف"}</span>`}
                        </div>
                    </div>
                </div>
                <button onclick="controlTask('remove_result', '${task.gid}')" title="حذف من السجل" class="text-slate-500 hover:text-rose-400 p-1.5 transition">
                    ✕
                </button>
            </div>
        `;
    }).join("");
}

// Action Handlers
async function controlTask(action, gid) {
    try {
        const res = await fetch("/api/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, gid })
        });
        const data = await res.json();
        if (!data.success) {
            showToast("تعذر تنفيذ العملية: " + (data.error || ""), "error");
        }
    } catch (e) {
        showToast("خطأ في الاتصال بالسيرفر", "error");
    }
}

// Paste from Clipboard
btnPaste.addEventListener("click", async () => {
    try {
        const text = await navigator.clipboard.readText();
        if (text) {
            urlInput.value = text.trim();
            showToast("تم لصق الرابط من الحافظة", "info");
        }
    } catch (err) {
        showToast("يرجى لصق الرابط يدوياً", "info");
    }
});

// Clear Stopped History
btnClearHistory.addEventListener("click", async () => {
    try {
        await fetch("/api/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "clear_stopped" })
        });
        showToast("تم تنظيف سجل التحميلات المكتملة");
    } catch (e) {
        showToast("فشل تنظيف السجل", "error");
    }
});

// Direct Download Button
btnDownloadDirect.addEventListener("click", async () => {
    const url = urlInput.value.trim();
    if (!url) {
        showToast("يرجى إدخال رابط التحميل أولاً", "error");
        return;
    }

    const folder = subfolderInput.value.trim();
    btnDownloadDirect.disabled = true;
    btnDownloadDirect.innerHTML = `<span>⏳ جاري الإضافة...</span>`;

    try {
        const res = await fetch("/api/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ urls: [url], folder })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`🚀 تم بدء التحميل بنجاح (${data.added_count} ملف)!`);
            urlInput.value = "";
        } else {
            showToast("فشل بدء التحميل: " + (data.errors ? data.errors.join(", ") : ""), "error");
        }
    } catch (e) {
        showToast("تعذر الاتصال بالسيرفر", "error");
    } finally {
        btnDownloadDirect.disabled = false;
        btnDownloadDirect.innerHTML = `<span>🚀 بدء التحميل الفوري</span>`;
    }
});

// Allow pressing Enter to download immediately
urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        btnDownloadDirect.click();
    }
});

// Inspect / Batch Modal Handler
btnInspect.addEventListener("click", async () => {
    const url = urlInput.value.trim();
    if (!url) {
        showToast("يرجى إدخال رابط الفحص أولاً", "error");
        return;
    }

    btnInspect.disabled = true;
    btnInspect.innerHTML = `<span>⏳ جاري الفحص...</span>`;

    try {
        const res = await fetch("/api/inspect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });
        const data = await res.json();
        
        if (!data.success) {
            showToast("فشل فحص الرابط: " + (data.error || ""), "error");
            return;
        }

        if (data.type === "batch" && data.items && data.items.length > 0) {
            openBatchModal(data);
        } else {
            // Single item resolved, ask or directly start
            showToast(`تم استخراج الرابط المباشر: ${data.title}`);
            const folder = subfolderInput.value.trim();
            const downloadUrl = (data.items && data.items[0]) ? data.items[0].url : url;
            await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ urls: [downloadUrl], folder })
            });
            urlInput.value = "";
        }
    } catch (e) {
        showToast("خطأ أثناء فحص الرابط", "error");
    } finally {
        btnInspect.disabled = false;
        btnInspect.innerHTML = `<span>🔍 فحص الحلقات (Batch)</span>`;
    }
});

function openBatchModal(data) {
    currentBatchItems = data.items || [];
    modalTitle.textContent = data.title || "قائمة الملفات المكتشفة";
    modalSubtitle.textContent = `تم العثور على ${currentBatchItems.length} ملف عبر ${data.resolver_used || "Scraper"}`;

    batchItemsList.innerHTML = currentBatchItems.map((item, idx) => `
        <div class="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-dark-950/40 transition">
            <label class="flex items-center gap-3 cursor-pointer min-w-0 flex-1">
                <input type="checkbox" data-idx="${idx}" checked class="episode-checkbox w-4 h-4 rounded text-brand-600 focus:ring-brand-500 bg-dark-950 border-slate-700">
                <span class="text-xs text-white font-mono truncate" dir="ltr">${item.name}</span>
            </label>
            <span class="text-[11px] font-mono text-slate-400 shrink-0 ml-3">${item.size_formatted}</span>
        </div>
    `).join("");

    updateBatchSummary();
    batchModal.classList.remove("hidden");

    document.querySelectorAll(".episode-checkbox").forEach(cb => {
        cb.addEventListener("change", updateBatchSummary);
    });
}

function updateBatchSummary() {
    const checked = document.querySelectorAll(".episode-checkbox:checked");
    selectedSummary.textContent = `${checked.length} من أصل ${currentBatchItems.length} محدد`;
    btnConfirmDownloadBatch.textContent = `📥 بدء تحميل الحلقات المحددة (${checked.length})`;
}

btnSelectAll.addEventListener("click", () => {
    document.querySelectorAll(".episode-checkbox").forEach(cb => cb.checked = true);
    updateBatchSummary();
});

btnDeselectAll.addEventListener("click", () => {
    document.querySelectorAll(".episode-checkbox").forEach(cb => cb.checked = false);
    updateBatchSummary();
});

function closeBatchModal() {
    batchModal.classList.add("hidden");
    currentBatchItems = [];
}

btnCloseModal.addEventListener("click", closeBatchModal);
btnCancelBatch.addEventListener("click", closeBatchModal);

// Confirm Batch Download
btnConfirmDownloadBatch.addEventListener("click", async () => {
    const checkedBoxes = document.querySelectorAll(".episode-checkbox:checked");
    const selectedUrls = [];
    checkedBoxes.forEach(cb => {
        const idx = parseInt(cb.getAttribute("data-idx"));
        if (currentBatchItems[idx]) {
            selectedUrls.push(currentBatchItems[idx].url);
        }
    });

    if (selectedUrls.length === 0) {
        showToast("يرجى تحديد حلقة واحدة على الأقل", "error");
        return;
    }

    const folder = subfolderInput.value.trim();
    closeBatchModal();
    showToast(`🚀 جاري جدولة تحميل ${selectedUrls.length} حلقة إلى درايف...`, "info");

    try {
        const res = await fetch("/api/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ urls: selectedUrls, folder })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ تم بدء تحميل ${data.added_count} حلقة بنجاح!`);
            urlInput.value = "";
        } else {
            showToast("فشل إضافة بعض الحلقات", "error");
        }
    } catch (e) {
        showToast("خطأ أثناء إرسال طلب التحميل", "error");
    }
});

// Torrent File Upload Handler
torrentFileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    const folder = subfolderInput.value.trim();
    if (folder) formData.append("folder", folder);

    showToast(`جاري رفع ملف التورنت ${file.name}...`, "info");

    try {
        const res = await fetch("/api/upload-torrent", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ تم بدء تحميل التورنت (${data.filename})!`);
        } else {
            showToast("فشل رفع التورنت: " + (data.error || ""), "error");
        }
    } catch (err) {
        showToast("خطأ في رفع ملف التورنت", "error");
    } finally {
        torrentFileInput.value = "";
    }
});

// Initialize on Load
window.addEventListener("DOMContentLoaded", () => {
    connectWebSocket();
});
