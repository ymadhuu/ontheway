import requests
import smtplib
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "otw_rail_secret_key"

# Try to enable CORS if available (optional)
try:
    from flask_cors import CORS
    CORS(app)
    print("CORS enabled")
except ImportError:
    print("flask-cors not installed, CORS disabled (backend endpoint may still work)")
    
    # Add basic CORS headers manually
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        return response

# --- CONFIGURATION ---
SENDER_EMAIL = "ymadhu23it@student.mes.ac.in"
SENDER_PASSWORD = "vnpkcimvgavcliga" 

# --- EMAIL FUNCTION ---
def send_confirmation_email(user_email, train_name, pnr, amount, seats, date):
    subject = f"🎟️ Booking Confirmed - PNR: {pnr} | OTW Railways"
    body = f"""
Namaste! Aapki ticket successfully confirm ho gayi hai! 🚂

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         BOOKING CONFIRMATION DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 PNR Number: {pnr}
🚂 Train Name: {train_name}
📅 Journey Date: {date}
💺 Seat Numbers: {seats}
💰 Total Fare Paid: ₹{amount}
✅ Status: CONFIRMED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Important Instructions:
• Please carry original ID proof for verification
• Arrive at the station at least 30 minutes before departure
• This is a computer-generated ticket - no signature required
• For any queries or cancellations, contact OTW Railways support

Thank you for choosing OTW Railways!
Wishing you a safe and happy journey! 🚄

Best Regards,
OTW Railways Team
    """
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = user_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# --- ROUTES (Saare routes app.run se upar hone chahiye) ---

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/register')
def register(): 
    return render_template('register.html')

@app.route('/dashboard')
def dashboard(): 
    return render_template('dashboard.html')

@app.route('/search')
def search(): 
    return render_template('search.html')

@app.route('/checkout')
def checkout(): 
    return render_template('checkout.html')

@app.route('/pnr')
def pnr(): 
    return render_template('pnr.html')

@app.route('/admin')
def admin(): 
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('index'))

@app.route('/about') # AB YE CHALEGA!
def about():
    return render_template('about.html')

@app.route('/alogin') # YE BHI CHALEGA!
def admin_login_page():
    return render_template('alogin.html')

@app.route('/api/book-ticket', methods=['POST'])
def book_ticket():
    data = request.json
    success = send_confirmation_email(
        data.get('email'), data.get('trainName'), data.get('pnr'), 
        data.get('amount'), data.get('seat'), data.get('date')  
    )
    return jsonify({"status": "Success" if success else "Error"})

