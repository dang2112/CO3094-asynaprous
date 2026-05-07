// ==========================================
// THÔNG TIN TOÀN CỤC (GLOBAL VARIABLES)
// ==========================================
let myInfo = { username: "", password: "", ip: "", port: "" };
let trackerUrl = "http://127.0.0.1:8000"; // Địa chỉ Server Trung Tâm (Tracker)
let activePeers = {};
let currentChannel = "general";
let selectedPeer = null;
let channelReadCounts = { "general": 0};
let lastChannelForDropdown = "";
let lastMembersCount = 0;
let authToken = null; // For token-based auth
let channelMembers = { "general": []}; // channel -> members
let authHeaders = {};
let lastRenderedChannel = "";
let peerPollHandle = null;
let messagePollHandle = null;

function getAuthHeaders(includeContentType = false) {
    const headers = {};

    if (includeContentType) {
        headers['Content-Type'] = 'application/json';
    }

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    } else if (myInfo.username && myInfo.password) {
        const credentials = btoa(`${myInfo.username}:${myInfo.password}`);
        headers['Authorization'] = `Basic ${credentials}`;
    }

    return headers;
}

function syncChannelTabs(channels) {
    const channelList = document.getElementById("channelList");
    const normalizedChannels = ["general", ...channels.filter(ch => ch !== "general")];

    channelList.querySelectorAll("li").forEach(li => {
        const channelName = li.id.replace("tab-", "");
        if (!normalizedChannels.includes(channelName)) {
            li.remove();
        }
    });

    normalizedChannels.forEach(channelName => {
        if (!document.getElementById(`tab-${channelName}`)) {
            const li = document.createElement("li");
            li.onclick = () => changeChannel(channelName);
            li.id = `tab-${channelName}`;
            li.innerHTML = `<span># ${channelName}</span><span class="unread-badge" id="badge-${channelName}">0</span>`;
            channelList.appendChild(li);
        }

        if (channelReadCounts[channelName] === undefined) {
            channelReadCounts[channelName] = 0;
        }
    });

    if (!normalizedChannels.includes(currentChannel)) {
        currentChannel = "general";
    }

    const items = document.querySelectorAll("#channelList li");
    items.forEach(li => li.classList.remove("active"));

    const activeTab = document.getElementById(`tab-${currentChannel}`);
    if (activeTab) {
        activeTab.classList.add("active");
    }
}

async function deliverMessageToPeer(peerInfo, payload, headers) {
    return fetch(`http://${peerInfo.ip}:${peerInfo.port}/send-peer`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
    });
}

