import http.server
import socketserver
import sqlite3
import json
import os
import urllib.parse

PORT = 8765
DB_FILE = 'wishes.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS wishes (
            id TEXT PRIMARY KEY,
            name TEXT,
            message TEXT,
            timestamp TEXT,
            likes INTEGER DEFAULT 0,
            hasLiked BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/wishes':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT id, name, message, timestamp, likes, hasLiked FROM wishes ORDER BY timestamp DESC')
            rows = c.fetchall()
            conn.close()
            
            wishes = []
            for row in rows:
                wishes.append({
                    "id": row[0],
                    "name": row[1],
                    "message": row[2],
                    "timestamp": row[3],
                    "likes": row[4],
                    "hasLiked": bool(row[5])
                })
            self.send_json_response(wishes)
        else:
            # Serve static files
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/wishes':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO wishes (id, name, message, timestamp, likes, hasLiked)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (data['id'], data['name'], data['message'], data['timestamp'], 0, False))
                conn.commit()
                conn.close()
                self.send_json_response({"status": "success"})
            except Exception as e:
                self.send_json_response({"status": "error", "message": str(e)}, 400)
                
        elif self.path == '/api/like':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                wish_id = data.get('id')
                if wish_id:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    # toggle like logic or just increment? Let's assume just increment for simplicity
                    # Wait, our frontend allows toggling, so we should receive 'increment': true or false
                    increment = data.get('increment', True)
                    if increment:
                        c.execute('UPDATE wishes SET likes = likes + 1, hasLiked = 1 WHERE id = ?', (wish_id,))
                    else:
                        c.execute('UPDATE wishes SET likes = likes - 1, hasLiked = 0 WHERE id = ?', (wish_id,))
                    conn.commit()
                    
                    c.execute('SELECT likes FROM wishes WHERE id = ?', (wish_id,))
                    res = c.fetchone()
                    new_likes = res[0] if res else 0
                    conn.close()
                    self.send_json_response({"status": "success", "likes": new_likes})
                else:
                    self.send_json_response({"status": "error", "message": "Missing ID"}, 400)
            except Exception as e:
                self.send_json_response({"status": "error", "message": str(e)}, 400)
                
        elif self.path == '/api/reset':
            try:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('DELETE FROM wishes')
                conn.commit()
                conn.close()
                self.send_json_response({"status": "success"})
            except Exception as e:
                self.send_json_response({"status": "error", "message": str(e)}, 400)
        else:
            self.send_error(404, "Endpoint not found")

if __name__ == "__main__":
    init_db()
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
