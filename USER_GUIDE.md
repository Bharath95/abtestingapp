# DesignPoll — User Guide

A simple tool to run A/B design tests. Show your design options to people, let them pick their favorite, and see the results.

---

## Getting Started (First Time Only)

You only need to do this once when you first get the app.

### What You Need Installed

Before using DesignPoll, make sure these are installed on your computer:

- **Python 3.11+** — Check by opening Terminal and typing: `python3 --version`
- **Node.js 18+** — Check by typing: `node --version`
- **npm** — Comes with Node.js. Check: `npm --version`

If any of these are missing, ask your developer to install them, or:
- Python: https://www.python.org/downloads/
- Node.js: https://nodejs.org/ (choose the LTS version)

### First-Time Setup

Open **Terminal** (on Mac: search for "Terminal" in Spotlight) and run these commands one by one:

```
cd /path/to/abtestingapp
```
(Replace `/path/to/abtestingapp` with wherever the project folder is on your computer)

**Set up the backend:**
```
cd backend
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

**Set up the frontend:**
```
cd frontend
npm install
cd ..
```

That's it! You're ready to go.

---

## Starting the App

Every time you want to use DesignPoll, you need to start two things. Open **two Terminal windows**.

### Terminal Window 1 — Start the Backend

```
cd /path/to/abtestingapp/backend
source venv/bin/activate
uvicorn main:app --reload
```

You should see a message like "Uvicorn running on http://127.0.0.1:8000". **Leave this window open.**

### Terminal Window 2 — Start the Frontend

```
cd /path/to/abtestingapp/frontend
npm run dev
```

You should see "Ready" with a URL. **Leave this window open.**

### Open the App

Open your web browser (Chrome, Safari, etc.) and go to:

**http://localhost:3000**

You should see the DesignPoll dashboard.

---

## Creating a Test

### Step 1: Start a New Test

1. Click **"New Test"** in the top-right corner
2. Enter a **name** for your test (e.g., "Homepage Redesign")
3. Optionally add a **description** — this is shown to respondents before they start (e.g., "We're redesigning our homepage. Help us pick the best layout!")
4. Click **"Create Test"**

You'll be taken to the test editing page.

### Step 2: Add Questions

Each question shows a set of design options for people to choose from.

1. Click **"Add Question"**
2. Enter the **question title** (e.g., "Which homepage layout do you prefer?")
3. Configure these settings:
   - **Follow-up prompt** — The question asked after they pick an option (default: "Why did you choose this?"). You can change this to anything.
   - **Require follow-up** — Check this box if you want people to explain their choice. Uncheck if it's optional.
   - **Randomize options** — Check this to shuffle the order options appear (recommended to avoid bias). Uncheck if order matters.

### Step 3: Add Options to Each Question

Each question needs **2 to 5 options** (the design variants people choose between).

For each option:

1. Click **"Add Option"**
2. Enter a **label** (e.g., "Design A", "Blue Theme", "Minimalist Layout")
3. Choose how to show the design:
   - **Image Upload** — Click or drag-and-drop to upload a screenshot/mockup (JPEG, PNG, WebP, or GIF, max 10MB)
   - **URL** — Paste a link to a live page, Figma prototype, or any web URL

4. Repeat for each design option (minimum 2, maximum 5)

### Step 4: Add More Questions (Optional)

Repeat Steps 2-3 for each screen or design decision you want to test. For example:
- Question 1: "Which homepage layout?" (3 options)
- Question 2: "Which color scheme?" (2 options)
- Question 3: "Which navigation style?" (4 options)

---

## Activating a Test

Once you've added all your questions and options:

1. Go to your test's page
2. Click the **"Activate"** button
3. The test status changes from "Draft" to **"Active"**

**Important:**
- You need at least **1 question** with **2-5 options each** to activate
- Once activated, you **cannot change questions or options** (this protects the integrity of your results)
- You can still change the test name and description after activation

---

## Sharing with Respondents

Once your test is active, you'll see a **shareable link** on the test page. It looks like:

```
http://localhost:3000/respond/abc123xyz
```

### Option A: Hand Your Device to People (Easiest)

1. Open the shareable link in your browser
2. Hand your laptop/tablet/phone to the person
3. They complete the test
4. They hand it back
5. Repeat with the next person

### Option B: Share on Local Network

If you and the respondents are on the **same WiFi network**:

1. Find your computer's IP address:
   - On Mac: System Settings → Wi-Fi → Details → IP Address (looks like `192.168.1.xxx`)
2. Replace `localhost` with your IP in the link:
   ```
   http://192.168.1.xxx:3000/respond/abc123xyz
   ```
3. Share this link with respondents (text, email, Slack, etc.)
4. They open it on their own device

**Note:** This only works when your computer is on and both Terminal windows are running.

---

## What Respondents See

When someone opens your test link, they experience:

1. **Intro Screen** — Your test name and description with a "Start" button
2. **For Each Question:**
   - They see all options displayed side by side
   - They click one to select it — **their choice locks in immediately** (no going back!)
   - A "Locked in" indicator confirms their selection
   - If follow-up is configured, a text box appears asking why they chose that option
   - They click "Next" to continue
3. **A progress bar** shows "Question 2 of 5" etc.
4. **Thank You Screen** — after the last question

The whole flow is mobile-friendly, so it works on phones and tablets too.

---

## Viewing Results

### Analytics Dashboard

1. Go to your test's page
2. Click **"Analytics"**

You'll see:

- **Summary Stats** — Total respondents, total answers, how many completed all questions, and completion rate
- **Per Question:**
  - **Bar chart** showing how many votes each option got (with percentages)
  - You can toggle between **bar chart** and **pie chart** views
  - The **winning option** is highlighted
  - **Follow-up reasons** — all the text explanations grouped by which option people chose

### Exporting Data

Click the **"Export CSV"** button to download all responses as a spreadsheet file. You can open this in Excel, Google Sheets, or Numbers. Each row contains:
- Question title
- Which option was chosen
- The follow-up text (if any)
- Timestamp

---

## Closing a Test

When you're done collecting responses:

1. Go to your test's page
2. Click **"Close Test"**
3. The status changes to **"Closed"**

Closed tests:
- No longer accept new responses
- Respondents who try the link will see a "not accepting responses" message
- Your results and analytics are still fully accessible

---

## Managing Tests

### From the Dashboard (home page), you can:

- See all your tests with their status (Draft / Active / Closed)
- See how many questions and responses each test has
- Click any test to view or edit it

### Deleting a Test

1. Open the test
2. Scroll to the bottom
3. Click **"Delete Test"**
4. Confirm in the popup

**Warning:** This permanently deletes the test, all questions, all options, all responses, and all uploaded images. This cannot be undone.

---

## Stopping the App

When you're done for the day:

1. In **Terminal Window 1** (backend): Press `Ctrl + C`
2. In **Terminal Window 2** (frontend): Press `Ctrl + C`

Your data is saved automatically. Next time you want to use the app, just start both terminals again (see "Starting the App" above).

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Page not found" or blank screen | Make sure both Terminal windows are running |
| "Failed to fetch" errors | The backend isn't running — check Terminal Window 1 |
| Images not loading | Make sure the backend is running on port 8000 |
| Can't activate test | Check that every question has at least 2 options |
| Respondent sees "not accepting responses" | The test might be in Draft (not activated) or Closed |
| Link doesn't work for others | They need to be on the same WiFi network (see "Share on Local Network") |
| App feels slow to start | First load takes a few seconds — this is normal |

---

## Quick Reference

| Action | How |
|--------|-----|
| Start backend | `cd backend && source venv/bin/activate && uvicorn main:app --reload` |
| Start frontend | `cd frontend && npm run dev` |
| Open the app | http://localhost:3000 |
| Stop the app | `Ctrl + C` in both Terminal windows |
