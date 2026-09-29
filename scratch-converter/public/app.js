document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const statusDiv = document.getElementById('uploadStatus');
    const fileInput = document.getElementById('sb3File');
    const outputArea = document.getElementById('scratchblocksOutput');

    if (fileInput.files.length === 0) return;

    statusDiv.textContent = 'Uploading and decompiling...';

    const formData = new FormData();
    formData.append('sb3File', fileInput.files[0]);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (response.ok) {
            outputArea.value = data.scratchblocks;
            statusDiv.textContent = 'Decompiled successfully.';
        } else {
            statusDiv.textContent = 'Error: ' + data.error;
        }
    } catch (err) {
        statusDiv.textContent = 'Error: ' + err.message;
    }
});

document.getElementById('renderBtn').addEventListener('click', () => {
    const text = document.getElementById('scratchblocksOutput').value;
    const renderArea = document.getElementById('render-area');
    renderArea.innerHTML = ''; // clear old

    // We split by "=== Target Name ===" so we can render scripts block by block
    // scratchblocks.renderMatching expects DOM elements containing the text.

    const pre = document.createElement('pre');
    pre.className = 'blocks';
    // Remove the === Sprite === headers for rendering
    const codeToRender = text.replace(/===.*?===\n/g, '').trim();
    pre.textContent = codeToRender;

    renderArea.appendChild(pre);

    scratchblocks.renderMatching('.blocks', {
        style: 'scratch3',
        languages: ['en']
    });
});

let spriteCount = 1;

document.getElementById('addSpriteBtn').addEventListener('click', () => {
    spriteCount++;
    const container = document.getElementById('spritesContainer');
    const newSpriteName = `Sprite${spriteCount}`;
    const div = document.createElement('div');
    div.className = 'sprite-editor';
    div.innerHTML = `
        <br>
        <label>Sprite Name: <input type="text" class="sprite-name" value="${newSpriteName}"></label>
        <button class="remove-sprite-btn" style="float: right;">Remove</button>
        <textarea class="sprite-code">sprite "${newSpriteName}";\n\nwhen flag at 0,0 {\n  \n}</textarea>
    `;
    container.appendChild(div);
});

document.getElementById('spritesContainer').addEventListener('click', (e) => {
    if (e.target.classList.contains('remove-sprite-btn')) {
        const editor = e.target.closest('.sprite-editor');
        if (document.querySelectorAll('.sprite-editor').length > 1) {
            editor.remove();
        } else {
            alert('You must have at least one sprite.');
        }
    }
});

document.getElementById('compileBtn').addEventListener('click', async () => {
    const statusDiv = document.getElementById('compileStatus');

    const spriteEditors = document.querySelectorAll('.sprite-editor');
    const sprites = Array.from(spriteEditors).map(editor => {
        return {
            name: editor.querySelector('.sprite-name').value.trim() || 'Sprite1',
            code: editor.querySelector('.sprite-code').value
        };
    });

    statusDiv.textContent = 'Compiling...';

    try {
        const response = await fetch('/api/compile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ sprites })
        });

        if (response.ok) {
            // Trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'project.sb3';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            statusDiv.textContent = 'Compiled and downloaded successfully.';
        } else {
            const data = await response.json();
            statusDiv.textContent = 'Error: ' + data.error;
        }
    } catch (err) {
        statusDiv.textContent = 'Error: ' + err.message;
    }
});
