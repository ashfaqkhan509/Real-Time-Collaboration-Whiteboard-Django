// Main whiteboard application JavaScript

// Import utility functions
// Note: In a real application, you might use ES6 modules or a bundler
// For simplicity, we're assuming util.js is loaded before this file

let canvas, ctx;
let isDrawing = false;
let currentTool = 'pen';
let currentColor = '#000000';
let lineWidth = 3;
let startX, startY;
let currentPath = [];
let websocket;
let boardId;
let username;
let userCanDraw = false; // 👈 NEW FLAG

// User cursor elements
const userCursors = new Map();
const userLabels = new Map();

// DOM Elements
let toolbarButtons;
let colorOptions;
let brushSizeSlider;
let brushSizeValue;
let clearBoardButton;
let usersList;
let activityLog;
let textModal;
let textInput;
let addTextButton;

/**
 * Initialize the whiteboard application
 * @param {number} boardId - The ID of the board to connect to
 */
function initializeWhiteboard(boardIdParam) {
    boardId = boardIdParam;

    const canDrawMeta = document.querySelector('meta[name="can-draw"]');
    if (canDrawMeta) {
        userCanDraw = canDrawMeta.content === "true";
    }
    
    // Get DOM elements
    canvas = document.getElementById('whiteboard-canvas');
    toolbarButtons = document.querySelectorAll('.tool-btn');
    colorOptions = document.querySelectorAll('.color-option');
    brushSizeSlider = document.getElementById('brush-size');
    brushSizeValue = document.getElementById('brush-size-value');
    clearBoardButton = document.getElementById('clear-board');
    usersList = document.getElementById('users-list');
    activityLog = document.getElementById('activity-log');
    textModal = new bootstrap.Modal(document.getElementById('textModal'));
    textInput = document.getElementById('text-input');
    addTextButton = document.getElementById('add-text');
    
    // Set up canvas
    const container = document.getElementById('whiteboard-container');
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    
    ctx = canvas.getContext('2d');
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    // Set up event listeners
    setupEventListeners();
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Handle window resize
    window.addEventListener('resize', resizeCanvas);
}

/**
 * Set up event listeners for the whiteboard
 */
function setupEventListeners() {
    // Toolbar buttons
    toolbarButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons
            toolbarButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            button.classList.add('active');
            // Set current tool
            currentTool = button.dataset.tool;
        });
    });
    
    // Set pen as default active tool
    document.querySelector('.tool-btn[data-tool="pen"]').classList.add('active');
    
    // Color options
    colorOptions.forEach(option => {
        option.addEventListener('click', () => {
            // Remove active class from all options
            colorOptions.forEach(opt => opt.classList.remove('active'));
            // Add active class to clicked option
            option.classList.add('active');
            // Set current color
            currentColor = option.dataset.color;
        });
    });
    
    // Brush size slider
    brushSizeSlider.addEventListener('input', () => {
        lineWidth = parseInt(brushSizeSlider.value);
        brushSizeValue.textContent = lineWidth;
    });
    
    // Clear board button
    clearBoardButton.addEventListener('click', () => {
        if (confirm('Are you sure you want to clear the entire board?')) {
            sendClearBoardAction();
        }
    });
    
    // Canvas events
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseout', stopDrawing);
    
    // Touch events for mobile devices
    canvas.addEventListener('touchstart', handleTouchStart);
    canvas.addEventListener('touchmove', handleTouchMove);
    canvas.addEventListener('touchend', handleTouchEnd);
    
    // Text modal events
    addTextButton.addEventListener('click', addTextToCanvas);
    
    // Request users list
    setTimeout(() => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'request_users'
            }));
        }
    }, 1000);
}

