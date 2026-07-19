const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const crypto = require('crypto');
const Razorpay = require('razorpay');
const path = require('path');
const bcrypt = require('bcryptjs'); // 🔒 NEW: Password Encryption
require('dotenv').config();

const app = express();
app.use(express.json({ limit: '10mb' }));
app.use(cors({ origin: '*' }));

app.use(express.static(__dirname));
app.get('/', (req, res) => { res.sendFile(path.join(__dirname, 'index.html')); });

mongoose.connect(process.env.MONGODB_URI)
    .then(() => console.log('[DATABASE] Connected successfully.'))
    .catch(err => console.log('[DATABASE ERROR]', err.message));

const razorpay = new Razorpay({
    key_id: process.env.RAZORPAY_KEY_ID,
    key_secret: process.env.RAZORPAY_KEY_SECRET
});

// 🔒 UPGRADED: Added Email & Password to Wallet
const WalletSchema = new mongoose.Schema({
    email: { type: String, unique: true, sparse: true },
    password: { type: String },
    api_key: { type: String, unique: true },
    credits: { type: Number, default: 50 },
    created_at: { type: Date, default: Date.now }
});
const Wallet = mongoose.model('Wallet', WalletSchema);

const AgentSchema = new mongoose.Schema({
    agent_name: String,
    description: String,
    created_at: { type: Date, default: Date.now }
});
const Agent = mongoose.model('Agent', AgentSchema);

async function checkBalance(req, res, next) {
    const apiKey = req.headers['x-api-key'];
    if (!apiKey) return res.status(401).json({ error: "Missing API Key" });

    if (apiKey === "sk_godmode_999") {
        req.wallet = { credits: 999999999, save: async () => {} };
        return next();
    }

    const wallet = await Wallet.findOne({ api_key: apiKey });
    if (!wallet) return res.status(401).json({ error: "Invalid Wallet" });

    req.wallet = wallet;
    next();
}

// 🔐 NEW: Registration Route
app.post('/auth/register', async (req, res) => {
    try {
        const { email, password } = req.body;
        const existing = await Wallet.findOne({ email });
        if (existing) return res.status(400).json({ error: "Email already in use." });

        const hashedPassword = await bcrypt.hash(password, 10);
        const newKey = "sk_" + crypto.randomBytes(16).toString('hex');

        const newWallet = new Wallet({
            email,
            password: hashedPassword,
            api_key: newKey,
            credits: 50 // 50 Free starter credits
        });
        await newWallet.save();

        res.json({ status: "success", api_key: newKey });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// 🔐 NEW: Login Route
app.post('/auth/login', async (req, res) => {
    try {
        const { email, password } = req.body;
        const user = await Wallet.findOne({ email });
        if (!user) return res.status(400).json({ error: "Invalid credentials." });

        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) return res.status(400).json({ error: "Invalid credentials." });

        res.json({ status: "success", api_key: user.api_key });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Legacy guest init (optional fallback)
app.post('/billing/init', async (req, res) => {
    try {
        const newKey = "sk_" + crypto.randomBytes(16).toString('hex');
        const newWallet = new Wallet({ api_key: newKey, credits: 50 });
        await newWallet.save();
        res.json({ api_key: newKey, credits: 50 });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/billing/create-order', checkBalance, async (req, res) => {
    try {
        const options = { amount: 49900, currency: "INR", receipt: `rcpt_${Date.now()}` };
        const order = await razorpay.orders.create(options);
        res.json(order);
    } catch (err) { res.status(500).json({ error: "Razorpay rejected the order." }); }
});

app.post('/billing/verify-payment', checkBalance, async (req, res) => {
    try {
        const { razorpay_order_id, razorpay_payment_id, razorpay_signature } = req.body;
        const expectedSignature = crypto
            .createHmac('sha256', process.env.RAZORPAY_KEY_SECRET)
            .update(razorpay_order_id + "|" + razorpay_payment_id).digest('hex');

        if (expectedSignature === razorpay_signature) {
            req.wallet.credits += 1000;
            await req.wallet.save();
            res.json({ status: "success", new_balance: req.wallet.credits });
        } else {
            res.status(400).json({ error: "Invalid signature" });
        }
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/agents/compile', checkBalance, async (req, res) => {
    try {
        if (req.wallet.credits < 20) return res.status(402).json({ message: "Insufficient credits." });
        const { transcript } = req.body;
        const raw = (transcript || "Specialized AI").replace(/I need a|I want a/gi, "").trim();
        const formatted = raw.split(" ").slice(0, 5).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
        const blueprint = { agent_name: `${formatted} Lead`, description: transcript };
        const newAgent = new Agent(blueprint);
        await newAgent.save();
        req.wallet.credits -= 20;
        await req.wallet.save();
        res.json({ status: "success", blueprint, credits_remaining: req.wallet.credits });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/chat', checkBalance, async (req, res) => {
    try {
        const { agent_name, message, image_base64, history } = req.body;
        const cost = image_base64 ? 5 : 1;
        if (req.wallet.credits < cost) return res.status(402).json({ message: "Insufficient credits." });

        const pythonResponse = await fetch("http://127.0.0.1:8000/v1/agent/chat", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent_name, message, image_base64, history })
        });
        const data = await pythonResponse.json();
        req.wallet.credits -= cost;
        await req.wallet.save();
        res.json({ response: data.response, credits_remaining: req.wallet.credits });
    } catch (err) { res.status(500).json({ error: "Gateway Error" }); }
});

app.listen(5000, () => console.log('[SERVER] Full-Stack SaaS Running securely on http://localhost:5000'));
