const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const gameContainer = document.getElementById('game-container');

// UI Elements
const roleDisplay = document.getElementById('player-role');
const blindnessOverlay = document.getElementById('blindness-overlay');
const sneezeOverlay = document.getElementById('sneeze-overlay');
const refluxOverlay = document.getElementById('acid-reflux-overlay');

// Game State
let playerId = null;
let playerRole = null;
let gameState = { players: {}, temporal_ghosts: [] };
let environment = { isRaining: false, isBright: false, nearFlowers: false };

// Local Player State (for smoothing and immediate feedback)
let localPlayer = {
    x: 400, y: 300, vx: 0, vy: 0,
    pupils_dilated: true,
    sneeze_pressure: 0,
    digestion_rhythm: 0,
    temp: 98.6,
    vestibular_balance: 100
};

// WebSocket Setup
const ws = new WebSocket(`ws://${window.location.hostname}:8001`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === 'init') {
        playerId = message.id;
        playerRole = message.role;
        roleDisplay.innerText = `${playerRole.toUpperCase()} (ID: ${playerId})`;
    } else if (message.type === 'state_update') {
        gameState = message.data;
    }
};

// Input Handling
const keys = {};
window.addEventListener('keydown', (e) => keys[e.key.toLowerCase()] = true);
window.addEventListener('keyup', (e) => keys[e.key.toLowerCase()] = false);

// --- BIOLOGICAL MECHANICS ---

function processVestibular() {
    // If we move mouse/look too fast (simulated here by rapid A/D switching)
    if (keys['a'] && keys['d']) {
        localPlayer.vestibular_balance -= 2;
    } else {
        localPlayer.vestibular_balance += 0.5;
    }

    localPlayer.vestibular_balance = Math.max(0, Math.min(100, localPlayer.vestibular_balance));

    if (localPlayer.vestibular_balance < 20) {
        canvas.classList.add('vestibular-flip');
        // Uncontrollable breakdance windmill movement
        localPlayer.vx += (Math.random() - 0.5) * 10;
        localPlayer.vy += (Math.random() - 0.5) * 10;
    } else {
        canvas.classList.remove('vestibular-flip');
    }
}

function processPupils() {
    // Manual Pupillary Dilation
    if (keys['p']) {
        localPlayer.pupils_dilated = false;
        document.getElementById('pupil-status').innerText = 'Constricted';
    } else {
        localPlayer.pupils_dilated = true;
        document.getElementById('pupil-status').innerText = 'Dilated';
    }

    // Step outside into bright light
    if (environment.isBright && localPlayer.pupils_dilated) {
        blindnessOverlay.style.opacity = 1;
    } else {
        blindnessOverlay.style.opacity = 0;
    }
}

function processAllergies() {
    if (environment.nearFlowers) {
        localPlayer.sneeze_pressure += 1;
        document.getElementById('allergy-status').innerText = 'DANGER! Spam F!';

        if (keys['f']) {
            localPlayer.sneeze_pressure -= 5; // Filter pollen
        }

        if (localPlayer.sneeze_pressure > 100) {
            // Sneeze Rocket detonated!
            sneezeOverlay.style.opacity = 1;
            localPlayer.vx = -60; // Rocket backward
            localPlayer.sneeze_pressure = 0;
            setTimeout(() => sneezeOverlay.style.opacity = 0, 1000);
        }
    } else {
        localPlayer.sneeze_pressure = 0;
        document.getElementById('allergy-status').innerText = 'Safe';
    }
}

function processThermoregulation() {
    if (environment.isRaining) {
        localPlayer.temp -= 0.1;
        document.getElementById('temp-status').innerText = 'Freezing! Spam T!';

        if (keys['t']) {
            localPlayer.temp += 0.5; // Shivering generates heat
        }

        if (localPlayer.temp < 95) {
            gameContainer.classList.add('shivering');
        } else {
            gameContainer.classList.remove('shivering');
        }
    } else {
        localPlayer.temp = 98.6;
        document.getElementById('temp-status').innerText = 'Normal';
        gameContainer.classList.remove('shivering');
    }
}

