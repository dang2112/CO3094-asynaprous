// ==========================================
// THÔNG TIN TOÀN CỤC (GLOBAL VARIABLES)
// ==========================================
let myInfo = { username: "", ip: "", port: "" };
let trackerUrl = "http://127.0.0.1:8000"; // Địa chỉ Server Trung Tâm (Tracker)
let activePeers = {};
let currentChannel = "general";
let selectedPeer = null;
let channelReadCounts = { "general": 0, "study-group": 0 };
let lastRenderedChannel = "";

// ==========================================
// 1. GIAI ĐOẠN KHỞI TẠO (ĐĂNG NHẬP)
// ==========================================
async function login() {
    myInfo.username = document.getElementById("username").value.trim();
    myInfo.ip = document.getElementById("myIp").value.trim();
    myInfo.port = document.getElementById("myPort").value.trim();

    if (!myInfo.username || !myInfo.port) {
        return alert("Vui lòng nhập đủ tên và cổng!");
    }

    try {
        // Gửi thông tin IP/Port lên Tracker Server (Client-Server Paradigm)
        await fetch(`${trackerUrl}/submit-info`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(myInfo)
        });

        document.getElementById("loginModal").style.display = "none";
        document.getElementById("userInfo").innerText = `👤 ${myInfo.username} (Port: ${myInfo.port})`;
        
        setInterval(fetchPeers, 3000);    // Mỗi 3s cập nhật danh sách IP 1 lần
        setInterval(fetchMessages, 1000); // Mỗi 1s lấy tin nhắn P2P 1 lần
        
        fetchPeers();
        fetchMessages();

    } catch (err) {
        alert("Lỗi kết nối tới Tracker Server ở cổng 8000.");
    }
}

// ==========================================
// 2. ĐỒNG BỘ MẠNG (POLLING LẤY IP VÀ TIN NHẮN)
// ==========================================
async function fetchPeers() {
    try {
        // Lấy danh sách Peer từ Tracker
        const res = await fetch(`${trackerUrl}/get-list`);
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
    } catch(e) {
        console.log("Đang mất kết nối với Tracker...");
    }
}

async function fetchMessages() {
    try {
        const res = await fetch(`http://127.0.0.1:${myInfo.port}/get-messages`);
        const channelsData = await res.json();
        
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

    const peerInfo = activePeers[selectedPeer];
    if (!peerInfo) {
        alert('Peer đã chọn không tồn tại. Vui lòng chọn lại.');
        return;
    }

    try {
        await fetch(`http://${peerInfo.ip}:${peerInfo.port}/send-peer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.log(`Lỗi gửi trực tiếp tới ${selectedPeer}:`, e);
    }

    try {
        await fetch(`http://127.0.0.1:${myInfo.port}/send-peer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
        const res = await fetch(`http://127.0.0.1:${myInfo.port}/broadcast`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            console.log('Broadcast failed', res.status);
        }
    } catch (e) {
        console.log('Lỗi broadcast:', e);
    }

    input.value = "";
    setTimeout(fetchMessages, 200);
}