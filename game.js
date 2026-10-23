const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const gameContainer = document.getElementById('game-container');

// UI Elements
const roleDisplay = document.getElementById('player-role');
const bodyIdDisplay = document.getElementById('body-id');
const blindnessOverlay = document.getElementById('blindness-overlay');
const sneezeOverlay = document.getElementById('sneeze-overlay');
const refluxOverlay = document.getElementById('acid-reflux-overlay');
const passedOutOverlay = document.getElementById('passed-out-overlay');

const voluntaryControls = document.getElementById('voluntary-controls');
const involuntaryControls = document.getElementById('involuntary-controls');

// Game State
let clientId = null;
let bodyId = null;
let playerRole = null;
let gameState = { bodies: {}, ghosts: [], bicycles: [], bullies: [], environment: {} };

// Setup Sliders
const slidersContainer = document.getElementById('sliders-container');
const muscleNames = ["Zygomaticus", "Corrugator", "Frontalis", "Orbicularis Oculi", "Levator Labii", "Depressor Anguli", "Mentalis", "Risorius", "Buccinator", "Masseter", "Procerus", "Platysma"];
for (let i = 0; i < 12; i++) {
    const slider = document.createElement('input');
    slider.type = 'range';
    slider.min = '0';
    slider.max = '100';
    slider.value = '0';
    slider.className = 'muscle-slider';
    slider.id = `muscle-${i}`;
    slidersContainer.appendChild(slider);
}

// Digestion Rhythm State
let rhythmPhase = 0;
let justDigested = false;

// WebSocket Setup
const ws = new WebSocket(`ws://${window.location.hostname}:8001`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === 'init') {
        clientId = message.client_id;
        bodyId = message.body_id;
        playerRole = message.role;
        roleDisplay.innerText = playerRole.toUpperCase();
        bodyIdDisplay.innerText = bodyId;

        if (playerRole === 'voluntary') voluntaryControls.style.display = 'block';
        if (playerRole === 'involuntary') involuntaryControls.style.display = 'block';
    } else if (message.type === 'state_update') {
        gameState = message.data;
    }
};

// Input Handling
const keys = {};
window.addEventListener('keydown', (e) => { keys[e.key.toLowerCase()] = true; });
window.addEventListener('keyup', (e) => { keys[e.key.toLowerCase()] = false; });

// --- BIOLOGICAL MECHANICS (LOCAL PREDICTION & INPUT) ---

function processVoluntary(localBody) {
    // 4D Kick
    if (keys[' ']) {
        localBody.x += (Math.random() - 0.5) * 400;
        localBody.y += (Math.random() - 0.5) * 400;
        keys[' '] = false;
    }

    // Sneeze Filter
    if (gameState.environment.nearFlowers) {
        if (keys['f']) localBody.sneeze_pressure = Math.max(0, localBody.sneeze_pressure - 10);
    }

    // Vestibular (Rapid A/D)
    if (keys['a'] && keys['d']) localBody.vestibular_balance -= 5;
    else localBody.vestibular_balance = Math.min(100, localBody.vestibular_balance + 0.5);

    // Movement (if not on bike)
    if (!localBody.attached_to) {
        if (keys['w']) localBody.vy -= 1;
        if (keys['s']) localBody.vy += 1;
        if (keys['a']) localBody.vx -= 1;
        if (keys['d']) localBody.vx += 1;
    }

    // Read Facial Muscles
    for (let i = 0; i < 12; i++) {
        localBody.face_muscles[i] = parseInt(document.getElementById(`muscle-${i}`).value);
    }

    // Send update
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'voluntary_input',
            data: {
                x: localBody.x, y: localBody.y, vx: localBody.vx, vy: localBody.vy,
                face_muscles: localBody.face_muscles,
                sneeze_pressure: localBody.sneeze_pressure,
                vestibular_balance: localBody.vestibular_balance
            }
        }));
    }
}

