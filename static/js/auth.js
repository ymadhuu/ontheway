// --- 1. CONFIGURATIONS ---
const firebaseConfig = {
    apiKey: "AIzaSyBmJjSD03nKazEClq20_PA5b1hpwRtwZqA",
    authDomain: "ontheway-9350e.firebaseapp.com",
    projectId: "ontheway-9350e",
    storageBucket: "ontheway-9350e.firebasestorage.app",
    messagingSenderId: "625055911494",
    appId: "1:625055911494:web:e0f667f77b7f9ab0374447"
};

if (!firebase.apps.length) firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();

const GEMINI_KEY = "AIzaSyBA-YeT9kg-4idfh6Qgh8_tUZnqz9_qjRk"; 
// Using gemini-pro as default (most stable and widely available)
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${GEMINI_KEY}`;

// --- 2. PAGE ROUTING & AUTH STATE ---
auth.onAuthStateChanged((user) => {
    const path = window.location.pathname;
    if (user) {
        if (document.getElementById('userEmailDisplay')) 
            document.getElementById('userEmailDisplay').innerText = user.email;
        
        // Page specific loads
        if (path.includes("dashboard")) loadMyBookings();
        if (path.includes("search")) loadTrainsAsCards();
        if (path.includes("checkout")) renderBookingSummary(); 
    } else {
        const publicPages = ["/", "/register", "/index.html"];
        if (!publicPages.some(page => path.endsWith(page))) window.location.href = "/";
    }
});

// --- 3. SEARCH & BOOKING LOGIC ---
function loadTrainsAsCards() {
    const container = document.getElementById('train-cards-container');
    if (!container) return;
    db.collection("trains").get().then((qs) => {
        container.innerHTML = "";
        qs.forEach((doc) => {
            const data = doc.data();
                container.innerHTML += `
                <div class="train-card" style="border:1px solid #444; padding:15px; margin:10px; border-radius:10px; background:rgba(255,255,255,0.05);">
                    <h4>${data.name}</h4>
                    <p>${data.source} to ${data.destination}</p>
                    <button class="book-btn" onclick="initiateBooking('${data.name}', ${data.fare}, '${data.source || 'Mumbai'}', '${data.destination || 'Delhi'}')" style="background:#00d2ff; border:none; padding:8px 15px; border-radius:5px; cursor:pointer;">Select</button>
                </div>`;
        });
    });
}

function initiateBooking(name, fare, source, destination) {
    const dateInput = document.getElementById('journey-date');
    if (!dateInput || !dateInput.value) return alert("Please select a date!");
    localStorage.setItem('pendingBooking', JSON.stringify({ 
        name, 
        fare, 
        date: dateInput.value, 
        seats: "None Selected",
        source: source || "Mumbai",
        destination: destination || "Delhi",
        departureTime: "10:00",
        arrivalTime: "18:00"
    }));
    window.location.href = "/checkout";
}

// --- 4. CHECKOUT & EMAIL LOGIC ---
function renderBookingSummary() {
    const pending = JSON.parse(localStorage.getItem('pendingBooking'));
    const summaryDiv = document.getElementById('booking-details');
    if (pending && summaryDiv) {
        summaryDiv.innerHTML = `
            <h2>${pending.name}</h2>
            <p>Journey Date: ${pending.date}</p>
            <p>Fare: ₹${pending.fare}</p>
            <p id="selected-seat-info" style="color:#00ff88; font-weight:bold;">Seat: ${pending.seats}</p>
        `;
        if(pending.seats === "None Selected") setupSeatSelection();
    }
}

async function finalizeBooking() {
    const pending = JSON.parse(localStorage.getItem('pendingBooking'));
    const user = auth.currentUser;
    if (pending.seats === "None Selected") return alert("Seat select kar le bhai!");

    const pnr = Math.floor(Math.random() * 9000000000) + 1000000000;
    const finalData = { ...pending, pnr: pnr.toString(), userEmail: user.email };

    try {
        await db.collection("bookings").add(finalData);
        
        // EmailJS call (Public Key 'YOUR_PUBLIC_KEY' replace kar dena dashboard.html mein)
        emailjs.send("service_otw", "template_otw", {
            to_email: user.email,
            train_name: finalData.name,
            pnr_no: finalData.pnr,
            seat_no: finalData.seats
        }).then(() => console.log("Mail Sent")).catch(e => console.log("Mail Error"));

        alert("Booking Done! PNR: " + pnr);
        window.location.href = "/dashboard";
    } catch (e) { alert("Error: " + e.message); }
}

// --- 5. AI CHAT & PNR TRACKER ---
async function sendMessage(autoMsg = null) {
    const input = document.getElementById('chatInput');
    const container = document.getElementById('chat-body') || document.getElementById('chat-content');
    const msg = autoMsg || (input ? input.value : "");

    if (!msg || !container) return;
    if (input) input.value = "";

    container.innerHTML += `<div style="text-align:right; color:#00ff88; margin:5px;"><b>You:</b> ${msg}</div>`;
    
    try {
        const res = await fetch(GEMINI_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ contents: [{ parts: [{ text: `You are OTW Rail Bot. Reply in 1 line Hinglish. User: ${msg}` }] }] })
        });
        const data = await res.json();
        const reply = data.candidates[0].content.parts[0].text;
        container.innerHTML += `<div style="text-align:left; color:#00d2ff; margin:5px;"><b>OTW Bot:</b> ${reply}</div>`;
    } catch (e) { container.innerHTML += `<div>Error connecting AI.</div>`; }
    container.scrollTop = container.scrollHeight;
}

function trackPNR() {
    const val = document.getElementById('pnrInput')?.value;
    if (val && val.length === 10) {
        if(typeof toggleChat === "function") toggleChat();
        sendMessage("Check my PNR status: " + val);
    } else { alert("Enter 10 digit PNR"); }
}

// --- 6. DASHBOARD LOAD ---
function loadMyBookings() {
    const container = document.getElementById('my-bookings-container');
    if (!container || !auth.currentUser) return;
    db.collection("bookings").where("userEmail", "==", auth.currentUser.email).get().then((qs) => {
        container.innerHTML = qs.empty ? "No bookings found." : "";
        qs.forEach(doc => {
            const b = doc.data();
            container.innerHTML += `<div class="booking-card" style="background:rgba(255,255,255,0.1); padding:10px; margin:5px; border-radius:5px;">
                <b>${b.trainName}</b> | PNR: ${b.pnr} | Seat: ${b.seats}
            </div>`;
        });
    });
}

function handleLogout() { auth.signOut().then(() => window.location.href = "/"); }

// --- 7. LOGIN FUNCTION ---
function login() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    
    if(!email || !password) {
        alert("Please enter both email and password!");
        return;
    }
    
    auth.signInWithEmailAndPassword(email, password)
        .then((userCredential) => {
            // Successfully logged in
            console.log("Login successful:", userCredential.user.email);
            window.location.href = "/dashboard";
        })
        .catch((error) => {
            console.error("Login error:", error);
            let errorMessage = "Login failed. ";
            
            switch(error.code) {
                case 'auth/user-not-found':
                    errorMessage += "No account found with this email.";
                    break;
                case 'auth/wrong-password':
                    errorMessage += "Incorrect password.";
                    break;
                case 'auth/invalid-email':
                    errorMessage += "Invalid email format.";
                    break;
                case 'auth/user-disabled':
                    errorMessage += "This account has been disabled.";
                    break;
                case 'auth/too-many-requests':
                    errorMessage += "Too many failed attempts. Please try again later.";
                    break;
                default:
                    errorMessage += error.message;
            }
            
            alert(errorMessage);
        });
}

// --- 8. SIGN UP FUNCTION ---
function signUp() {
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPass').value;
    
    if(!name || !email || !password) {
        alert("Please fill in all fields!");
        return;
    }
    
    if(password.length < 6) {
        alert("Password must be at least 6 characters long!");
        return;
    }
    
    auth.createUserWithEmailAndPassword(email, password)
        .then((userCredential) => {
            // User created successfully
            console.log("Registration successful:", userCredential.user.email);
            alert("Account created successfully! Redirecting to dashboard...");
            window.location.href = "/dashboard";
        })
        .catch((error) => {
            console.error("Registration error:", error);
            let errorMessage = "Registration failed. ";
            
            switch(error.code) {
                case 'auth/email-already-in-use':
                    errorMessage += "An account with this email already exists.";
                    break;
                case 'auth/invalid-email':
                    errorMessage += "Invalid email format.";
                    break;
                case 'auth/weak-password':
                    errorMessage += "Password is too weak. Please use a stronger password.";
                    break;
                default:
                    errorMessage += error.message;
            }
            
            alert(errorMessage);
        });
}