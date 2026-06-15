document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-btn');
    const folderInput = document.getElementById('folder-path');
    const statusContainer = document.getElementById('status-container');
    const statusMessage = document.getElementById('status-message');
    const spinner = document.getElementById('btn-spinner');
    const btnText = document.querySelector('.btn-text');

    generateBtn.addEventListener('click', async () => {
        const folderPath = folderInput.value.trim();

        if (!folderPath) {
            showStatus('Please enter a folder path.', 'error');
            return;
        }

        // UI Loading State
        btnText.style.display = 'none';
        spinner.style.display = 'block';
        generateBtn.disabled = true;
        showStatus('Extracting BOM data... This may take a minute.', '');

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ folder_path: folderPath })
            });

            const data = await response.json();

            if (data.success) {
                showStatus(`Success! Master BOM saved to: ${data.file}`, 'success');
            } else {
                showStatus(`Error: ${data.message}`, 'error');
            }
        } catch (error) {
            showStatus('A network error occurred while connecting to the backend.', 'error');
        } finally {
            // Revert UI Loading State
            btnText.style.display = 'block';
            spinner.style.display = 'none';
            generateBtn.disabled = false;
        }
    });

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusContainer.className = 'status-container'; // Reset
        if (type) {
            statusContainer.classList.add(type);
        }
    }
});
