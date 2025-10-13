# 🎓 HOW TO TRAIN YOUR AI QUOTING SYSTEM

## 📤 Upload Training Data

### Method 1: Via API (Recommended)
Send POST request to: `https://lockzone-ai-floorplan.onrender.com/api/upload-learning-data`
```bash
curl -X POST https://lockzone-ai-floorplan.onrender.com/api/upload-learning-data \
  -F "files[]=@floorplan1.pdf" \
  -F "files[]=@floorplan2.pdf" \
  -F "notes=These are bedroom layouts with 3 rooms each"
cd /Users/macbook/Desktop/lockzone-ai-floorplan

cat > templates/index.html << 'ENDOFFILE'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integratd living - Automated Quoting Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #556B2F 0%, #3D4F1F 100%); color: white; padding: 40px; text-align: center; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        
        /* Tab Navigation */
        .tabs { display: flex; background: #f8f9fa; border-bottom: 2px solid #ddd; }
        .tab { flex: 1; padding: 20px; text-align: center; cursor: pointer; font-weight: 600; color: #666; transition: all 0.3s; border-bottom: 3px solid transparent; }
        .tab:hover { background: #e9ecef; }
        .tab.active { color: #556B2F; border-bottom-color: #556B2F; background: white; }
        
        .tab-content { display: none; padding: 40px; }
        .tab-content.active { display: block; }
        
        .content { padding: 0; }
        .upload-section { background: #f8f9fa; border-radius: 15px; padding: 40px; margin-bottom: 30px; border: 2px dashed #556B2F; cursor: pointer; transition: all 0.3s; text-align: center; }
        .upload-section:hover { background: #e9ecef; transform: translateY(-2px); }
        .upload-icon { font-size: 4em; margin-bottom: 20px; }
        input[type="file"] { display: none; }
        .form-group { margin-bottom: 25px; }
        label { display: block; font-weight: 600; color: #556B2F; margin-bottom: 10px; font-size: 1.1em; }
        input[type="text"], textarea { width: 100%; padding: 15px; border: 2px solid #ddd; border-radius: 10px; font-size: 1em; transition: border 0.3s; font-family: inherit; }
        input[type="text"]:focus, textarea:focus { outline: none; border-color: #556B2F; }
        textarea { min-height: 100px; resize: vertical; }
        .tier-selection { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .tier-card { background: #f8f9fa; border: 2px solid #ddd; border-radius: 12px; padding: 20px; cursor: pointer; text-align: center; transition: all 0.3s; }
        .tier-card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .tier-card.selected { background: #556B2F; color: white; border-color: #556B2F; }
        .automation-types { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }
        .checkbox-card { background: #f8f9fa; border: 2px solid #ddd; border-radius: 12px; padding: 20px; cursor: pointer; text-align: center; transition: all 0.3s; }
        .checkbox-card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .checkbox-card.selected { background: #556B2F; color: white; border-color: #556B2F; }
        .checkbox-card .symbol { font-size: 2.5em; margin-bottom: 10px; }
        .checkbox-card .name { font-weight: 600; }
        .analyze-btn, .upload-learning-btn { width: 100%; padding: 20px; background: linear-gradient(135deg, #556B2F 0%, #3D4F1F 100%); color: white; border: none; border-radius: 12px; font-size: 1.2em; font-weight: 600; cursor: pointer; transition: all 0.3s; }
        .analyze-btn:hover, .upload-learning-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(85, 107, 47, 0.3); }
        .analyze-btn:disabled, .upload-learning-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .loading { display: none; text-align: center; padding: 40px; }
        .loading.active { display: block; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #556B2F; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .results { display: none; margin-top: 30px; padding: 30px; background: #f8f9fa; border-radius: 15px; }
        .results.active { display: block; }
        .results h2 { color: #556B2F; margin-bottom: 20px; }
        .result-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .result-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .result-card h3 { color: #556B2F; margin-bottom: 10px; font-size: 1.1em; }
        .result-card p { font-size: 2em; font-weight: 600; color: #333; }
        .download-buttons { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 25px; }
        .download-btn { padding: 15px 25px; background: #556B2F; color: white; text-decoration: none; border-radius: 10px; text-align: center; font-weight: 600; transition: all 0.3s; display: block; }
        .download-btn:hover { background: #3D4F1F; transform: translateY(-2px); }
        .error { display: none; padding: 20px; background: #fee; border: 1px solid #fcc; border-radius: 10px; color: #c33; margin-top: 20px; }
        .error.active { display: block; }
        .success { display: none; padding: 20px; background: #efe; border: 1px solid #cfc; border-radius: 10px; color: #363; margin-top: 20px; }
        .success.active { display: block; }
        
        .file-list { margin-top: 20px; padding: 20px; background: white; border-radius: 10px; }
        .file-item { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .file-item .remove-btn { background: #c33; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer; }
        .file-item .remove-btn:hover { background: #a22; }
        
        .info-box { background: #e7f3ff; border-left: 4px solid #2196F3; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .info-box h3 { color: #2196F3; margin-bottom: 10px; }
        .info-box ul { margin-left: 20px; }
        .info-box li { margin: 8px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Integratd living</h1>
            <p>Automated Quoting Tool with AI Learning</p>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('quote')">📊 Generate Quote</div>
            <div class="tab" onclick="switchTab('learn')">🎓 Train AI</div>
        </div>

        <div class="content">
            <!-- QUOTE TAB -->
            <div id="quote-tab" class="tab-content active">
                <div class="upload-section" onclick="document.getElementById('floorplan').click()">
                    <div class="upload-icon">📄</div>
                    <h2>Upload Floor Plan PDF</h2>
                    <p>Click to select or drag & drop your floor plan</p>
                    <input type="file" id="floorplan" accept=".pdf" onchange="handleFileSelect(this)">
                    <p id="filename" style="margin-top: 15px; font-weight: 600; color: #556B2F;"></p>
                </div>

                <div class="form-group">
                    <label for="project_name">Project Name</label>
                    <input type="text" id="project_name" placeholder="Enter project name..." value="Residential Project">
                </div>

                <div class="form-group">
                    <label>Select Tier</label>
                    <div class="tier-selection">
                        <div class="tier-card selected" data-tier="basic" onclick="selectTier(this, 'basic')">
                            <h3>Basic</h3>
                            <p>Essential automation</p>
                        </div>
                        <div class="tier-card" data-tier="premium" onclick="selectTier(this, 'premium')">
                            <h3>Premium</h3>
                            <p>Advanced features</p>
                        </div>
                        <div class="tier-card" data-tier="deluxe" onclick="selectTier(this, 'deluxe')">
                            <h3>Deluxe</h3>
                            <p>Luxury automation</p>
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label>Select Automation Types</label>
                    <div class="automation-types">
                        <div class="checkbox-card" data-type="lighting" onclick="toggleAutomation(this)">
                            <div class="symbol">💡</div>
                            <div class="name">Lighting Control</div>
                        </div>
                        <div class="checkbox-card" data-type="shading" onclick="toggleAutomation(this)">
                            <div class="symbol">🪟</div>
                            <div class="name">Shading Control</div>
                        </div>
                        <div class="checkbox-card" data-type="security_access" onclick="toggleAutomation(this)">
                            <div class="symbol">🔐</div>
                            <div class="name">Security & Access</div>
                        </div>
                        <div class="checkbox-card" data-type="climate" onclick="toggleAutomation(this)">
                            <div class="symbol">🌡</div>
                            <div class="name">Climate Control</div>
                        </div>
                        <div class="checkbox-card" data-type="audio" onclick="toggleAutomation(this)">
                            <div class="symbol">🔊</div>
                            <div class="name">Audio System</div>
                        </div>
                    </div>
                </div>

                <button class="analyze-btn" onclick="analyzeFloorplan()">
                    🚀 Analyze & Generate Quote
                </button>

                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <h3>Analyzing floor plan...</h3>
                    <p>This may take a moment</p>
                </div>

                <div class="error" id="error"></div>

                <div class="results" id="results">
                    <h2>✅ Analysis Complete!</h2>
                    <div class="result-grid">
                        <div class="result-card">
                            <h3>Rooms Detected</h3>
                            <p id="rooms">0</p>
                        </div>
                        <div class="result-card">
                            <h3>Doors Found</h3>
                            <p id="doors">0</p>
                        </div>
                        <div class="result-card">
                            <h3>Windows Found</h3>
                            <p id="windows">0</p>
                        </div>
                        <div class="result-card">
                            <h3>Total Cost</h3>
                            <p id="total">$0.00</p>
                        </div>
                    </div>
                    <div class="download-buttons">
                        <a href="#" class="download-btn" id="download-annotated">📄 Download Annotated Plan</a>
                        <a href="#" class="download-btn" id="download-quote">💰 Download Quote</a>
                    </div>
                </div>
            </div>

            <!-- LEARNING TAB -->
            <div id="learn-tab" class="tab-content">
                <div class="info-box">
                    <h3>🎯 Help Improve AI Accuracy</h3>
                    <p>Upload floor plans and related documents to train the AI and improve detection accuracy.</p>
                    <ul>
                        <li><strong>Current Room Detection:</strong> ~85%</li>
                        <li><strong>Current Door/Window Detection:</strong> ~80%</li>
                        <li><strong>Goal:</strong> 95%+ accuracy</li>
                    </ul>
                </div>

                <div class="upload-section" onclick="document.getElementById('learning-files').click()">
                    <div class="upload-icon">📚</div>
                    <h2>Upload Training Data</h2>
                    <p>Select multiple floor plans, images, or PDFs</p>
                    <input type="file" id="learning-files" accept=".pdf,.png,.jpg,.jpeg" multiple onchange="handleLearningFiles(this)">
                </div>

                <div id="file-list" class="file-list" style="display: none;">
                    <h3 style="color: #556B2F; margin-bottom: 15px;">Selected Files:</h3>
                    <div id="file-items"></div>
                </div>

                <div class="form-group">
                    <label for="learning-notes">Notes (Optional)</label>
                    <textarea id="learning-notes" placeholder="Add any notes about these files... e.g., 'These are 3-bedroom residential plans' or 'Commercial office layouts with open floor plans'"></textarea>
                </div>

                <button class="upload-learning-btn" onclick="uploadLearningData()" id="upload-learning-btn">
                    📤 Upload Training Data
                </button>

                <div class="loading" id="learning-loading">
                    <div class="spinner"></div>
                    <h3>Uploading training data...</h3>
                    <p>Processing files...</p>
                </div>

                <div class="error" id="learning-error"></div>
                <div class="success" id="learning-success"></div>

                <div class="info-box" style="margin-top: 30px;">
                    <h3>💡 What to Upload</h3>
                    <ul>
                        <li><strong>Floor Plans:</strong> Architectural drawings, blueprints</li>
                        <li><strong>Past Projects:</strong> Completed projects with known room counts</li>
                        <li><strong>Variations:</strong> Different styles, sizes, complexities</li>
                        <li><strong>Annotations:</strong> Plans with marked rooms/doors/windows</li>
                    </ul>
                    <p style="margin-top: 15px;"><strong>The more diverse data you provide, the smarter the AI becomes!</strong></p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Quote tab variables
        let selectedFile = null;
        let selectedTier = 'basic';
        let selectedAutomation = new Set();

        // Learning tab variables
        let learningFiles = [];

        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');
        }

        function handleFileSelect(input) {
            selectedFile = input.files[0];
            document.getElementById('filename').textContent = selectedFile ? `Selected: ${selectedFile.name}` : '';
        }

        function selectTier(element, tier) {
            document.querySelectorAll('.tier-card').forEach(card => card.classList.remove('selected'));
            element.classList.add('selected');
            selectedTier = tier;
        }

        function toggleAutomation(element) {
            const type = element.dataset.type;
            if (element.classList.contains('selected')) {
                element.classList.remove('selected');
                selectedAutomation.delete(type);
            } else {
                element.classList.add('selected');
                selectedAutomation.add(type);
            }
        }

        async function analyzeFloorplan() {
            if (!selectedFile) {
                showError('Please upload a floor plan PDF first');
                return;
            }

            if (selectedAutomation.size === 0) {
                showError('Please select at least one automation type');
                return;
            }

            const formData = new FormData();
            formData.append('floorplan', selectedFile);
            formData.append('project_name', document.getElementById('project_name').value);
            formData.append('tier', selectedTier);
            selectedAutomation.forEach(type => formData.append('automation_types[]', type));

            document.getElementById('loading').classList.add('active');
            document.getElementById('results').classList.remove('active');
            document.getElementById('error').classList.remove('active');
            document.querySelector('.analyze-btn').disabled = true;

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    document.getElementById('rooms').textContent = data.analysis.rooms_detected;
                    document.getElementById('doors').textContent = data.analysis.doors_detected;
                    document.getElementById('windows').textContent = data.analysis.windows_detected;
                    document.getElementById('total').textContent = `$${data.costs.grand_total.toFixed(2)}`;
                    
                    document.getElementById('download-annotated').href = data.files.annotated_pdf;
                    document.getElementById('download-quote').href = data.files.quote_pdf;

                    document.getElementById('results').classList.add('active');
                } else {
                    showError(data.error || 'Analysis failed');
                }
            } catch (error) {
                showError('Network error: ' + error.message);
            } finally {
                document.getElementById('loading').classList.remove('active');
                document.querySelector('.analyze-btn').disabled = false;
            }
        }

        function handleLearningFiles(input) {
            learningFiles = Array.from(input.files);
            displayFileList();
        }

        function displayFileList() {
            const fileList = document.getElementById('file-list');
            const fileItems = document.getElementById('file-items');
            
            if (learningFiles.length === 0) {
                fileList.style.display = 'none';
                return;
            }

            fileList.style.display = 'block';
            fileItems.innerHTML = '';

            learningFiles.forEach((file, index) => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <span>📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)</span>
                    <button class="remove-btn" onclick="removeFile(${index})">Remove</button>
                `;
                fileItems.appendChild(item);
            });
        }

        function removeFile(index) {
            learningFiles.splice(index, 1);
            displayFileList();
        }

        async function uploadLearningData() {
            if (learningFiles.length === 0) {
                showLearningError('Please select at least one file to upload');
                return;
            }

            const formData = new FormData();
            learningFiles.forEach(file => formData.append('files[]', file));
            formData.append('notes', document.getElementById('learning-notes').value);

            document.getElementById('learning-loading').classList.add('active');
            document.getElementById('learning-error').classList.remove('active');
            document.getElementById('learning-success').classList.remove('active');
            document.getElementById('upload-learning-btn').disabled = true;

            try {
                const response = await fetch('/api/upload-learning-data', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    showLearningSuccess(`✅ Successfully uploaded ${learningFiles.length} files! Batch ID: ${data.batch_id}`);
                    
                    // Reset form
                    learningFiles = [];
                    document.getElementById('learning-files').value = '';
                    document.getElementById('learning-notes').value = '';
                    displayFileList();
                } else {
                    showLearningError(data.error || 'Upload failed');
                }
            } catch (error) {
                showLearningError('Network error: ' + error.message);
            } finally {
                document.getElementById('learning-loading').classList.remove('active');
                document.getElementById('upload-learning-btn').disabled = false;
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.classList.add('active');
        }

        function showLearningError(message) {
            const errorDiv = document.getElementById('learning-error');
            errorDiv.textContent = message;
            errorDiv.classList.add('active');
        }

        function showLearningSuccess(message) {
            const successDiv = document.getElementById('learning-success');
            successDiv.textContent = message;
            successDiv.classList.add('active');
        }
    </script>
</body>
</html>
