const express = require('express');
const multer = require('multer');
const JSZip = require('jszip');
const fs = require('fs');
const path = require('path');
const { toScratchblocks } = require('parse-sb3-blocks');
const fractch = require('fractch');
const os = require('os');
const crypto = require('crypto');

const app = express();
const port = process.env.PORT || 3000;

// Setup multer for in-memory file uploads
const upload = multer({ storage: multer.memoryStorage() });

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Upload SB3 and decompile to scratchblocks text
app.post('/api/upload', upload.single('sb3File'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        const zip = await JSZip.loadAsync(req.file.buffer);
        const projectJsonFile = zip.file('project.json');

        if (!projectJsonFile) {
            return res.status(400).json({ error: 'Invalid sb3 file: project.json missing' });
        }

        const jsonStr = await projectJsonFile.async('string');
        const project = JSON.parse(jsonStr);

        let scratchblocksText = '';

        for (const target of project.targets) {
            scratchblocksText += `=== ${target.name} ===\n\n`;

            const blocks = target.blocks;
            if (!blocks) continue;

            const startBlocks = Object.keys(blocks).filter(id => blocks[id].topLevel);
            for (const id of startBlocks) {
                try {
                    const sbText = toScratchblocks(id, blocks, 'en');
                    scratchblocksText += sbText + '\n\n';
                } catch (e) {
                    console.error('Error parsing block:', e);
                }
            }
        }

        res.json({ scratchblocks: scratchblocksText });
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: err.message });
    }
});

// Compile fractch code to SB3
app.post('/api/compile', async (req, res) => {
    let tempDir = null;
    try {
        const { sprites = [] } = req.body; // Expect an array of { name: "...", code: "..." }
        if (!sprites || sprites.length === 0) {
            return res.status(400).json({ error: 'No fractch code provided' });
        }

        // Create a temporary directory for the fractch project
        tempDir = path.join(os.tmpdir(), `fractch-${crypto.randomBytes(8).toString('hex')}`);
        fs.mkdirSync(tempDir, { recursive: true });

        // Initialize a new fractch project with empty Stage
        const stageDir = path.join(tempDir, 'Stage');
        fs.mkdirSync(stageDir);
        fs.writeFileSync(path.join(stageDir, 'main.fractch'), 'sprite "Stage";\n');

        // Add user defined sprites
        for (const sprite of sprites) {
            // Sanitize the sprite name to prevent path traversal
            let sanitizedName = sprite.name.replace(/[^a-zA-Z0-9_\- ]/g, '').trim();
            if (!sanitizedName) {
                sanitizedName = 'UnnamedSprite';
            }
            const spriteDir = path.join(tempDir, sanitizedName);
            if (!fs.existsSync(spriteDir)) {
                fs.mkdirSync(spriteDir);
            }
            fs.writeFileSync(path.join(spriteDir, 'main.fractch'), sprite.code);
        }

        // Pack the project to an sb3
        const outSb3 = path.join(tempDir, 'project.sb3');
        await fractch.packSb3({ buildDir: tempDir, outSb3 });

        res.download(outSb3, 'project.sb3', (err) => {
            // Cleanup temp directory after download
            if (tempDir) {
                fs.rmSync(tempDir, { recursive: true, force: true });
            }
            if (err) {
                console.error("Download error:", err);
            }
        });
    } catch (err) {
        console.error(err);
        if (tempDir) {
            try {
                fs.rmSync(tempDir, { recursive: true, force: true });
            } catch(e) {}
        }
        res.status(500).json({ error: err.message });
    }
});

app.listen(port, () => {
    console.log(`Server listening on port ${port}`);
});
