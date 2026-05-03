# import tkinter as tk
# from tkinter import scrolledtext, messagebox
# import urllib.request
# import json
# import threading
# import time

# class ChatApp:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("P2P Hybrid Chat - Desktop App")
#         self.root.geometry("450x550")
        
#         self.username = ""
#         self.my_port = ""
#         self.my_ip = "127.0.0.1"
#         self.peers = {}

#         # ====================================
#         # 1. GIAO DIỆN ĐĂNG NHẬP (LOGIN WINDOW)
#         # ====================================
#         self.login_frame = tk.Frame(root, pady=80)
#         self.login_frame.pack()

#         tk.Label(self.login_frame, text="Tên của bạn:", font=("Arial", 12)).pack(pady=5)
#         self.name_entry = tk.Entry(self.login_frame, font=("Arial", 12))
#         self.name_entry.pack(pady=5)

#         tk.Label(self.login_frame, text="Port máy bạn (VD: 9001):", font=("Arial", 12)).pack(pady=5)
#         self.port_entry = tk.Entry(self.login_frame, font=("Arial", 12))
#         self.port_entry.pack(pady=5)

#         tk.Button(self.login_frame, text="Vào Chat", command=self.login, 
#                   bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=15).pack(pady=20)

#         # ====================================
#         # 2. GIAO DIỆN BOX CHAT (CHAT WINDOW)
#         # ====================================
#         self.chat_frame = tk.Frame(root)
        
#         # Khung hiển thị tin nhắn (có thanh cuộn)
#         self.chat_area = scrolledtext.ScrolledText(self.chat_frame, state='disabled', width=50, height=25, font=("Consolas", 11))
#         self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

#         self.chat_area.tag_configure("right", justify='right', foreground="#0084FF") # Của mình: Canh phải, chữ xanh dương
#         self.chat_area.tag_configure("left", justify='left', foreground="#000000")   # Người khác: Canh trái, chữ đen

#         # Khung nhập tin nhắn
#         input_frame = tk.Frame(self.chat_frame)
#         input_frame.pack(fill=tk.X, padx=10, pady=5)

#         self.msg_entry = tk.Entry(input_frame, font=("Arial", 12))
#         self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
#         self.msg_entry.bind("<Return>", lambda e: self.send_message()) # Bấm Enter để gửi

#         tk.Button(input_frame, text="Gửi", command=self.send_message, bg="#2196F3", fg="white", width=8).pack(side=tk.RIGHT)

#     def make_request(self, url, data=None):
#         """Hàm gửi Request bằng Socket TCP thuần, chống lại mọi lỗi định dạng của Server"""
#         import socket
#         import urllib.parse
#         import ast
#         import json

#         try:
#             # 1. Phân tích URL
#             parts = urllib.parse.urlparse(url)
#             host = parts.hostname
#             port = parts.port or 80
#             path = parts.path
#             method = "POST" if data else "GET"

#             # 2. Xây dựng gói tin HTTP Request thủ công
#             headers = [
#                 f"{method} {path} HTTP/1.1",
#                 f"Host: {host}:{port}",
#                 "Connection: close"
#             ]

#             body_bytes = b""
#             if data:
#                 body_bytes = json.dumps(data).encode('utf-8')
#                 headers.append("Content-Type: application/json")
#                 headers.append(f"Content-Length: {len(body_bytes)}")
#                 # Nhúng data vào Header dự phòng rớt mạng
#                 for k, v in data.items():
#                     headers.append(f"X-Chat-{k}: {urllib.parse.quote(str(v))}")

#             req_str = "\r\n".join(headers) + "\r\n\r\n"
#             req_bytes = req_str.encode('utf-8') + body_bytes

#             # 3. Mở kết nối Socket TCP trực tiếp
#             with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#                 s.settimeout(3)
#                 s.connect((host, port))
#                 s.sendall(req_bytes)

#                 # Nhận dữ liệu trả về
#                 response = b""
#                 while True:
#                     chunk = s.recv(4096)
#                     if not chunk: break
#                     response += chunk

#             # 4. Phân tích gói tin trả về (Dù là HTTP chuẩn hay Raw String đều xử lý được)
#             res_str = response.decode('utf-8', errors='ignore').strip()

#             if res_str.startswith("HTTP/"):
#                 # Nếu là HTTP chuẩn, chặt bỏ Header lấy phần Body
#                 body_part = res_str.split("\r\n\r\n", 1)[-1].strip()
#             else:
#                 # Nếu server framework lỗi, nhả Raw String thì ta lấy luôn
#                 body_part = res_str 