/**
 * Connect to the WebSocket server
 */
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/board/${boardId}/`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function(event) {
        console.log('WebSocket connection established');
        addActivityLog('System', 'Connected to the board');
    };
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === "heartbeat") {
        console.log("✅ Heartbeat received:", data.message);

        // Optional: show it on the page
        let hbDiv = document.getElementById("heartbeat");
        if (!hbDiv) {
            hbDiv = document.createElement("div");
            hbDiv.id = "heartbeat";
            hbDiv.style.position = "fixed";
            hbDiv.style.bottom = "10px";
            hbDiv.style.right = "10px";
            hbDiv.style.background = "#4caf50";
            hbDiv.style.color = "#fff";
            hbDiv.style.padding = "5px 10px";
            hbDiv.style.borderRadius = "5px";
            document.body.appendChild(hbDiv);
        }
        hbDiv.innerText = "❤️ Heartbeat at " + new Date().toLocaleTimeString();
    }
        handleWebSocketMessage(data);
    };
    
    websocket.onclose = function(event) {
        console.log('WebSocket connection closed');
        addActivityLog('System', 'Disconnected from the board');
    };
    
    websocket.onerror = function(error) {
        console.error('WebSocket error:', error);
        addActivityLog('System', 'Connection error occurred');
    };
}

/**
 * Handle incoming WebSocket messages
 * @param {Object} data - The message data
 */
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'board_state':
            loadBoardState(data.state);
            break;
        case 'drawing_action':
            applyRemoteAction(data.action);
            addActivityLog(data.user, getActionDescription(data.action.action_type));
            break;
        case 'user_joined':
            updateOnlineUsers(data.users);
            addActivityLog('System', `${data.user} joined the board`);
            break;
        case 'user_left':
            updateOnlineUsers(data.users);
            addActivityLog('System', `${data.user} left the board`);
            break;
        case 'active_users':
            updateOnlineUsers(data.users);
            break;
        case 'cursor_position':
            updateRemoteCursorPosition(data);
            break;
        case 'heartbeat':
            // Handle heartbeat if needed
            break;
        case 'error':
            alert(`Error: ${data.message}`);
            break;
    }
}

/**
 * Load the initial board state
 * @param {Array} state - Array of drawing actions
 */
function loadBoardState(state) {
    // Clear the canvas first
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Apply each action in order
    state.forEach(action => {
        if (typeof DrawingUtils !== 'undefined') {
            DrawingUtils.applyActionToCanvas(ctx, action, canvas);
        }
    });
}

/**
 * Apply a remote drawing action to the canvas
 * @param {Object} action - The drawing action
 */
function applyRemoteAction(action) {
    if (typeof DrawingUtils !== 'undefined') {
        DrawingUtils.applyActionToCanvas(ctx, action, canvas);
    }
}

/**
 * Send a drawing action to the server
 * @param {string} actionType - Type of action
 * @param {Object} actionData - Action data
 */
function sendDrawingAction(actionType, actionData) {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        const action = {
            type: 'drawing_action',
            action_type: actionType,
            action_data: actionData,
            action_id: DrawingUtils.generateActionId()
        };
        
        websocket.send(JSON.stringify(action));
    }
}

/**
 * Start drawing on the canvas
 * @param {Event} e - Mouse or touch event
 */
function startDrawing(e) {
    if (!userCanDraw) {
        alert("You do not have permission to draw on this board.");
        return;
    }
    if (currentTool === 'text') {
        // For text tool, we'll show a modal to get text input
        const pos = DrawingUtils.getMousePos(canvas, e);
        showTextModal(pos.x, pos.y);
        return;
    }
    
    isDrawing = true;
    const pos = DrawingUtils.getMousePos(canvas, e);
    startX = pos.x;
    startY = pos.y;
    
    if (currentTool === 'pen') {
        currentPath = [{x: pos.x, y: pos.y}];
    }
    
    // Send cursor position
    sendCursorPosition(pos.x, pos.y);
}

/**
 * Draw on the canvas
 * @param {Event} e - Mouse or touch event
 */
function draw(e) {
    if (!isDrawing || !userCanDraw) return;
    
    const pos = DrawingUtils.getMousePos(canvas, e);
    
    switch (currentTool) {
        case 'pen':
            currentPath.push({x: pos.x, y: pos.y});
            ctx.beginPath();
            ctx.moveTo(currentPath[currentPath.length - 2].x, currentPath[currentPath.length - 2].y);
            ctx.lineTo(pos.x, pos.y);
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = lineWidth;
            ctx.stroke();
            break;
        case 'eraser':
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.lineTo(pos.x, pos.y);
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = lineWidth * 2;
            ctx.stroke();
            break;
    }
    
    // Send cursor position
    sendCursorPosition(pos.x, pos.y);
}

/**
 * Stop drawing on the canvas
 * @param {Event} e - Mouse or touch event
 */
function stopDrawing(e) {
    if (!isDrawing || !userCanDraw) return;
    
    isDrawing = false;
    const pos = DrawingUtils.getMousePos(canvas, e);
    
    switch (currentTool) {
        case 'pen':
            // Send the complete path
            sendDrawingAction('draw', {
                points: currentPath,
                color: currentColor,
                lineWidth: lineWidth
            });
            break;
        case 'line':
            // Draw line on canvas
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.lineTo(pos.x, pos.y);
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = lineWidth;
            ctx.stroke();
            
            // Send line action
            sendDrawingAction('line', {
                startX: startX,
                startY: startY,
                endX: pos.x,
                endY: pos.y,
                color: currentColor,
                lineWidth: lineWidth
            });
            break;
        case 'rectangle':
            // Draw rectangle on canvas
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = lineWidth;
            ctx.strokeRect(startX, startY, pos.x - startX, pos.y - startY);
            
            // Send rectangle action
            sendDrawingAction('shape', {
                shapeType: 'rectangle',
                startX: startX,
                startY: startY,
                endX: pos.x,
                endY: pos.y,
                color: currentColor,
                lineWidth: lineWidth
            });
            break;
        case 'circle':
            // Draw circle on canvas
            const radius = Math.sqrt(Math.pow(pos.x - startX, 2) + Math.pow(pos.y - startY, 2));
            ctx.beginPath();
            ctx.arc(startX, startY, radius, 0, 2 * Math.PI);
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = lineWidth;
            ctx.stroke();
            
            // Send circle action
            sendDrawingAction('shape', {
                shapeType: 'circle',
                startX: startX,
                startY: startY,
                endX: pos.x,
                endY: pos.y,
                color: currentColor,
                lineWidth: lineWidth
            });
            break;
        case 'eraser':
            // Send erase action
            sendDrawingAction('erase', {
                startX: startX,
                startY: startY,
                endX: pos.x,
                endY: pos.y,
                lineWidth: lineWidth * 2
            });
            break;
    }
}

/**
 * Handle touch start event
 * @param {TouchEvent} e - Touch event
 */
function handleTouchStart(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const mouseEvent = new MouseEvent('mousedown', {
        clientX: touch.clientX,
        clientY: touch.clientY
    });
    canvas.dispatchEvent(mouseEvent);
}

/**
 * Handle touch move event
 * @param {TouchEvent} e - Touch event
 */
function handleTouchMove(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const mouseEvent = new MouseEvent('mousemove', {
        clientX: touch.clientX,
        clientY: touch.clientY
    });
    canvas.dispatchEvent(mouseEvent);
}

/**
 * Handle touch end event
 * @param {TouchEvent} e - Touch event
 */
function handleTouchEnd(e) {
    e.preventDefault();
    const mouseEvent = new MouseEvent('mouseup', {});
    canvas.dispatchEvent(mouseEvent);
}

/**
 * Show text modal for text input
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 */
function showTextModal(x, y) {
    // Store position for when text is added
    showTextModal.x = x;
    showTextModal.y = y;
    
    // Clear previous text
    textInput.value = '';
    
    // Show modal
    textModal.show();
    
    // Focus on text input
    setTimeout(() => {
        textInput.focus();
    }, 500);
}

/**
 * Add text to canvas from modal input
 */
function addTextToCanvas() {
    const text = textInput.value.trim();
    if (text) {
        // Draw text on canvas
        ctx.font = `${lineWidth * 5}px Arial`;
        ctx.fillStyle = currentColor;
        ctx.fillText(text, showTextModal.x, showTextModal.y);
        
        // Send text action
        sendDrawingAction('text', {
            text: text,
            x: showTextModal.x,
            y: showTextModal.y,
            color: currentColor,
            fontSize: lineWidth * 5
        });
    }
    
    // Hide modal
    textModal.hide();
}

/**
 * Send cursor position to other users
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 */
function sendCursorPosition(x, y) {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({
            type: 'cursor_position',
            x: x,
            y: y
        }));
    }
}

/**
 * Update remote user cursor position
 * @param {Object} data - Cursor position data
 */
function updateRemoteCursorPosition(data) {
    // In a real application, you would update cursor positions here
    // For simplicity, we're not implementing this visualization
}

/**
 * Send clear board action to server
 */
function sendClearBoardAction() {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        const action = {
            type: 'drawing_action',
            action_type: 'clear',
            action_data: { clearAll: true },
            action_id: DrawingUtils.generateActionId()
        };
        
        websocket.send(JSON.stringify(action));
        
        // Clear local canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

/**
 * Update the list of online users
 * @param {Array} users - Array of usernames
 */
function updateOnlineUsers(users) {
    if (!usersList) return;
    
    // Get current username from a meta tag or global variable
    // In a real app, you'd get this from the server or authentication system
    const currentUser = document.querySelector('meta[name="username"]');
    const currentUsername = currentUser ? currentUser.content : 'You';
    
    usersList.innerHTML = '';
    users.forEach(user => {
        const userElement = document.createElement('div');
        userElement.className = 'user-item';
        userElement.textContent = user;
        
        if (user === currentUsername) {
            userElement.classList.add('self');
            userElement.textContent += ' (You)';
        }
        
        usersList.appendChild(userElement);
    });
}

/**
 * Add an entry to the activity log
 * @param {string} user - Username
 * @param {string} action - Action description
 */
function addActivityLog(user, action) {
    if (!activityLog) return;
    
    const activityItem = document.createElement('div');
    activityItem.className = 'activity-item';
    
    const now = new Date();
    const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    activityItem.innerHTML = `
        <span class="activity-time text-muted">${timeString}</span>
        <span class="activity-user">${user}</span>
        <span class="activity-action">${action}</span>
    `;
    
    activityLog.prepend(activityItem);
    
    // Limit activity log to 50 items
    if (activityLog.children.length > 50) {
        activityLog.removeChild(activityLog.lastChild);
    }
}

/**
 * Get a description for an action type
 * @param {string} actionType - Type of action
 * @returns {string} Action description
 */
function getActionDescription(actionType) {
    const descriptions = {
        'draw': 'drew on the board',
        'line': 'drew a line',
        'shape': 'drew a shape',
        'text': 'added text',
        'erase': 'erased part of the board',
        'clear': 'cleared the board'
    };
    
    return descriptions[actionType] || 'performed an action';
}

/**
 * Resize the canvas when the window is resized
 */
function resizeCanvas() {
    const container = document.getElementById('whiteboard-container');
    const newWidth = container.clientWidth;
    const newHeight = container.clientHeight;
    
    // Create a temporary canvas to hold the current drawing
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.drawImage(canvas, 0, 0);
    
    // Resize the main canvas
    canvas.width = newWidth;
    canvas.height = newHeight;
    
    // Redraw the content on the resized canvas
    ctx.drawImage(tempCanvas, 0, 0);
}

// Export for use in other modules (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initializeWhiteboard };
}