// ==========================================
// 1. GIAI ĐOẠN KHỞI TẠO (ĐĂNG NHẬP)
// ==========================================
async function login() {
    myInfo.username = document.getElementById("username").value.trim();
    myInfo.password = document.getElementById("password").value.trim();
    myInfo.ip = document.getElementById("myIp").value.trim();
    myInfo.port = document.getElementById("myPort").value.trim();

    if (!myInfo.username || !myInfo.password || !myInfo.port) {
        return alert("Vui lòng nhập đủ tên, mật khẩu và cổng!");
    }

    try {
        // Create Basic Auth header
        const credentials = btoa(`${myInfo.username}:${myInfo.password}`);
        const authHeader = `Basic ${credentials}`;

        // Gửi thông tin IP/Port lên Tracker Server (Client-Server Paradigm)
        const response = await fetch(`${trackerUrl}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': authHeader
            },
            body: JSON.stringify({
                username: myInfo.username,
                password: myInfo.password, //trying plaintext password
                ip: myInfo.ip,
                port: myInfo.port
            })
        });

        const result = await response.json();
        if (!response.ok || result.error) {
            return alert(`Đăng nhập thất bại: ${result.error || response.statusText}`);
        }

        authToken = result.token || null; // Store token if provided

        // Set auth headers for future requests
        authHeaders = {
            'Authorization': authToken ? `Bearer ${authToken}` : `Basic ${btoa(`${myInfo.username}:${myInfo.password}`)}`
        };

        document.getElementById("loginModal").style.display = "none";
        document.getElementById("userInfo").innerText = `👤 ${myInfo.username} (Port: ${myInfo.port})`;

        // Show auth type
        updateAuthInfo();

        // Immediately add self to general channel
        if (!channelMembers["general"]) {
            channelMembers["general"] = [];
        }
        if (!channelMembers["general"].includes(myInfo.username)) {
            channelMembers["general"].push(myInfo.username);
        }

        await fetch(`${trackerUrl}/submit-info`, {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: JSON.stringify({
                username: myInfo.username,
                ip: myInfo.ip,
                port: myInfo.port
            })
        });

        updateChannelMembers();

        if (peerPollHandle) clearInterval(peerPollHandle);
        if (messagePollHandle) clearInterval(messagePollHandle);

        peerPollHandle = setInterval(fetchPeers, 3000);    // Mỗi 3s cập nhật danh sách IP 1 lần
        messagePollHandle = setInterval(fetchMessages, 1000); // Mỗi 1s lấy tin nhắn P2P 1 lần
        
        fetchPeers();
        fetchMessages();
    }
    catch (err) {
        alert(err);
    }
}

async function register() {
    myInfo.username = document.getElementById("username").value.trim();
    myInfo.password = document.getElementById("password").value.trim();
    myInfo.ip = document.getElementById("myIp").value.trim();
    myInfo.port = document.getElementById("myPort").value.trim();

    if (!myInfo.username || !myInfo.password || !myInfo.port) {
        return alert("Vui lòng nhập đủ tên, mật khẩu và cổng!");
    }

    try {
        const response = await fetch(`${trackerUrl}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: myInfo.username,
                password: myInfo.password,
                ip: myInfo.ip,
                port: myInfo.port
            })
        });

        const result = await response.json();
        if (!response.ok || result.error) {
            return alert(`Đăng ký thất bại: ${result.error || response.statusText}`);
        }

        alert("Đăng ký thành công! Bây giờ bạn có thể đăng nhập.");
    } catch (err) {
        alert("Lỗi kết nối tới Tracker Server.");
    }
}

async function logout() {
    if (!myInfo.username) return;

    try {
        const headers = {};
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        } else {
            const credentials = btoa(`${myInfo.username}:${myInfo.password}`);
            headers['Authorization'] = `Basic ${credentials}`;
        }

        await fetch(`${trackerUrl}/logout`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ username: myInfo.username })
        });
    } catch (err) {
        console.log("Lỗi khi đăng xuất:", err);
    }

    // Reset state
    myInfo = { username: "", password: "", ip: "", port: "" };
    authToken = null;
    authHeaders = {};
    activePeers = {};
    selectedPeer = null;
    currentChannel = "general";
    channelReadCounts = { "general": 0 };
    channelMembers = { "general": [] };
    lastRenderedChannel = "";
    lastChannelForDropdown = "";
    lastMembersCount = 0;

    if (peerPollHandle) clearInterval(peerPollHandle);
    if (messagePollHandle) clearInterval(messagePollHandle);
    peerPollHandle = null;
    messagePollHandle = null;
    
    // Clear UI
    document.getElementById("loginModal").style.display = "flex";
    document.getElementById("userInfo").innerText = "";
    document.getElementById("messagesBox").innerHTML = "";
    document.getElementById("channelTitle").innerText = "# general";
    document.getElementById("peerList").innerHTML = "";
    document.getElementById("channelMembersList").innerHTML = "";
    document.getElementById("channelList").innerHTML = `
        <li class="active" onclick="changeChannel('general')" id="tab-general">
            <span># general</span>
            <span class="unread-badge" id="badge-general">0</span>
        </li>`;
    document.getElementById("selectedPeerInfo").innerText = "Chưa chọn peer trực tiếp.";
    
    updateAuthInfo();
}

function updateAuthInfo() {
    const authTypeEl = document.getElementById("authType");
    if (authToken) {
        authTypeEl.innerText = "Bearer Token";
    } else if (myInfo.username && myInfo.password) {
        authTypeEl.innerText = "Basic (user:pass)";
    } else {
        authTypeEl.innerText = "None";
    }
}

