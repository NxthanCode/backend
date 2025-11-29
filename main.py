# main.py - Complete FastAPI Backend
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import secrets
import jwt
import sqlite3
import bcrypt
import httpx
import os

app = FastAPI(title="Forced Entry API")

# CORS middleware - FIXED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== DATABASE SETUP ==========
def init_db():
    conn = sqlite3.connect('forced_entry.db')
    cursor = conn.cursor()
    
    # Users table - FIXED: Added proper SQL
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Verification codes table - FIXED: Added proper SQL
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            type TEXT NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()

    conn.commit()
    conn.close()
init_db()
SECRET_KEY = "forced-entry-" + secrets.token_urlsafe(32)
ALGORITHM = "HS256"
def get_db_connection():
    conn = sqlite3.connect('forced_entry.db')
    conn.row_factory = sqlite3.Row
    return conn
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
def create_access_token(user_id: int):
    expires = datetime.utcnow() + timedelta(days=7)
    payload = {"user_id": user_id, "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
def generate_verification_code():
    return str(secrets.randbelow(900000) + 100000)  
class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "forcedentry.game@gmail.com"  # Your Gmail
        self.app_password = "ffyi puqc wtkg cqju"  # The 16-char password from Step 2
    
    async def send_verification_email(self, email: str, code: str) -> bool:
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333; text-align: center;">Welcome to Forced Entry!</h2>
            <p>Your verification code:</p>
            <div style="background: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
                <h1 style="color: #000; font-size: 32px; letter-spacing: 5px; margin: 0;">{code}</h1>
            </div>
            <p>Enter this code to verify your account.</p>
            <p style="color: #666; font-size: 12px;">This code will expire in 30 minutes.</p>
        </div>
        """
        
        return await self._send_smtp_email(email, "Forced Entry Verification", html_content)
    
    async def send_password_reset_email(self, email: str, code: str) -> bool:
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333; text-align: center;">Password Reset</h2>
            <p>Your password reset code:</p>
            <div style="background: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
                <h1 style="color: #000; font-size: 32px; letter-spacing: 5px; margin: 0;">{code}</h1>
            </div>
            <p>Enter this code to reset your password.</p>
        </div>
        """
        
        return await self._send_smtp_email(email, "Password Reset - Forced Entry", html_content)
    
    async def _send_smtp_email(self, to_email: str, subject: str, html_content: str) -> bool:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = to_email
            
            # Create HTML version
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(self.sender_email, self.app_password)
                server.send_message(message)
            
            print(f"✅ Email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ SMTP error: {e}")
            return False

email_service = EmailService()


@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return {"message": "CORS preflight"}


@app.post("/register")
async def register(user_data: dict):
    username = user_data.get('username')
    email = user_data.get('email')
    password = user_data.get('password')
    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="All fields are required")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User already exists")
    password_hash = hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, password_hash)
    )
    user_id = cursor.lastrowid
    verification_code = generate_verification_code()
    expires_at = datetime.now().isoformat() + timedelta(minutes=30)
    cursor.execute(
        "INSERT INTO verification_codes (email, code, type, expires_at) VALUES (?, ?, ?, ?)",
        (email, verification_code, "email_verification", expires_at.isoformat())
    )
    conn.commit()
    conn.close()
    email_sent = await email_service.send_verification_email(email, verification_code)
    return {
        "message": "Registration successful. Check your email for verification code.",
        "user_id": user_id,
        "email_sent": email_sent
    }
@app.post("/verify-email")
async def verify_email(verification_data: dict):
    email = verification_data.get('email')
    code = verification_data.get('code')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM verification_codes WHERE email = ? AND code = ? AND type = 'email_verification' AND used = FALSE AND expires_at > ?",
        (email, code, datetime.now().isoformat())
    )
    code_record = cursor.fetchone()
    if not code_record:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    cursor.execute("UPDATE verification_codes SET used = TRUE WHERE id = ?", (code_record['id'],))
    cursor.execute("UPDATE users SET email_verified = TRUE WHERE email = ?", (email,))
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.commit()
    conn.close()
    access_token = create_access_token(user['id'])
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "email_verified": True,
            "created_at": user['created_at']
        }
    }
@app.post("/login")
async def login(user_data: dict):
    email = user_data.get('email')
    password = user_data.get('password')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    if not user or not verify_password(password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user['email_verified']:
        raise HTTPException(status_code=400, detail="Please verify your email first")
    access_token = create_access_token(user['id'])
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "email_verified": user['email_verified'],
            "created_at": user['created_at']
        }
    }
@app.post("/forgot-password")
async def forgot_password(email_data: dict):
    email = email_data.get('email')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if not cursor.fetchone():
        conn.close()
        return {"message": "If an account exists, a reset code has been sent"}
    reset_code = generate_verification_code()
    expires_at = datetime.now().isoformat() + timedelta(minutes=30)
    cursor.execute(
        "INSERT INTO verification_codes (email, code, type, expires_at) VALUES (?, ?, ?, ?)",
        (email, reset_code, "password_reset", expires_at.isoformat())
    )
    conn.commit()
    conn.close()
    email_sent = await email_service.send_password_reset_email(email, reset_code)
    return {"message": "If an account exists, a reset code has been sent", "email_sent": email_sent}
@app.post("/reset-password")
async def reset_password(reset_data: dict):
    email = reset_data.get('email')
    new_password = reset_data.get('new_password')
    code = reset_data.get('code')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM verification_codes WHERE email = ? AND code = ? AND type = 'password_reset' AND used = FALSE AND expires_at > ?",
        (email, code, datetime.now().isoformat())
    )
    code_record = cursor.fetchone()
    if not code_record:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    cursor.execute("UPDATE verification_codes SET used = TRUE WHERE id = ?", (code_record['id'],))
    new_password_hash = hash_password(new_password)
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (new_password_hash, email)
    )
    conn.commit()
    conn.close()
    return {"message": "Password reset successful"}
@app.get("/me")
async def get_current_user(token: str):
    payload = verify_token(token)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (payload['user_id'],))
    user = cursor.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user['id'],
        "username": user['username'],
        "email": user['email'],
        "email_verified": user['email_verified'],
        "created_at": user['created_at']
    }
@app.get("/")
async def root():
    return {"message": "Forced Entry API is running!"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
