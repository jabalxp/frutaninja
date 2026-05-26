/**
 * Fruit Ninja Vision AI - Ranking System
 * JavaScript Controller for the Live Leaderboard Dashboard
 */

const FIREBASE_URL = "https://fruitninjavisionai-default-rtdb.firebaseio.com/ranking.json";

// Dom Elements
const podiumEl = document.getElementById("podium");
const tbodyEl = document.getElementById("leaderboard-rows");
const loaderEl = document.getElementById("loader");
const wrapperEl = document.getElementById("leaderboard-wrapper");
const emptyEl = document.getElementById("empty-state");
const refreshBtn = document.getElementById("btn-refresh");

// Tab Navigation Elements
const tabLeaderboard = document.getElementById("tab-leaderboard");
const tabGallery = document.getElementById("tab-gallery");
const viewLeaderboard = document.getElementById("view-leaderboard");
const viewGallery = document.getElementById("view-gallery");

// Gallery Elements
const galleryGridEl = document.getElementById("gallery-grid");
const galleryEmptyEl = document.getElementById("gallery-empty-state");
const galleryRefreshBtn = document.getElementById("btn-gallery-refresh");

let isFetching = false;

/**
 * Fetches rankings from Firebase Realtime Database, sorts them, and updates the UI
 */
async function fetchRanking() {
    if (isFetching) return;
    isFetching = true;
    
    // Rotate the refresh icons during fetch
    const refreshIcon = refreshBtn ? refreshBtn.querySelector(".refresh-icon") : null;
    const galleryRefreshIcon = galleryRefreshBtn ? galleryRefreshBtn.querySelector(".refresh-icon") : null;
    if (refreshIcon) {
        refreshIcon.style.animation = "spin 1s linear infinite";
    }
    if (galleryRefreshIcon) {
        galleryRefreshIcon.style.animation = "spin 1s linear infinite";
    }

    try {
        const response = await fetch(FIREBASE_URL);
        if (!response.ok) throw new Error("Erro de comunicação com o banco de dados");
        
        const data = await response.json();
        
        // Convert Firebase's push object/dictionary of objects into an array
        let players = [];
        if (data) {
            players = Object.keys(data).map(key => {
                return {
                    id: key,
                    name: data[key].name || "Anônimo",
                    score: parseInt(data[key].score) || 0,
                    timestamp: data[key].timestamp || Date.now(),
                    avatar_seed: data[key].avatar_seed || data[key].name || "player",
                    photo_base64: data[key].photo_base64 || ""
                };
            });
        }

        // Sort descending by score, and by timestamp (earlier score is higher rank if tied)
        players.sort((a, b) => {
            if (b.score !== a.score) {
                return b.score - a.score;
            }
            return a.timestamp - b.timestamp;
        });

        renderLeaderboard(players);
        renderGallery(players);
    } catch (error) {
        console.error("Erro ao obter ranking:", error);
        showErrorState();
    } finally {
        isFetching = false;
        if (refreshIcon) {
            refreshIcon.style.animation = "";
        }
        if (galleryRefreshIcon) {
            galleryRefreshIcon.style.animation = "";
        }
    }
}

/**
 * Renders the leaderboard podium and table
 * @param {Array} players Sorted list of players
 */