// ==========================================
// CHANNEL MANAGEMENT
// ==========================================
async function createChannel() {
    const channelName = document.getElementById("newChannelName").value.trim();
    if (!channelName) {
        alert("Vui lòng nhập tên kênh!");
        return;
    }

    const headers = getAuthHeaders(true);

    try {
        const response = await fetch(`${trackerUrl}/create-channel`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                channel_name: channelName,
                creator: myInfo.username,
                members: [myInfo.username] // Creator automatically joins
            })
        });

        if (!response.ok) {
            const error = await response.text();
            return alert(`Tạo kênh thất bại: ${error}`);
        }

        // Add to UI
        channelReadCounts[channelName] = 0;
        channelMembers[channelName] = [myInfo.username];

        const channelList = document.getElementById("channelList");
        const li = document.createElement("li");
        li.onclick = () => changeChannel(channelName);
        li.id = `tab-${channelName}`;
        li.innerHTML = `<span># ${channelName}</span><span class="unread-badge" id="badge-${channelName}">0</span>`;
        channelList.appendChild(li);

        document.getElementById("newChannelName").value = "";
        alert(`Kênh ${channelName} đã được tạo!`);
    } catch (err) {
        alert("Lỗi kết nối tới Tracker Server.");
    }
}

async function addMemberToChannel() {
    const selectedUser = document.getElementById("addMemberSelect").value;
    if (!selectedUser) {
        alert("Vui lòng chọn một peer!");
        return;
    }

    const headers = getAuthHeaders(true);

    try {
        const response = await fetch(`${trackerUrl}/add-list`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                channel: currentChannel,
                username: selectedUser,
                requester: myInfo.username
            })
        });

        if (!response.ok) {
            const error = await response.text();
            return alert(`Thêm thành viên thất bại: ${error}`);
        }

        // Update local member list
        if (!channelMembers[currentChannel]) {
            channelMembers[currentChannel] = [];
        }
        if (!channelMembers[currentChannel].includes(selectedUser)) {
            channelMembers[currentChannel].push(selectedUser);
        }

        updateChannelMembers();
        alert(`${selectedUser} đã được thêm vào kênh ${currentChannel}!`);
        
        // Refresh channels to update dropdown
        setTimeout(refreshChannels, 500);
    } catch (err) {
        alert("Lỗi kết nối tới Tracker Server.");
    }
}

async function refreshChannels() {
    await fetchChannels();
}

function updateChannelMembers() {
    const membersList = document.getElementById("channelMembersList");
    const memberSelect = document.getElementById("addMemberSelect");

    // Update members list
    membersList.innerHTML = "";
    const members = channelMembers[currentChannel] || [];
    members.forEach(member => {
        const li = document.createElement("li");
        li.textContent = member;
        if (member === myInfo.username) {
            li.style.fontWeight = "bold";
            li.textContent += " (Bạn)";
        }
        membersList.appendChild(li);
    });

    // Update dropdown if channel changed or member count changed
    if (lastChannelForDropdown !== currentChannel || lastMembersCount !== members.length || memberSelect.options.length <= 1) {
        memberSelect.innerHTML = '<option value="">Chọn peer để thêm...</option>';
        for (const [user, info] of Object.entries(activePeers)) {
            if (!members.includes(user)) {
                const option = document.createElement("option");
                option.value = user;
                option.textContent = `${user} (${info.ip}:${info.port})`;
                memberSelect.appendChild(option);
            }
        }
        lastChannelForDropdown = currentChannel;
        lastMembersCount = members.length;
    }
}

