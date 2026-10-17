class LocalAIClient {
    constructor() {
        this.socket = null;
        this.currentUser = localStorage.getItem('localai_user_id') || ('user_' + Date.now());
        localStorage.setItem('localai_user_id', this.currentUser);
        this.isGenerating = false;
        this.initialize();
    }

    initialize() {
        this.initSocket();
        this.bindEvents();
        this.loadInitialData();
        this.checkSystemStatus();
    }

    async loadInitialData() {
        try {
            await this.loadAvailableModels();
            await this.loadSettings();
            await this.restoreHistory();
        } catch (error) {
            console.error('初始化失败:', error);
        }
    }

    initSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('已连接到服务器');
            this.updateStatus('已连接到服务器');
        });

        this.socket.on('disconnect', () => {
            this.updateStatus('连接已断开');
        });

        this.socket.on('chat_chunk', (data) => {
            this.appendMessageChunk(data.chunk);
            if (data.done) {
                this.isGenerating = false;
                this.enableInput();
            }
        });

        this.socket.on('error', (data) => {
            this.isGenerating = false;
            this.enableInput();
            this.showError(data.message || '发生错误');
        });
    }

    bindEvents() {
        // 标签页切换
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // 聊天发送
        document.getElementById('send-btn').addEventListener('click', () => this.sendMessage());
        document.getElementById('chat-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 停止生成
        const stopBtn = document.getElementById('stop-btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopGeneration());
        }

        // 清空聊天（同步清空后端历史）
        const clearBtn = document.getElementById('clear-chat');
        if (clearBtn) {
            clearBtn.addEventListener('click', async () => {
                document.getElementById('chat-messages').innerHTML = `
                    <div class="message ai-message">
                        <div class="avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="content">
                            对话已清空，有什么可以帮您的吗？
                        </div>
                    </div>
                `;
                try {
                    await fetch(`/api/history/${this.currentUser}`, { method: 'DELETE' });
                } catch (e) {
                    console.warn('清空后端历史失败:', e);
                }
            });
        }

        // 聊天输入框粘贴图片 → 直接视觉分析
        const chatInput = document.getElementById('chat-input');
        chatInput.addEventListener('paste', (e) => {
            const items = e.clipboardData?.items || [];
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    e.preventDefault();
                    const file = item.getAsFile();
                    if (file) {
                        this.handleImageUpload(file, 'vision');
                        this.switchTab('vision');
                        this.showMessage('已粘贴图片，切换到视觉分析', 'info');
                    }
                    return;
                }
            }
        });

        // 视觉分析
        const visionUpload = document.getElementById('vision-upload');
        if (visionUpload) {
            visionUpload.addEventListener('change', (e) => {
                this.handleImageUpload(e.target.files[0], 'vision');
            });
        }

        const analyzeBtn = document.getElementById('analyze-btn');
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => this.analyzeImage());
        }

        // 拖放上传
        const dropArea = document.getElementById('drop-area');
        if (dropArea) {
            dropArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropArea.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
            });

            dropArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                dropArea.style.backgroundColor = 'transparent';
            });

            dropArea.addEventListener('drop', (e) => {
                e.preventDefault();
                dropArea.style.backgroundColor = 'transparent';
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleImageUpload(files[0], 'vision');
                }
            });
        }

        // 系统控制
        document.getElementById('system-control-toggle').addEventListener('change', (e) => {
            this.toggleSystemControl(e.target.checked);
        });

        document.getElementById('enable-system-control').addEventListener('change', (e) => {
            this.toggleSystemControl(e.target.checked);
        });

        // 快速操作按钮
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const app = e.currentTarget.dataset.app;
                if (app === 'screenshot') {
                    this.takeScreenshot();
                } else if (app) {
                    this.executeCommand(app);
                }
            });
        });

        // 命令执行
        document.getElementById('execute-btn').addEventListener('click', () => {
            const command = document.getElementById('command-input').value.trim();
            if (command) {
                this.executeCommand(command);
            }
        });

        document.getElementById('command-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const command = e.target.value.trim();
                if (command) {
                    this.executeCommand(command);
                }
            }
        });

        // 截图
        document.getElementById('screenshot-btn').addEventListener('click', () => this.takeScreenshot());

        // 刷新系统信息
        document.getElementById('refresh-system-info').addEventListener('click', () => this.getSystemInfo());

        // 设置
        document.getElementById('refresh-models').addEventListener('click', () => this.refreshModels());
        document.getElementById('test-connection').addEventListener('click', () => this.testConnection());
        document.getElementById('save-settings').addEventListener('click', () => this.saveSettings());
        document.getElementById('reset-settings').addEventListener('click', () => this.resetSettings());

        // 截图质量滑块
        const qualitySlider = document.getElementById('screenshot-quality');
        const qualityValue = document.getElementById('quality-value');
        qualitySlider.addEventListener('input', (e) => {
            qualityValue.textContent = e.target.value + '%';
        });
    }

    switchTab(tabName) {
        // 更新按钮状态
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 显示对应标签页
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();

        if (!message || this.isGenerating) return;

        // 禁用输入
        this.isGenerating = true;
        this.disableInput();

        // 添加用户消息到界面
        this.appendMessage(message, 'user');
        input.value = '';

        // 获取选择的模型
        const modelSelect = document.getElementById('model-select');
        const model = modelSelect.value;

        // 获取 Agent 模式设置
        const agentModeCheckbox = document.getElementById('enable-agent-mode');
        const useAgent = agentModeCheckbox ? agentModeCheckbox.checked : true;

        // 创建一个新的 AI 消息容器，并记录它的内容区域引用
        const aiMessageDiv = this.createAIMessageContainer();
        this.currentAIResponseContent = aiMessageDiv.querySelector('.content');
        this.currentAIResponseRaw = '';

        // 发送WebSocket消息
        this.socket.emit('chat_message', {
            user_id: this.currentUser,
            message: message,
            model: model,
            use_agent: useAgent
        });
    }

    stopGeneration() {
        // 前端停止：结束当前消息渲染并恢复输入
        this.isGenerating = false;
        this.enableInput();
        if (this.currentAIResponseContent) {
            const loading = this.currentAIResponseContent.querySelector('.loading');
            if (loading) loading.remove();
        }
        this.showMessage('已停止等待回复（后台生成可能仍在进行）', 'info');
    }

    appendMessage(content, type = 'user') {
        const messagesDiv = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        const avatarIcon = type === 'user' ? 'fas fa-user' : 'fas fa-robot';

        messageDiv.innerHTML = `
            <div class="avatar">
                <i class="${avatarIcon}"></i>
            </div>
            <div class="content"></div>
        `;

        const contentDiv = messageDiv.querySelector('.content');
        if (type === 'user') {
            contentDiv.textContent = content;
        } else {
            contentDiv.innerHTML = this.renderMarkdown(content);
        }

        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return messageDiv;
    }

    createAIMessageContainer() {
        const messagesDiv = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai-message';

        messageDiv.innerHTML = `
            <div class="avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="content">
                <span class="loading"></span>
            </div>
        `;

        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        return messageDiv;
    }

    appendMessageChunk(chunk) {
        if (!this.currentAIResponseContent) return;

        const loading = this.currentAIResponseContent.querySelector('.loading');
        if (loading) {
            loading.remove();
        }

        if (chunk) {
            this.currentAIResponseRaw += chunk;
            // 流式过程中用纯文本追加（性能好），完成后统一渲染 Markdown
            const span = document.createElement('span');
            span.textContent = chunk;
            this.currentAIResponseContent.appendChild(span);
        }

        // 自动滚动（仅当用户接近底部时）
        const messagesDiv = document.getElementById('chat-messages');
        const nearBottom = messagesDiv.scrollHeight - messagesDiv.scrollTop - messagesDiv.clientHeight < 100;
        if (nearBottom) {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    }

    finalizeAIMessage() {
        // 流结束后将累积的原始文本渲染为 Markdown
        if (this.currentAIResponseContent && this.currentAIResponseRaw) {
            this.currentAIResponseContent.innerHTML = this.renderMarkdown(this.currentAIResponseRaw);
            this.currentAIResponseRaw = '';
        }
        this.currentAIResponseContent = null;
    }

    /**
     * 轻量级安全 Markdown 渲染（纯前端，无外部依赖）
     * 支持：代码块、行内代码、粗体、斜体、链接、标题、列表
     * 所有内容先转义 HTML 再应用 Markdown 规则，防止 XSS
     */
    renderMarkdown(text) {
        if (!text) return '';
        let html = this.escapeHtml(text);

        // 代码块 ```lang\n...```
        html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre class="code-block"><code>${code}</code></pre>`;
        });

        // 行内代码 `...`
        html = html.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');

        // 粗体 **...**
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // 斜体 *...*
        html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');

        // 链接 [text](url) - 仅允许 http/https
        html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

        // 标题
        html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
        html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^# (.+)$/gm, '<h3>$1</h3>');

        // 无序列表
        html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>[\s\S]*?<\/li>)(?!\s*<li>)/g, '<ul>$1</ul>');

        // 换行
        html = html.replace(/\n/g, '<br>');

        return html;
    }

    async restoreHistory() {
        // 刷新页面后恢复对话历史
        try {
            const response = await fetch(`/api/history/${this.currentUser}`);
            if (!response.ok) return;
            const data = await response.json();
            if (data.history && data.history.length > 0) {
                const messagesDiv = document.getElementById('chat-messages');
                messagesDiv.innerHTML = ''; // 移除默认欢迎消息
                for (const msg of data.history) {
                    if (msg.role === 'user' || msg.role === 'assistant') {
                        this.appendMessage(msg.content, msg.role);
                    }
                }
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        } catch (e) {
            console.warn('恢复对话历史失败:', e);
        }
    }

    async handleImageUpload(file, context) {
        if (!file || !file.type.match('image.*')) {
            this.showError('请选择图片文件');
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            this.showError('图片大小不能超过5MB');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                if (context === 'vision') {
                    this.displayImagePreview(img, file);
                } else {
                    this.sendImageWithMessage(file);
                }
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    displayImagePreview(img, file) {
        const previewDiv = document.getElementById('image-preview');
        previewDiv.innerHTML = '';

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        // 限制预览尺寸
        const maxWidth = 800;
        const maxHeight = 600;
        let width = img.width;
        let height = img.height;

        if (width > height) {
            if (width > maxWidth) {
                height *= maxWidth / width;
                width = maxWidth;
            }
        } else {
            if (height > maxHeight) {
                width *= maxHeight / height;
                height = maxHeight;
            }
        }

        canvas.width = width;
        canvas.height = height;
        ctx.drawImage(img, 0, 0, width, height);

        const imgElement = document.createElement('img');
        imgElement.src = canvas.toDataURL('image/jpeg', 0.8);
        imgElement.style.maxWidth = '100%';
        imgElement.style.maxHeight = '100%';

        previewDiv.appendChild(imgElement);

        // 保存文件引用
        previewDiv.dataset.fileName = file.name;
        previewDiv.dataset.fileType = file.type;
        previewDiv.dataset.fileData = canvas.toDataURL('image/jpeg', 0.8);
    }

    async analyzeImage() {
        const previewDiv = document.getElementById('image-preview');
        const imageData = previewDiv.dataset.fileData;
        const prompt = document.getElementById('analysis-prompt').value;

        if (!imageData || imageData === 'data:,') {
            this.showError('请先上传图片');
            return;
        }

        const analyzeBtn = document.getElementById('analyze-btn');
        const originalText = analyzeBtn.innerHTML;
        analyzeBtn.innerHTML = '<span class="loading"></span> 分析中...';
        analyzeBtn.disabled = true;

        try {
            // 将base64转换为Blob
            const response = await fetch(imageData);
            const blob = await response.blob();

            const formData = new FormData();
            formData.append('image', blob, 'image.jpg');
            formData.append('prompt', prompt);

            const result = await fetch('/api/vision', {
                method: 'POST',
                body: formData
            });

            const data = await result.json();

            if (data.error) {
                this.showError(data.error);
            } else {
                this.displayAnalysisResult(data);
            }
        } catch (error) {
            this.showError('分析失败: ' + error.message);
        } finally {
            analyzeBtn.innerHTML = originalText;
            analyzeBtn.disabled = false;
        }
    }

    displayAnalysisResult(data) {
        const resultDiv = document.getElementById('result-content');
        resultDiv.innerHTML = `
            <div class="result-section">
                <h4><i class="fas fa-align-left"></i> 详细分析</h4>
                <div>${this.renderMarkdown(data.analysis)}</div>
            </div>
            <div class="result-section">
                <h4><i class="fas fa-info-circle"></i> 图片信息</h4>
                <pre>${this.escapeHtml(data.description)}</pre>
            </div>
        `;
    }

    async executeCommand(command) {
        if (!command) return;

        const resultDiv = document.getElementById('command-result');
        resultDiv.innerHTML = '<span class="loading"></span> 执行中...';

        try {
            const response = await fetch('/api/system/command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ command })
            });

            const data = await response.json();

            if (data.error) {
                resultDiv.innerHTML = `<span class="status-error">
                    <i class="fas fa-times-circle"></i> 错误: ${this.escapeHtml(data.error)}
                </span>`;
            } else {
                resultDiv.innerHTML = `
                    <span class="status-success">
                        <i class="fas fa-check-circle"></i> ${this.escapeHtml(data.message || '命令执行成功')}
                    </span>
                    ${data.output ? `<pre>${this.escapeHtml(data.output)}</pre>` : ''}
                `;
            }
        } catch (error) {
            resultDiv.innerHTML = `<span class="status-error">
                <i class="fas fa-times-circle"></i> 请求失败: ${this.escapeHtml(error.message)}
            </span>`;
        }
    }

    async takeScreenshot() {
        try {
            const response = await fetch('/api/system/screenshot');
            const data = await response.json();

            if (data.error) {
                this.showError(data.error);
            } else {
                // 在聊天中显示截图
                const messagesDiv = document.getElementById('chat-messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message user-message';
                messageDiv.innerHTML = `
                    <div class="avatar">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="content">
                        <img src="${data.screenshot}" style="max-width: 300px; border-radius: 8px;" alt="屏幕截图">
                    </div>
                `;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        } catch (error) {
            this.showError('截图失败: ' + error.message);
        }
    }

    async getSystemInfo() {
        const infoDiv = document.getElementById('system-info');
        infoDiv.innerHTML = '<span class="loading"></span> 获取中...';

        try {
            const response = await fetch('/api/system/info');
            const data = await response.json();

            if (data.error) {
                infoDiv.innerHTML = `<span class="status-error">获取失败: ${this.escapeHtml(data.error)}</span>`;
                return;
            }

            // 格式化显示
            const formatBytes = (bytes) => {
                const gb = (bytes / (1024 ** 3)).toFixed(2);
                return gb + ' GB';
            };

            infoDiv.innerHTML = `
                <div class="info-item">
                    <i class="fas fa-microchip"></i> CPU: ${data.cpu.percent.toFixed(1)}% 使用率 (${data.cpu.cores}核)
                </div>
                <div class="info-item">
                    <i class="fas fa-memory"></i> 内存: ${formatBytes(data.memory.used)}/${formatBytes(data.memory.total)} (${data.memory.percent.toFixed(1)}%)
                </div>
                <div class="info-item">
                    <i class="fas fa-hdd"></i> 磁盘: ${formatBytes(data.disk.used)}/${formatBytes(data.disk.total)} (${data.disk.percent.toFixed(1)}%)
                </div>
                <div class="info-item">
                    <i class="fas fa-tasks"></i> 进程: ${data.system.processes} 个
                </div>
            `;
        } catch (error) {
            infoDiv.innerHTML = `<span class="status-error">获取失败: ${this.escapeHtml(error.message)}</span>`;
        }
    }

    async refreshModels() {
        const btn = document.getElementById('refresh-models');
        const originalText = btn.innerHTML;

        try {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 刷新中...';

            await this.loadAvailableModels();

            // 重新设置默认模型
            const response = await fetch('/api/config/safe');
            const config = await response.json();
            const modelSelect = document.getElementById('model-select');
            if (config.ollama.default_model && modelSelect.querySelector(`option[value="${CSS.escape(config.ollama.default_model)}"]`)) {
                modelSelect.value = config.ollama.default_model;
            }

            this.showMessage('模型列表已刷新！', 'success');
        } catch (error) {
            console.error('刷新模型失败:', error);
            this.showMessage('刷新失败，请检查 Ollama 服务是否运行。', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    async testConnection() {
        const testBtn = document.getElementById('test-connection');
        const originalText = testBtn.innerHTML;
        testBtn.innerHTML = '<span class="loading"></span> 测试中...';

        try {
            const response = await fetch('/health');
            const data = await response.json();

            if (data.ollama_connected) {
                this.showMessage('连接测试成功！Ollama服务正常运行。', 'success');
            } else {
                this.showMessage('Ollama服务连接失败，请检查是否已启动。', 'warning');
            }
        } catch (error) {
            this.showMessage('连接测试失败: ' + error.message, 'error');
        } finally {
            testBtn.innerHTML = originalText;
        }
    }

    async checkSystemStatus() {
        const statusDiv = document.getElementById('system-status');

        try {
            const response = await fetch('/health');
            const data = await response.json();

            if (data.ollama_connected) {
                statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> 服务正常运行';
                statusDiv.style.color = '#2ecc71';
            } else {
                statusDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Ollama未连接';
                statusDiv.style.color = '#e74c3c';
            }
        } catch (error) {
            statusDiv.innerHTML = '<i class="fas fa-times-circle"></i> 连接失败';
            statusDiv.style.color = '#e74c3c';
        }
    }

    async loadAvailableModels() {
        try {
            const response = await fetch('/api/models');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            const modelSelect = document.getElementById('model-select');
            if (!modelSelect) {
                console.error('找不到 model-select 元素');
                return;
            }

            modelSelect.innerHTML = ''; // 清空现有选项

            if (data.models && data.models.length > 0) {
                // 为每个模型创建选项
                data.models.forEach(modelName => {
                    const option = document.createElement('option');
                    option.value = modelName;
                    option.textContent = this.formatModelName(modelName);
                    modelSelect.appendChild(option);
                });
            } else {
                // 没有模型时显示提示
                const option = document.createElement('option');
                option.value = '';
                option.textContent = '未找到已安装的模型';
                modelSelect.appendChild(option);

                this.showMessage('未检测到已安装的模型，请运行 install_models.bat 安装模型。', 'warning');
            }
        } catch (error) {
            console.error('加载模型列表失败:', error);

            const modelSelect = document.getElementById('model-select');
            if (modelSelect) {
                modelSelect.innerHTML = '<option value="">加载失败</option>';
            }

            this.showMessage('Ollama服务未启动或连接失败，请确保 Ollama 正在运行。', 'error');
        }
    }

    formatModelName(modelName) {
        // 格式化模型名称为友好的显示名称
        const modelMap = {
            'qwen3:4b': 'Qwen 3 (4B)',
            'qwen3:8b': 'Qwen 3 (8B)',
            'qwen3:14b': 'Qwen 3 (14B)',
            'qwen3-vl:8b': 'Qwen3-VL (视觉)',
            'qwen2.5:7b': 'Qwen 2.5 (7B)',
            'qwen2.5:3b': 'Qwen 2.5 (3B)',
            'qwen2.5:14b': 'Qwen 2.5 (14B)',
            'qwen2-vl:7b': 'Qwen-VL (视觉)',
            'qwen2.5-coder:7b': 'Qwen-Coder (编程)',
            'qwen2.5-coder:14b': 'Qwen-Coder (14B)',
            'llama3.2:1b': 'Llama 3.2 (1B)',
            'llama3.2:3b': 'Llama 3.2 (3B)',
            'llama3.1:8b': 'Llama 3.1 (8B)',
            'llava:7b': 'LLaVA (视觉)',
            'llava:13b': 'LLaVA (13B)',
            'codellama:7b': 'CodeLlama (编程)',
            'deepseek-coder:6.7b': 'DeepSeek-Coder'
        };

        // 如果有映射，返回友好名称，否则返回原名称
        return modelMap[modelName] || modelName;
    }

    async loadSettings() {
        try {
            // 使用后端 API 获取安全配置（/config.json 是 404）
            const response = await fetch('/api/config/safe');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const config = await response.json();

            // 加载设置到表单
            document.getElementById('ollama-url').value = config.ollama.base_url;
            document.getElementById('enable-system-control').checked = config.system.allow_system_control;

            // 加载 Agent 模式设置（默认开启）
            const agentModeCheckbox = document.getElementById('enable-agent-mode');
            if (agentModeCheckbox) {
                agentModeCheckbox.checked = config.system.enable_agent_mode !== false;
            }

            document.getElementById('allowed-commands').value = config.system.allowed_commands.join('\n');
            document.getElementById('screenshot-quality').value = config.system.screenshot_quality;
            document.getElementById('quality-value').textContent = config.system.screenshot_quality + '%';
            document.getElementById('max-file-size').value = config.system.max_file_size / (1024 * 1024);

            // 设置默认模型
            const modelSelect = document.getElementById('model-select');
            if (config.ollama.default_model && modelSelect.querySelector(`option[value="${CSS.escape(config.ollama.default_model)}"]`)) {
                modelSelect.value = config.ollama.default_model;
            }

            // 同步系统控制开关
            document.getElementById('system-control-toggle').checked = config.system.allow_system_control;
        } catch (error) {
            console.error('加载设置失败:', error);
        }
    }

    async saveSettings() {
        const settings = {
            ollama: {
                base_url: document.getElementById('ollama-url').value
            },
            system: {
                allow_system_control: document.getElementById('enable-system-control').checked,
                enable_agent_mode: document.getElementById('enable-agent-mode').checked,
                allowed_commands: document.getElementById('allowed-commands').value.split('\n').map(cmd => cmd.trim()).filter(cmd => cmd),
                screenshot_quality: parseInt(document.getElementById('screenshot-quality').value),
                max_file_size: parseInt(document.getElementById('max-file-size').value) * 1024 * 1024
            }
        };

        try {
            // 保存到后端 config.json（持久化，重启后仍生效）
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            const data = await response.json();

            if (data.success) {
                this.showMessage('设置已保存！', 'success');
            } else {
                this.showMessage('保存失败: ' + (data.error || '未知错误'), 'error');
            }
        } catch (error) {
            this.showMessage('保存失败: ' + error.message, 'error');
        }
    }

    resetSettings() {
        if (confirm('确定要恢复默认设置吗？')) {
            this.loadSettings();
            this.showMessage('设置已恢复默认值', 'success');
        }
    }

    toggleSystemControl(enabled) {
        const controls = document.querySelectorAll('.action-btn, #command-input, #execute-btn, #screenshot-btn');
        controls.forEach(control => {
            if (control.id !== 'screenshot-btn') {
                control.disabled = !enabled;
            }
        });

        // 更新设置表单
        document.getElementById('enable-system-control').checked = enabled;
    }

    disableInput() {
        const input = document.getElementById('chat-input');
        const btn = document.getElementById('send-btn');
        const stopBtn = document.getElementById('stop-btn');
        if (input) input.disabled = true;
        if (btn) btn.disabled = true;
        if (stopBtn) stopBtn.style.display = 'inline-flex';
    }

    enableInput() {
        const input = document.getElementById('chat-input');
        const btn = document.getElementById('send-btn');
        const stopBtn = document.getElementById('stop-btn');
        if (input) {
            input.disabled = false;
            input.focus();
        }
        if (btn) btn.disabled = false;
        if (stopBtn) stopBtn.style.display = 'none';
        // 流结束后渲染最终 Markdown
        this.finalizeAIMessage();
    }

    showMessage(message, type = 'info') {
        const colors = {
            success: '#2ecc71',
            error: '#e74c3c',
            warning: '#f39c12',
            info: '#3498db'
        };

        const messageDiv = document.createElement('div');
        messageDiv.className = 'toast-notification';
        messageDiv.style.background = colors[type] || colors.info;
        messageDiv.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : 'info'}-circle"></i>
            ${this.escapeHtml(message)}
        `;

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.classList.add('toast-out');
            setTimeout(() => messageDiv.remove(), 300);
        }, 3000);
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    updateStatus(message) {
        const statusDiv = document.getElementById('system-status');
        statusDiv.innerHTML = `<i class="fas fa-info-circle"></i> ${this.escapeHtml(message)}`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    sendImageWithMessage(file) {
        // 在聊天中发送图片消息
        this.appendMessage(`[图片: ${file.name}]`, 'user');
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new LocalAIClient();

    // 自动检查系统状态
    setInterval(() => window.app.checkSystemStatus(), 30000);

    // 获取系统信息
    window.app.getSystemInfo();
});