function process4DPhysics() {
    // W-Axis Kicking (Simulated: Spacebar kicks so hard you teleport)
    if (keys[' ']) {
        localPlayer.x += (Math.random() - 0.5) * 400; // Teleport 20 yards away
        localPlayer.y += (Math.random() - 0.5) * 400;
        keys[' '] = false; // Prevent hold
    }
}

function processMovement() {
    // Basic movement if we have the voluntary role, or if testing locally
    if (playerRole === 'voluntary' || playerRole === null) {
        if (keys['w']) localPlayer.vy -= 1;
        if (keys['s']) localPlayer.vy += 1;
        if (keys['a']) localPlayer.vx -= 1;
        if (keys['d']) localPlayer.vx += 1;
    }

    // Friction
    localPlayer.vx *= 0.9;
    localPlayer.vy *= 0.9;

    localPlayer.x += localPlayer.vx;
    localPlayer.y += localPlayer.vy;

    // Boundaries
    if (localPlayer.x < 0) localPlayer.x = 0;
    if (localPlayer.x > canvas.width) localPlayer.x = canvas.width;
    if (localPlayer.y < 0) localPlayer.y = 0;
    if (localPlayer.y > canvas.height) localPlayer.y = canvas.height;
}

// --- RENDERING ---

function drawStickman(x, y, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';

    // Head
    ctx.beginPath();
    ctx.arc(x, y - 40, 15, 0, Math.PI * 2);
    ctx.stroke();

    // Torso
    ctx.beginPath();
    ctx.moveTo(x, y - 25);
    ctx.lineTo(x, y + 20);
    ctx.stroke();

    // Arms
    ctx.beginPath();
    ctx.moveTo(x, y - 10);
    ctx.lineTo(x - 20, y + 10); // Left arm
    ctx.moveTo(x, y - 10);
    ctx.lineTo(x + 20, y + 10); // Right arm
    ctx.stroke();

    // Legs
    ctx.beginPath();
    ctx.moveTo(x, y + 20);
    ctx.lineTo(x - 15, y + 50); // Left leg
    ctx.moveTo(x, y + 20);
    ctx.lineTo(x + 15, y + 50); // Right leg
    ctx.stroke();
}

function drawEnvironment() {
    // Draw some flowers (Allergy trigger zone)
    ctx.fillStyle = 'pink';
    ctx.beginPath();
    ctx.arc(600, 400, 50, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'black';
    ctx.fillText("Allergy Zone", 565, 405);

    // Check if player is near flowers
    const distToFlowers = Math.hypot(localPlayer.x - 600, localPlayer.y - 400);
    environment.nearFlowers = distToFlowers < 70;

    // Simulate Rain/Bright Light zones based on time
    const time = Date.now() / 1000;
    environment.isBright = Math.sin(time * 0.5) > 0; // Sun comes out periodically
    environment.isRaining = Math.sin(time * 0.3) > 0.5; // Rains periodically

    if (environment.isRaining) {
        ctx.fillStyle = 'rgba(0, 0, 255, 0.2)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
}

function updateServer() {
    if (ws.readyState === WebSocket.OPEN && playerId) {
        ws.send(JSON.stringify({
            type: 'player_update',
            data: {
                x: localPlayer.x,
                y: localPlayer.y
            }
        }));
    }
}

// --- GAME LOOP ---
function gameLoop() {
    // Update local state
    processMovement();
    processVestibular();
    processPupils();
    processAllergies();
    processThermoregulation();
    process4DPhysics();

    // Clear Canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    drawEnvironment();

    // Draw Temporal Ghosts
    gameState.temporal_ghosts.forEach(ghost => {
        drawStickman(ghost.x, ghost.y, 'rgba(255, 255, 255, 0.5)'); // Ghostly white
    });

    // Draw all players from server state
    for (const id in gameState.players) {
        const p = gameState.players[id];
        // If it's us, use local coordinates for smoothness, else use server coordinates
        const drawX = (id === playerId) ? localPlayer.x : p.x;
        const drawY = (id === playerId) ? localPlayer.y : p.y;

        drawStickman(drawX, drawY, p.color);

        // Draw player label
        ctx.fillStyle = 'black';
        ctx.fillText(id + (p.role === 'involuntary' ? ' (Brain)' : ' (Muscles)'), drawX - 30, drawY - 60);
    }

    updateServer();
    requestAnimationFrame(gameLoop);
}

// Start loop
gameLoop();