// ==========================================
// 2. ĐỒNG BỘ MẠNG (POLLING LẤY IP VÀ TIN NHẮN)
// ==========================================
async function fetchPeers() {
    try {
        // Lấy danh sách Peer từ Tracker
        const res = await fetch(`${trackerUrl}/get-list`, { headers: getAuthHeaders(true) });
        activePeers = await res.json();
        
        // Cập nhật UI menu bên trái
        const list = document.getElementById("peerList");
        list.innerHTML = "";
        for (const [user, info] of Object.entries(activePeers)) {
            const isSelf = user === myInfo.username;
            const itemClass = isSelf ? 'self-peer' : 'peer-item';
            const displayName = isSelf ? `${user} (Bạn)` : `${user} (${info.ip}:${info.port})`;
            const clickAttr = isSelf ? '' : `onclick="selectPeer('${user}')"`;
            list.innerHTML += `<li class="${itemClass}" ${clickAttr} id="peer-${user}">${displayName}</li>`;
        }
        updateSelectedPeerInfo();
        // Fetch channel information
        await fetchChannels();    } catch(e) {
        console.log("Đang mất kết nối với Tracker...");
    }
}

async function fetchChannels() {
    try {
        const res = await fetch(`${trackerUrl}/get-channels`, { headers: getAuthHeaders(true) });
        const channelData = await res.json();

        // Update channel members
        if (channelData.error) {
            console.warn("Tracker returned channel error:", channelData.error);
            channelMembers = {};
        } else {
            channelMembers = channelData.members || {};
        }

        // If general membership is missing or empty, use active peers from tracker
        if (!Array.isArray(channelMembers["general"]) || channelMembers["general"].length === 0) {
            channelMembers["general"] = Object.keys(activePeers);
        }

        // Ensure current user is always present in general
        if (!channelMembers["general"].includes(myInfo.username)) {
            channelMembers["general"].push(myInfo.username);
        }

        syncChannelTabs(channelData.channels || ["general"]);
        updateChannelMembers();
    } catch(e) {
        console.log("Lỗi khi lấy thông tin kênh...");
    }
}

async function fetchMessages() {
    try {
        const res = await fetch(`http://127.0.0.1:${myInfo.port}/get-messages`, { headers: getAuthHeaders() });
        const channelsData = await res.json();
        
        if (!channelsData || typeof channelsData !== 'object') {
            return;
        }

        if (!(currentChannel in channelsData)) {
            channelsData[currentChannel] = [];
        }

        let hasNewMsgInActiveChannel = false;
        
        let forceRender = (lastRenderedChannel !== currentChannel); 

        for (const [chName, messages] of Object.entries(channelsData)) {
            if (channelReadCounts[chName] === undefined) channelReadCounts[chName] = 0;

            const totalMsgs = messages.length;
            const unread = totalMsgs - channelReadCounts[chName];

            if (chName === currentChannel) {
                if (unread > 0 || forceRender) {
                    renderMessages(messages);
                    channelReadCounts[chName] = totalMsgs;
                    if (unread > 0) hasNewMsgInActiveChannel = true;
                }
            } else {
                let badge = document.getElementById(`badge-${chName}`);
                if (badge && unread > 0) {
                    badge.innerText = unread;
                    badge.style.display = "block";
                }
            }
        }

        lastRenderedChannel = currentChannel;

        if (hasNewMsgInActiveChannel) {
            document.getElementById("notifyBadge").style.display = "block";
            document.title = "(🔔) Tin nhắn mới!";
            setTimeout(() => { 
                document.getElementById("notifyBadge").style.display = "none"; 
                document.title = "Hybrid P2P Chat";
            }, 3000);
        }

    } catch(e) {}
}

// ==========================================
// 3. XỬ LÝ GIAO DIỆN (RENDER & CHUYỂN KÊNH)
// ==========================================
// function renderMessages(messages) {
//     const box = document.getElementById("messagesBox");
//     box.innerHTML = "";
    
//     messages.forEach(msg => {
//         const isMine = (msg.from === myInfo.username);
        
//         const msgDiv = document.createElement("div");
//         msgDiv.className = `msg ${isMine ? "mine" : ""}`;
        
//         const displayName = isMine ? 'Tôi' : msg.from;
        
//         msgDiv.innerHTML = `<div class="msg-info">${displayName} - ${msg.timestamp}</div>${msg.text}`;
//         box.appendChild(msgDiv);
//     });
    
//     box.scrollTop = box.scrollHeight;
// }