@app.route('/api/test-gemini', methods=['GET'])
def test_gemini():
    """Test endpoint to check if Gemini API is working"""
    try:
        gemini_api_key = os.environ.get('GEMINI_API_KEY', 'AIzaSyBA-YeT9kg-4idfh6Qgh8_tUZnqz9_qjRk')
        
        if not gemini_api_key or gemini_api_key == "YOUR_API_KEY":
            return jsonify({"error": "API key not configured", "success": False}), 500
        
        # Simple test request
        test_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_api_key}'
        response = requests.post(
            test_url,
            json={"contents": [{"parts": [{"text": "Hello"}]}]},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": "API is working!", "status": response.status_code})
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            return jsonify({
                "success": False, 
                "error": error_data.get('error', {}).get('message', 'Unknown error'),
                "status": response.status_code,
                "response": error_data
            }), response.status_code
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/cancel-ticket', methods=['POST'])
def cancel_ticket():
    """Handle ticket cancellation with refund calculation"""
    try:
        data = request.json
        fare = float(data.get('fare', 0))
        journey_date = data.get('date', '')
        
        # Calculate cancellation charges based on time before journey
        try:
            journey_dt = datetime.strptime(journey_date, '%Y-%m-%d')
            hours_before = (journey_dt - datetime.now()).total_seconds() / 3600
        except:
            hours_before = 48  # Default if date parsing fails
        
        # Cancellation charges: 0% if >48h, 25% if 24-48h, 50% if 12-24h, 75% if <12h
        if hours_before > 48:
            cancellation_percent = 0
        elif hours_before > 24:
            cancellation_percent = 25
        elif hours_before > 12:
            cancellation_percent = 50
        else:
            cancellation_percent = 75
        
        cancellation_charges = round((fare * cancellation_percent) / 100, 2)
        refund_amount = round(fare - cancellation_charges, 2)
        
        # Send cancellation email
        user_email = data.get('email', '')
        if user_email:
            try:
                send_cancellation_email(user_email, data.get('pnr', ''), data.get('trainName', ''), 
                                      cancellation_charges, refund_amount)
            except:
                pass  # Don't fail if email fails
        
        return jsonify({
            "success": True,
            "cancellationCharges": cancellation_charges,
            "refundAmount": refund_amount,
            "cancellationPercent": cancellation_percent,
            "hoursBeforeJourney": round(hours_before, 1)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/train-status', methods=['GET'])
def train_status():
    """Get live train status and location"""
    try:
        train_number = request.args.get('train')
        date = request.args.get('date', '')
        
        if not train_number:
            return jsonify({"error": "Train number required", "success": False}), 400
        
        # Mock train status data (in real app, integrate with railway API)
        import random
        stations = [
            {"name": "Mumbai Central", "code": "MMCT", "arrival": "10:00", "departure": "10:05", "delay": random.randint(0, 30)},
            {"name": "Surat", "code": "ST", "arrival": "13:20", "departure": "13:25", "delay": random.randint(0, 45)},
            {"name": "Vadodara", "code": "BRC", "arrival": "15:10", "departure": "15:15", "delay": random.randint(0, 30)},
            {"name": "Ahmedabad", "code": "ADI", "arrival": "16:30", "departure": "16:35", "delay": random.randint(0, 20)},
            {"name": "Delhi", "code": "NDLS", "arrival": "18:00", "departure": "18:00", "delay": random.randint(0, 60)}
        ]
        
        current_station_idx = random.randint(0, len(stations) - 1)
        current_station = stations[current_station_idx]
        
        return jsonify({
            "success": True,
            "trainNumber": train_number,
            "trainName": f"OTW Express {train_number}",
            "currentStation": current_station,
            "nextStation": stations[current_station_idx + 1] if current_station_idx < len(stations) - 1 else None,
            "allStations": stations,
            "status": "Running" if current_station["delay"] < 15 else "Delayed",
            "delay": current_station["delay"],
            "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/track-train')
def track_train_page():
    """Train tracking page"""
    return render_template('track_train.html')

@app.route('/api/update-waitlist-status', methods=['POST'])
def update_waitlist_status():
    """Update waitlist status - simulate auto-confirmation"""
    try:
        data = request.json
        booking_id = data.get('bookingId')
        pnr = data.get('pnr')
        
        # Simulate waitlist confirmation logic
        # In real app, this would check actual waitlist status from railway API
        import random
        confirmation_chance = random.random()
        
        if confirmation_chance > 0.7:  # 30% chance of confirmation
            new_status = "CONFIRMED"
            waitlist_number = None
            rac_seat = None
            message = "Your waitlist ticket has been confirmed!"
        elif confirmation_chance > 0.4:  # 30% chance of RAC
            new_status = "RAC"
            waitlist_number = None
            rac_seat = f"RAC{random.randint(1, 10)}"
            message = "Your ticket status changed to RAC!"
        else:
            # Still waitlist, but position might improve
            new_status = "WAITLIST"
            waitlist_number = random.randint(1, 20)
            rac_seat = None
            message = f"Your waitlist position is now {waitlist_number}"
        
        return jsonify({
            "success": True,
            "status": new_status,
            "waitlistNumber": waitlist_number,
            "racSeat": rac_seat,
            "message": message
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def send_cancellation_email(user_email, pnr, train_name, cancellation_charges, refund_amount):
    """Send cancellation confirmation email"""
    subject = f"🎫 Ticket Cancelled - PNR: {pnr} | OTW Railways"
    body = f"""
Your ticket has been successfully cancelled.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         CANCELLATION DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 PNR Number: {pnr}
🚂 Train Name: {train_name}
❌ Status: CANCELLED
💰 Cancellation Charges: ₹{cancellation_charges}
💵 Refund Amount: ₹{refund_amount}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Refund Information:
• Refund will be processed within 5-7 working days
• Amount will be credited to your original payment method
• You will receive SMS/Email confirmation once refund is processed

Thank you for using OTW Railways!

Best Regards,
OTW Railways Team
    """
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = user_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

@app.route('/api/gemini-chat', methods=['POST'])
def gemini_chat():
    """Proxy endpoint for Gemini API to avoid CORS issues"""
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "No message provided", "success": False}), 400
        
        # Get API key from environment or use default
        gemini_api_key = os.environ.get('GEMINI_API_KEY', 'AIzaSyBA-YeT9kg-4idfh6Qgh8_tUZnqz9_qjRk')
        
        if not gemini_api_key or gemini_api_key == "YOUR_API_KEY":
            return jsonify({"error": "API key not configured", "success": False}), 500
        
        # Try multiple endpoints and models
        endpoints = [
            {'url': f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_api_key}', 'name': 'v1beta/gemini-pro'},
            {'url': f'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={gemini_api_key}', 'name': 'v1/gemini-pro'},
            {'url': f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={gemini_api_key}', 'name': 'v1beta/gemini-1.5-pro'},
            {'url': f'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={gemini_api_key}', 'name': 'v1/gemini-1.5-pro'},
        ]
        
        last_error = None
        
        for endpoint in endpoints:
            try:
                print(f"Trying endpoint: {endpoint['name']}")
                response = requests.post(
                    endpoint['url'],
                    json={"contents": [{"parts": [{"text": user_message}]}]},
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                
                print(f"Response status for {endpoint['name']}: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('candidates') and len(result['candidates']) > 0:
                        reply = result['candidates'][0]['content']['parts'][0]['text']
                        print(f"✅ Success with {endpoint['name']}")
                        return jsonify({"reply": reply, "success": True})
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('error', {}).get('message', response.text[:200])
                    last_error = f"{endpoint['name']}: {error_msg}"
                    print(f"❌ Failed {endpoint['name']}: {last_error}")
                
            except requests.exceptions.Timeout:
                last_error = f"{endpoint['name']}: Request timeout"
                print(f"⏱️ Timeout with {endpoint['name']}")
                continue
            except requests.exceptions.RequestException as e:
                last_error = f"{endpoint['name']}: {str(e)}"
                print(f"❌ Request error with {endpoint['name']}: {e}")
                continue
            except Exception as e:
                last_error = f"{endpoint['name']}: {str(e)}"
                print(f"❌ Unexpected error with {endpoint['name']}: {e}")
                continue
        
        # All endpoints failed
        error_msg = f"All endpoints failed. Last error: {last_error}" if last_error else "All endpoints failed"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg, "success": False, "last_error": last_error}), 500
        
    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg, "success": False}), 500

@app.route('/get_pnr_status', methods=['POST'])
def pnr_status():
    pnr_no = request.form.get('pnr')
    # Yahan hum Gemini API ya Firebase se mock data fetch karenge
    pnr_data = {
        "status": "CNF",
        "coach": "B1",
        "seat": "21",
        "train": "OTW Express"
    }
    return render_template('dashboard.html', pnr_result=pnr_data)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# --- SERVER START (HAMESHA SABSE LAST MEIN) ---


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)