function renderLeaderboard(players) {
    loaderEl.style.display = "none";
    
    if (players.length === 0) {
        emptyEl.style.display = "block";
        wrapperEl.style.display = "none";
        podiumEl.innerHTML = `
            <div class="podium-placeholder">
                Nenhuma pontuação registrada ainda. Seja o primeiro a jogar e cortar! 🍉
            </div>
        `;
        return;
    }
    
    emptyEl.style.display = "none";
    wrapperEl.style.display = "block";

    // 1. RENDER PODIUM (Top 3 Players)
    const top3 = players.slice(0, 3);
    let podiumHTML = "";
    
    top3.forEach((player, index) => {
        const rank = index + 1;
        
        // Generate a beautiful avatar using Robohash set4 (cats) with unique seeded URL or show captured camera photo
        const avatarUrl = player.photo_base64 
            ? `data:image/jpeg;base64,${player.photo_base64}` 
            : `https://robohash.org/${encodeURIComponent(player.avatar_seed)}.png?set=set4&bgset=bg1`;
        
        // Format date and time beautifully in Portuguese
        const dateObj = new Date(player.timestamp);
        const formattedDate = dateObj.toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "short"
        }) + " - " + dateObj.toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit"
        });
        
        const crownHTML = rank === 1 ? '<span class="crown-icon">👑</span>' : '';
        
        podiumHTML += `
            <div class="podium-card rank-${rank}">
                ${crownHTML}
                <span class="rank-badge">${rank}º</span>
                <div class="avatar-container">
                    <img class="avatar-image" src="${avatarUrl}" alt="${player.name}" onerror="this.src='https://robohash.org/${rank}.png?set=set4'">
                </div>
                <h3>${escapeHTML(player.name)}</h3>
                <div class="podium-score">${player.score}</div>
                <div class="podium-date">${formattedDate}</div>
            </div>
        `;
    });
    podiumEl.innerHTML = podiumHTML;

    // 2. RENDER TABLE (Rank 4+)
    const remaining = players.slice(3);
    let rowsHTML = "";
    
    if (remaining.length === 0) {
        tbodyEl.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    Jogue mais para subir na classificação geral! 🔪
                </td>
            </tr>
        `;
        return;
    }

    remaining.forEach((player, index) => {
        const rank = index + 4;
        const avatarUrl = player.photo_base64 
            ? `data:image/jpeg;base64,${player.photo_base64}` 
            : `https://robohash.org/${encodeURIComponent(player.avatar_seed)}.png?set=set4&bgset=bg1`;
        
        const dateObj = new Date(player.timestamp);
        const formattedDate = dateObj.toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "short"
        }) + " - " + dateObj.toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit"
        });
        
        rowsHTML += `
            <tr style="animation-delay: ${index * 0.04}s">
                <td class="col-rank"><span class="rank-number">${rank}</span></td>
                <td class="col-avatar">
                    <div class="row-avatar-container">
                        <img class="row-avatar-image" src="${avatarUrl}" alt="${player.name}" onerror="this.src='https://robohash.org/${rank}.png?set=set4'">
                    </div>
                </td>
                <td class="col-name">${escapeHTML(player.name)}</td>
                <td class="col-score"><span class="score-highlight">${player.score}</span></td>
                <td class="col-date">${formattedDate}</td>
            </tr>
        `;
    });
    tbodyEl.innerHTML = rowsHTML;
}

/**
 * Shows an elegant error message when fetch fails
 */
function showErrorState() {
    loaderEl.style.display = "none";
    emptyEl.style.display = "none";
    wrapperEl.style.display = "none";
    
    podiumEl.innerHTML = `
        <div class="podium-placeholder" style="border-color: rgba(255, 55, 100, 0.3); background: rgba(255, 55, 100, 0.05);">
            <p style="color: #ff3764; font-weight: 600; font-size: 1.2rem; margin-bottom: 0.5rem;">
                ⚠️ Erro de Conexão
            </p>
            <p style="color: var(--text-muted); font-size: 0.95rem;">
                Não foi possível conectar ao Firebase para carregar o ranking. Verifique sua conexão com a Internet.
            </p>
        </div>
    `;
}

/**
 * Escapes HTML strings to prevent XSS injection attacks
 * @param {string} str Unsanitized string
 * @returns {string} Sanitized string
 */
function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Renders the gallery of large player snapshots and download buttons
 * @param {Array} players Sorted list of players
 */
