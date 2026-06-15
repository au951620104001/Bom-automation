document.addEventListener('DOMContentLoaded', () => {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const promptText = document.getElementById('upload-prompt');
    
    const generateBtn = document.getElementById('generate-btn');
    const btnText = document.querySelector('.btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    
    const statusContainer = document.getElementById('status-container');
    const statusMessage = document.getElementById('status-message');
    const statusIcon = document.getElementById('status-icon');

    let selectedFiles = [];

    // --- Drag and Drop Logic ---
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        selectedFiles = Array.from(files);
        if (selectedFiles.length > 0) {
            promptText.style.display = 'none';
            fileList.innerHTML = selectedFiles.map(f => `<div>📄 ${f.name}</div>`).join('');
        } else {
            promptText.style.display = 'block';
            fileList.innerHTML = '';
        }
        
        statusContainer.className = 'status-container';
        statusMessage.textContent = 'Files selected. Ready to extract.';
        statusIcon.textContent = '';
    }

    // --- Upload and Generate Logic ---
    generateBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) {
            showStatus('Please select files to upload.', 'error');
            return;
        }

        // UI Loading State
        generateBtn.disabled = true;
        btnText.style.display = 'none';
        btnSpinner.style.display = 'block';
        showStatus('Uploading and processing files in CATIA V5... Please wait.', '');

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files[]', file);
        });

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showStatus(result.message, 'success');
                
                // Trigger file download automatically
                if(result.download_url) {
                    window.location.href = result.download_url;
                }
                
            } else {
                showStatus(result.message || 'Processing failed.', 'error');
            }
        } catch (error) {
            showStatus('Connection error. Could not reach the server.', 'error');
        } finally {
            // Restore UI
            generateBtn.disabled = false;
            btnText.style.display = 'block';
            btnSpinner.style.display = 'none';
        }
    });

    function showStatus(message, type) {
        statusContainer.className = `status-container ${type}`;
        statusMessage.textContent = message;
        
        if (type === 'success') {
            statusIcon.textContent = '✅';
        } else if (type === 'error') {
            statusIcon.textContent = '❌';
        } else {
            statusIcon.textContent = '⏳';
        }
    }
});
