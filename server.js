const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(express.json());
app.use(cors({ origin: '*' }));

// 1. Connect to MongoDB Atlas Cloud Database
mongoose.connect(process.env.MONGODB_URI)
    .then(() => console.log('[DATABASE] Connected successfully.'))
    .catch(err => console.log('[DATABASE ERROR]', err.message));

// 2. Define the Agent Schema (We removed the User schema since login is gone)
const AgentSchema = new mongoose.Schema({
    agent_name: String,
    description: String,
    created_at: { type: Date, default: Date.now }
});
const Agent = mongoose.model('Agent', AgentSchema);

// 3. Naming Logic
function generateCleanName(prompt) {
    const text = prompt.toLowerCase();
    if (text.includes('medi')) return "Medical Researcher";
    if (text.includes('code')) return "Software Engineer";
    if (text.includes('data')) return "Data Analyst";
    return "Core Agent Prime";
}

// 4. The Open Compile Route (No passwords required)
app.post('/agents/compile', async (req, res) => {
    try {
        const { transcript } = req.body;
        const friendlyName = generateCleanName(transcript || "");

        const blueprint = {
            agent_name: friendlyName,
            description: transcript || "General ops."
        };

        const newAgent = new Agent(blueprint);
        await newAgent.save();

        res.json({ status: "success", blueprint });
    } catch (err) {
        console.error("[COMPILE ERROR]", err);
        res.status(500).json({ error: err.message });
    }
});

// 5. Start the Engine
app.listen(5000, () => console.log('[SERVER] Open Manager running on port 5000'));