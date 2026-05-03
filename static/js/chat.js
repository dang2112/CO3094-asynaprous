// ==========================================
// THÔNG TIN TOÀN CỤC (GLOBAL VARIABLES)
// ==========================================
let myInfo = { username: "", ip: "", port: "" };
let trackerUrl = "http://127.0.0.1:8000"; // Địa chỉ Server Trung Tâm (Tracker)
let activePeers = {};
let currentChannel = "general";
let channelReadCounts = { "general": 0, "study-group": 0 };// Biến đếm để kích hoạt thông báo tin nhắn mới
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

        // Ẩn form đăng nhập, hiện giao diện chat
        document.getElementById("loginModal").style.display = "none";
        document.getElementById("userInfo").innerText = `👤 ${myInfo.username} (Port: ${myInfo.port})`;
        
        // Khởi động các vòng lặp chạy ngầm để đồng bộ dữ liệu liên tục
        setInterval(fetchPeers, 3000);    // Mỗi 3s cập nhật danh sách IP 1 lần
        setInterval(fetchMessages, 1000); // Mỗi 1s lấy tin nhắn P2P 1 lần
        
        fetchPeers();
        fetchMessages();

    } catch (err) {
        alert("Lỗi kết nối tới Tracker Server ở cổng 8000. Hãy kiểm tra lại Terminal!");
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
            list.innerHTML += `<li>🟢 ${user} (${info.ip}:${info.port})</li>`;
        }
    } catch(e) {
        console.log("Đang mất kết nối với Tracker...");
    }
}

async function fetchMessages() {
    try {
        const res = await fetch(`http://127.0.0.1:${myInfo.port}/get-messages`);
        const channelsData = await res.json();
        
        let hasNewMsgInActiveChannel = false;
        
        // KIỂM TRA: Xem người dùng có vừa bấm chuyển sang kênh khác không?
        let forceRender = (lastRenderedChannel !== currentChannel); 

        for (const [chName, messages] of Object.entries(channelsData)) {
            if (channelReadCounts[chName] === undefined) channelReadCounts[chName] = 0;

            const totalMsgs = messages.length;
            const unread = totalMsgs - channelReadCounts[chName];

            if (chName === currentChannel) {
                // TRƯỜNG HỢP 1: Kênh đang mở trên màn hình
                // BÍ QUYẾT: Vẽ lại màn hình khi CÓ TIN NHẮN MỚI hoặc VỪA ĐỔI KÊNH
                if (unread > 0 || forceRender) {
                    renderMessages(messages);
                    channelReadCounts[chName] = totalMsgs;
                    if (unread > 0) hasNewMsgInActiveChannel = true;
                }
            } else {
                // TRƯỜNG HỢP 2: Kênh đang ẩn (Cập nhật Ô đỏ)
                let badge = document.getElementById(`badge-${chName}`);
                if (badge && unread > 0) {
                    badge.innerText = unread;
                    badge.style.display = "block";
                }
            }
        }

        // Chốt lại kênh hiện tại để so sánh cho vòng lặp 1 giây tiếp theo
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
//         // LOGIC CANH LỀ: Nếu tên người gửi trùng với tên mình thì gắn class "mine"
//         const isMine = (msg.from === myInfo.username);
        
//         const msgDiv = document.createElement("div");
//         msgDiv.className = `msg ${isMine ? "mine" : ""}`;
        
//         // Tên hiển thị: Mình thì ghi "Tôi", người khác thì in tên họ ra
//         const displayName = isMine ? 'Tôi' : msg.from;
        
//         msgDiv.innerHTML = `<div class="msg-info">${displayName} - ${msg.timestamp}</div>${msg.text}`;
//         box.appendChild(msgDiv);
//     });
    
//     // Luôn cuộn thanh scroll xuống vị trí dưới cùng
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
    
    // TẮT Ô ĐỎ khi người dùng click vào kênh đó (Vì đã đọc)
    let badge = document.getElementById(`badge-${channelName}`);
    if (badge) {
        badge.style.display = "none";
        badge.innerText = "0";
    }
    
    // Cập nhật UI menu bên trái
    const items = document.querySelectorAll("#channelList li");
    items.forEach(li => li.classList.remove("active"));
    document.getElementById(`tab-${channelName}`).classList.add("active");
    
    fetchMessages(); // Tải tin nhắn của kênh mới ngay lập tức
}

// ==========================================
// 4. GỬI TIN NHẮN (P2P BROADCAST)
// ==========================================
async function sendMessage() {
    const input = document.getElementById("msgInput");
    const text = input.value.trim();
    if (!text) return; // Không cho gửi tin nhắn trống
    
    // Gói tin cần gửi
    const payload = {
        sender: myInfo.username,
        message: text,
        channel: currentChannel,
        timestamp: new Date().toLocaleTimeString()
    };

    // BƯỚC 1: Bắn trực tiếp qua HTTP POST tới các máy khác (Peer-to-Peer Paradigm)
    for (const [user, info] of Object.entries(activePeers)) {
        if (user === myInfo.username) continue; // Bỏ qua, không tự bắn qua mạng cho chính mình

        fetch(`http://${info.ip}:${info.port}/send-peer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).catch(e => console.log(`Lỗi gửi P2P tới ${user}`));
    }

    // BƯỚC 2: Bắn ngược vào backend máy mình để tự lưu lịch sử và hiển thị
    fetch(`http://127.0.0.1:${myInfo.port}/send-peer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).catch(e => console.log("Lỗi lưu tin nhắn nội bộ"));

    // Xóa trắng ô nhập liệu và ép giao diện cập nhật ngay lập tức
    input.value = "";
    setTimeout(fetchMessages, 200); // Chờ 0.2s cho backend lưu xong rồi lấy hiển thị lên
}