function processInvoluntary(localBody) {
    // Heartbeat
    if (keys['h']) {
        localBody.heart_rate += 15; // Pulse increases HR
        keys['h'] = false; // Require distinct pulses
    }
    localBody.heart_rate -= 0.5; // Natural decay
    if (localBody.heart_rate < 0) localBody.heart_rate = 0;

    document.getElementById('heart-rate-display').innerText = Math.floor(localBody.heart_rate);

    // Oxygen
    if (keys['b']) {
        localBody.oxygen = Math.min(100, localBody.oxygen + 5);
    } else {
        localBody.oxygen -= 0.5;
    }
    document.getElementById('oxygen-display').innerText = Math.floor(localBody.oxygen);

    // Pupils
    if (keys['p']) {
        localBody.pupils_dilated = false;
        document.getElementById('pupil-status').innerText = 'Constricted';
    } else {
        localBody.pupils_dilated = true;
        document.getElementById('pupil-status').innerText = 'Dilated';
    }

    // Thermoregulation
    if (gameState.environment.is_raining) {
        localBody.temp -= 0.1;
        document.getElementById('temp-status').innerText = Math.floor(localBody.temp);
        if (keys['t']) localBody.temp += 0.5;
    } else {
        localBody.temp = 98.6;
        document.getElementById('temp-status').innerText = '98.6';
    }

    // Digestion Rhythm Game (Note moves back and forth)
    rhythmPhase += 0.05;
    const noteX = 150 + Math.sin(rhythmPhase) * 140; // Center is 150
    document.getElementById('rhythm-note').style.left = `${noteX}px`;

    if (keys['d']) {
        // Did they hit the center (150 +/- 20)?
        if (Math.abs(noteX - 150) < 20 && !justDigested) {
            localBody.digestion_progress = Math.min(100, localBody.digestion_progress + 10);
            justDigested = true;
        } else if (!justDigested) {
            // Missed! Acid Reflux!
            localBody.digestion_spasm = true;
            localBody.digestion_progress = Math.max(0, localBody.digestion_progress - 20);
            justDigested = true;
        }
    } else {
        justDigested = false;
        localBody.digestion_spasm = false;
    }
    document.getElementById('digestion-progress').innerText = localBody.digestion_progress;


    // Pass out condition
    if (localBody.oxygen < 20 || localBody.heart_rate < 30 || localBody.heart_rate > 180) {
        if (!localBody.is_passed_out) {
            localBody.is_passed_out = true;
            // Spawn temporal ghost
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'temporal_ghost',
                    data: { x: localBody.x, y: localBody.y }
                }));
            }
        }
    } else {
        localBody.is_passed_out = false;
    }

    // Send update
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'involuntary_input',
            data: {
                heart_rate: localBody.heart_rate,
                oxygen: localBody.oxygen,
                temp: localBody.temp,
                digestion_progress: localBody.digestion_progress,
                pupils_dilated: localBody.pupils_dilated,
                is_passed_out: localBody.is_passed_out
            }
        }));
    }
}

// --- RENDERING & PHYSICS ---

function drawStickman(x, y, body) {
    if (body.is_passed_out) {
        ctx.strokeStyle = 'rgba(200, 0, 0, 0.5)'; // Limp and fading
        y += 40; // On the ground
    } else {
        ctx.strokeStyle = '#333';
    }
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';

    // Acid Reflux Spasms
    let spasmX = 0, spasmY = 0;
    if (body.digestion_spasm) {
        spasmX = (Math.random() - 0.5) * 20;
        spasmY = (Math.random() - 0.5) * 20;
    }

    // Head
    ctx.beginPath();
    ctx.arc(x + spasmX, y - 40 + spasmY, 15, 0, Math.PI * 2);
    ctx.stroke();

    // "Facial Emote Wheel" (Abstract representation)
    if (!body.is_passed_out) {
        let smile = (body.face_muscles[0] - 50) / 10; // Zygomaticus
        ctx.beginPath();
        ctx.arc(x + spasmX, y - 40 + spasmY, 8, 0.2, Math.PI - 0.2 + smile);
        ctx.stroke();
    }

    // Torso
    ctx.beginPath();
    ctx.moveTo(x + spasmX, y - 25 + spasmY);
    ctx.lineTo(x, y + 20);
    ctx.stroke();

    // Arms (Flail if vestibular is failing)
    let flail = (100 - body.vestibular_balance) / 5;
    ctx.beginPath();
    ctx.moveTo(x + spasmX, y - 10 + spasmY);
    ctx.lineTo(x - 20 - flail, y + 10 + flail);
    ctx.moveTo(x + spasmX, y - 10 + spasmY);
    ctx.lineTo(x + 20 + flail, y + 10 - flail);
    ctx.stroke();

    // Legs
    ctx.beginPath();
    ctx.moveTo(x, y + 20);
    ctx.lineTo(x - 15, y + 50);
    ctx.moveTo(x, y + 20);
    ctx.lineTo(x + 15, y + 50);
    ctx.stroke();
}