#             # 5. Ép kiểu dữ liệu an toàn
#             if body_part.startswith("{"):
#                 try:
#                     # Dùng ast.literal_eval để biến chuỗi {'msg': '...'} thành Dictionary
#                     return ast.literal_eval(body_part)
#                 except Exception:
#                     return json.loads(body_part)
                    
#             return None

#         except Exception as e:
#             print(f"❌ Lỗi Socket tới {url}: {str(e)}")
#             return None

#     def login(self):
#         self.username = self.name_entry.get().strip()
#         self.my_port = self.port_entry.get().strip()
        
#         if not self.username or not self.my_port:
#             messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ thông tin!")
#             return

#         # Server TRUNG TÂM (Tracker) luôn mặc định là Port 8000
#         self.tracker_url = "http://127.0.0.1:8000"
#         self.my_backend_url = f"http://127.0.0.1:{self.my_port}"

#         # Bước 1: Gọi lên Tracker để đăng ký IP/Port (Client-Server Paradigm)
#         res = self.make_request(f"{self.tracker_url}/submit-info", {
#             "username": self.username,
#             "ip": self.my_ip,
#             "port": self.my_port
#         })

#         if res:
#             # Nếu kết nối thành công, ẩn màn hình Login, hiện Box Chat
#             self.login_frame.pack_forget()
#             self.chat_frame.pack(fill=tk.BOTH, expand=True)
#             self.root.title(f"App Chat P2P - {self.username}")
            
#             # Bắt đầu vòng lặp lấy dữ liệu ngầm (Non-blocking UI)
#             self.update_peers()
#             self.update_messages()
#         else:
#             messagebox.showerror("Lỗi", "Không thể kết nối Server Trung Tâm.\n\nBạn đã mở Terminal chạy cổng 8000 chưa?")

#     def update_peers(self):
#         """Đồng bộ danh sách IP từ Tracker mỗi 3 giây"""
#         res = self.make_request(f"{self.tracker_url}/get-list")
#         if res: self.peers = res
#         self.root.after(3000, self.update_peers) 

#     def update_messages(self):
#         """Lấy tin nhắn P2P từ Backend của chính máy mình mỗi 1 giây"""
#         res = self.make_request(f"{self.my_backend_url}/get-messages")
#         if res and "general" in res:
#             self.chat_area.config(state='normal')
#             self.chat_area.delete(1.0, tk.END) # Xóa text cũ
            
#             # In lại toàn bộ text mới với định dạng canh lề
#             for msg in res["general"]:
#                 if msg['from'] == self.username:
#                     # Tin nhắn của mình: Canh phải, không cần hiện tên mình
#                     formatted_msg = f"{msg['text']} [{msg['timestamp']}]\n"
#                     self.chat_area.insert(tk.END, formatted_msg, "right")
#                 else:
#                     # Tin nhắn người khác: Canh trái
#                     formatted_msg = f"[{msg['timestamp']}] {msg['from']}: {msg['text']}\n"
#                     self.chat_area.insert(tk.END, formatted_msg, "left")
                    
#             self.chat_area.config(state='disabled')
#             self.chat_area.yview(tk.END) # Tự động cuộn xuống tin nhắn mới nhất
        
#         self.root.after(1000, self.update_messages) 

#     def send_message(self):
#         text = self.msg_entry.get().strip()
#         if not text: return

#         payload = {
#             "sender": self.username,
#             "message": text,
#             "channel": "general",
#             "timestamp": time.strftime("%H:%M:%S")
#         }

#         # Bắn HTTP POST trực tiếp tới tất cả máy khác (Peer-to-Peer Paradigm)
#         for user, info in self.peers.items():
#             # QUAN TRỌNG: Bỏ qua không tự gửi cho chính mình trong vòng lặp P2P này
#             if user == self.username:
#                 continue 
                
#             peer_url = f"http://{info['ip']}:{info['port']}/send-peer"
#             threading.Thread(target=self.make_request, args=(peer_url, payload)).start()

#         # Tự gửi cho chính mình 1 lần duy nhất để lưu vào Backend nội bộ
#         self.make_request(f"{self.my_backend_url}/send-peer", payload)
#         self.msg_entry.delete(0, tk.END)

# if __name__ == "__main__":
#     root = tk.Tk()
#     app = ChatApp(root)
#     root.mainloop()