function renderMessages(messages) {
    const box = document.getElementById("messagesBox");
    box.innerHTML = "";
    messages.forEach(msg => {
        const isMine = (msg.from === myInfo.username);
        const msgDiv = document.createElement("div");
        msgDiv.className = `msg ${isMine ? "mine" : ""}`;
        msgDiv.innerHTML = `<div class="msg-info">${isMine ? 'Tôi' : msg.from} - ${msg.timestamp}</div>${msg.text}`;
        box.appendChild(msgDiv);
    });
    box.scrollTop = box.scrollHeight;
}

function changeChannel(channelName) {
    currentChannel = channelName;
    document.getElementById("channelTitle").innerText = `# ${channelName}`;
    
    let badge = document.getElementById(`badge-${channelName}`);
    if (badge) {
        badge.style.display = "none";
        badge.innerText = "0";
    }
    
    const items = document.querySelectorAll("#channelList li");
    items.forEach(li => li.classList.remove("active"));
    document.getElementById(`tab-${channelName}`).classList.add("active");
    
    updateChannelMembers();
    fetchMessages();
}

function updateSelectedPeerInfo() {
    const infoBox = document.getElementById('selectedPeerInfo');
    if (!infoBox) return;

    if (selectedPeer) {
        infoBox.innerText = `Đang gửi trực tiếp tới: ${selectedPeer}`;
    } else {
        infoBox.innerText = 'Chưa chọn peer trực tiếp.';
    }
}

function selectPeer(user) {
    selectedPeer = user;
    document.querySelectorAll('.peer-item').forEach(li => li.classList.remove('selected-peer'));
    const selected = document.getElementById(`peer-${user}`);
    if (selected) selected.classList.add('selected-peer');
    updateSelectedPeerInfo();
}

// ==========================================
// 4. GỬI TIN NHẮN (P2P DIRECT / BROADCAST)
// ==========================================
async function sendMessage() {
    const input = document.getElementById("msgInput");
    const text = input.value.trim();
    if (!text) return;
    if (!selectedPeer) {
        alert('Vui lòng chọn một peer để gửi trực tiếp, hoặc nhấn Broadcast.');
        return;
    }
    
    const payload = {
        sender: myInfo.username,
        message: text,
        channel: currentChannel,
        timestamp: new Date().toLocaleTimeString()
    };

    let peerInfo = activePeers[selectedPeer];
    if (!peerInfo) {
        try {
            const lookup = await fetch(`${trackerUrl}/connect-peer`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ username: selectedPeer })
            });
            const lookupData = await lookup.json();
            peerInfo = lookupData.peer;
            if (peerInfo) {
                activePeers[selectedPeer] = { ip: peerInfo.ip, port: peerInfo.port };
            }
        } catch (e) {
            console.log('Lỗi tra cứu peer:', e);
        }
    }

    if (!peerInfo) {
        alert('Peer đã chọn không tồn tại. Vui lòng chọn lại.');
        return;
    }

    const headers = getAuthHeaders(true);

    try {
        await deliverMessageToPeer(peerInfo, payload, headers);
    } catch (e) {
        console.log(`Lỗi gửi trực tiếp tới ${selectedPeer}:`, e);
    }

    try {
        await fetch(`http://127.0.0.1:${myInfo.port}/send-peer`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.log("Lỗi lưu tin nhắn nội bộ", e);
    }

    input.value = "";
    setTimeout(fetchMessages, 200);
}

async function sendBroadcast() {
    const input = document.getElementById("msgInput");
    const text = input.value.trim();
    if (!text) return;

    const payload = {
        sender: myInfo.username,
        message: text,
        channel: currentChannel,
        timestamp: new Date().toLocaleTimeString()
    };

    try {
        const res = await fetch(`http://127.0.0.1:${myInfo.port}/broadcast-peer`, {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            console.log('Broadcast failed', res.status);
        } else {
            const result = await res.json();
            console.log('Broadcast sent to', result.broadcasted_to, 'peers');
        }
    } catch (e) {
        console.log('Lỗi broadcast:', e);
    }

    input.value = "";
    setTimeout(fetchMessages, 200);
}