function drawBicycle(bike) {
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 6;

    // Wheels
    ctx.beginPath();
    ctx.arc(bike.x - 30, bike.y + 20, 20, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(bike.x + 30, bike.y + 20, 20, 0, Math.PI * 2);
    ctx.stroke();

    // Frame
    ctx.beginPath();
    ctx.moveTo(bike.x - 30, bike.y + 20);
    ctx.lineTo(bike.x, bike.y - 10);
    ctx.lineTo(bike.x + 30, bike.y + 20);
    ctx.lineTo(bike.x - 10, bike.y + 20);
    ctx.closePath();
    ctx.stroke();
}

function drawBully(bully) {
    ctx.strokeStyle = 'purple';
    ctx.lineWidth = 8; // Thicker lines for bully
    // Draw body
    ctx.beginPath();
    ctx.arc(bully.x, bully.y - 50, 20, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(bully.x, bully.y - 30);
    ctx.lineTo(bully.x, bully.y + 30);
    ctx.stroke();
    // Arms up for atomic wedgie
    ctx.beginPath();
    ctx.moveTo(bully.x, bully.y - 10);
    ctx.lineTo(bully.x - 30, bully.y - 40);
    ctx.moveTo(bully.x, bully.y - 10);
    ctx.lineTo(bully.x + 30, bully.y - 40);
    ctx.stroke();

    ctx.fillStyle = 'red';
    ctx.fillText("BULLY", bully.x - 20, bully.y - 80);
}

function updateEnvironmentLocally() {
    // Check if player is near flowers
    if (gameState.bodies && gameState.bodies[bodyId]) {
        const localBody = gameState.bodies[bodyId];
        const distToFlowers = Math.hypot(localBody.x - 600, localBody.y - 400);
        gameState.environment.nearFlowers = distToFlowers < 70;
    }

    if (gameState.environment.is_raining) {
        ctx.fillStyle = 'rgba(0, 0, 255, 0.2)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
}

// --- MAIN GAME LOOP ---
function gameLoop() {
    if (gameState.bodies && gameState.bodies[bodyId]) {
        const localBody = gameState.bodies[bodyId];

        // Physics logic handled locally for responsiveness
        localBody.vx *= 0.9;
        localBody.vy *= 0.9;
        localBody.x += localBody.vx;
        localBody.y += localBody.vy;

        // Biological state processing
        if (playerRole === 'voluntary') processVoluntary(localBody);
        if (playerRole === 'involuntary') processInvoluntary(localBody);

        // UI Overlays based on state
        if (gameState.environment.is_bright && localBody.pupils_dilated) {
            blindnessOverlay.style.opacity = 1;
        } else {
            blindnessOverlay.style.opacity = 0;
        }

        if (localBody.temp < 95) gameContainer.classList.add('shivering');
        else gameContainer.classList.remove('shivering');

        if (localBody.vestibular_balance < 20) canvas.classList.add('vestibular-flip');
        else canvas.classList.remove('vestibular-flip');

        if (localBody.is_passed_out && playerRole) passedOutOverlay.style.opacity = 1;
        else passedOutOverlay.style.opacity = 0;

        if (localBody.digestion_spasm && playerRole) refluxOverlay.style.opacity = 1;
        else refluxOverlay.style.opacity = 0;
    }

    // Clear Canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    updateEnvironmentLocally();

    // Draw Environment
    ctx.fillStyle = 'pink';
    ctx.beginPath();
    ctx.arc(600, 400, 50, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'black';
    ctx.fillText("Allergy Zone", 565, 405);

    // Draw Temporal Ghosts
    gameState.ghosts.forEach(ghost => {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.beginPath();
        ctx.arc(ghost.x, ghost.y - 40, 15, 0, Math.PI * 2);
        ctx.stroke();
        // ... simple stick for ghosts
        ctx.beginPath();
        ctx.moveTo(ghost.x, ghost.y - 25);
        ctx.lineTo(ghost.x, ghost.y + 20);
        ctx.stroke();
    });

    // Draw Bicycles
    gameState.bicycles.forEach(bike => drawBicycle(bike));

    // Draw Bullies
    gameState.bullies.forEach(bully => drawBully(bully));

    // Draw Players
    for (const id in gameState.bodies) {
        const body = gameState.bodies[id];
        drawStickman(body.x, body.y, body);

        // Labels
        ctx.fillStyle = 'black';
        ctx.fillText(`Body: ${id}`, body.x - 20, body.y - 60);
        let playersText = "";
        if (body.has_voluntary) playersText += "Vol ";
        if (body.has_involuntary) playersText += "Inv ";
        ctx.fillText(`[${playersText}]`, body.x - 20, body.y - 75);
    }

    requestAnimationFrame(gameLoop);
}

// Start loop
gameLoop();