function renderGallery(players) {
    if (!galleryGridEl) return;

    if (players.length === 0) {
        if (galleryEmptyEl) galleryEmptyEl.style.display = "block";
        galleryGridEl.style.display = "none";
        return;
    }

    if (galleryEmptyEl) galleryEmptyEl.style.display = "none";
    galleryGridEl.style.display = "grid";

    let galleryHTML = "";

    players.forEach((player, index) => {
        const rank = index + 1;
        const hasRealPhoto = !!player.photo_base64;
        
        // Use real base64 player photo or fallback Robohash avatar
        const imgUrl = hasRealPhoto 
            ? `data:image/jpeg;base64,${player.photo_base64}` 
            : `https://robohash.org/${encodeURIComponent(player.avatar_seed)}.png?set=set4&bgset=bg1`;

        // Format date and time
        const dateObj = new Date(player.timestamp);
        const formattedDate = dateObj.toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "short"
        }) + " - " + dateObj.toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit"
        });

        // Unique clean filename for download
        const cleanName = player.name.replace(/[^a-zA-Z0-9]/g, "_");
        const downloadFilename = `Jogador-${cleanName}-${player.score}-pontos.jpg`;

        galleryHTML += `
            <div class="gallery-card" style="animation-delay: ${index * 0.03}s">
                <div class="gallery-photo-container">
                    <span class="gallery-badge">${rank}º LUGAR</span>
                    <img class="gallery-photo" src="${imgUrl}" alt="${player.name}" onerror="this.src='https://robohash.org/${rank}.png?set=set4'">
                    <span class="gallery-score">${player.score} pts</span>
                </div>
                <div class="gallery-info">
                    <span class="gallery-name">${escapeHTML(player.name)}</span>
                    <span class="gallery-date">${formattedDate}</span>
                </div>
                <button class="btn-download" onclick="downloadImage('${hasRealPhoto ? 'data:image/jpeg;base64,' + player.photo_base64 : imgUrl}', '${downloadFilename}')">
                    <svg class="download-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    <span>BAIXAR FOTO</span>
                </button>
            </div>
        `;
    });

    galleryGridEl.innerHTML = galleryHTML;
}

/**
 * Downloads player snapshots or fallback avatars directly by creating a local binary blob
 * @param {string} imgSrc Image source (either base64 data URI or external URL)
 * @param {string} filename Name of the file to save
 */
async function downloadImage(imgSrc, filename) {
    try {
        if (imgSrc.startsWith("data:")) {
            downloadBase64Image(imgSrc, filename);
        } else {
            // Fetch external avatar (Robohash has Access-Control-Allow-Origin: *)
            const response = await fetch(imgSrc);
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(blobUrl);
            }, 150);
        }
    } catch (error) {
        console.error("Erro ao baixar imagem:", error);
        // Fallback: Open the image source in a new tab if downloading is blocked by browser policies
        window.open(imgSrc, "_blank");
    }
}

/**
 * Helper to download raw Base64 data by building a clean local binary Blob object
 * @param {string} base64Data Data URL containing base64 encoded picture
 * @param {string} filename Name of the file to save
 */
function downloadBase64Image(base64Data, filename) {
    let block = base64Data.split(";");
    let contentType = "image/jpeg";
    let realData = base64Data;
    
    if (block.length > 1) {
        contentType = block[0].split(":")[1] || "image/jpeg";
        realData = block[1].split(",")[1];
    }
    
    // Decode base64 bytes to raw character string
    const byteCharacters = atob(realData);
    const sliceSize = 1024;
    const byteArrays = [];
    
    for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
        const slice = byteCharacters.slice(offset, offset + sliceSize);
        
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
    }
    
    const blob = new Blob(byteArrays, { type: contentType });
    const blobUrl = URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
    }, 150);
}

// Event Listeners
if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
        fetchRanking();
    });
}

if (galleryRefreshBtn) {
    galleryRefreshBtn.addEventListener("click", () => {
        fetchRanking();
    });
}

// Tab Switching Event Listeners
if (tabLeaderboard && tabGallery) {
    tabLeaderboard.addEventListener("click", () => {
        tabLeaderboard.classList.add("active");
        tabGallery.classList.remove("active");
        if (viewLeaderboard) viewLeaderboard.style.display = "block";
        if (viewGallery) viewGallery.style.display = "none";
    });

    tabGallery.addEventListener("click", () => {
        tabGallery.classList.add("active");
        tabLeaderboard.classList.remove("active");
        if (viewLeaderboard) viewLeaderboard.style.display = "none";
        if (viewGallery) viewGallery.style.display = "block";
    });
}

// Initial Fetch
fetchRanking();

// Auto Refresh Polling - Fetch every 10 seconds for real-time updates
setInterval(fetchRanking, 10000);
