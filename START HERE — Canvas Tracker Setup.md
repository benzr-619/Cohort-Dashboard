# Canvas Assignment Tracker — Start Here

A plain-language guide to connecting Claude to your school's Canvas so it can keep track of all your assignments across cohorts.

## The big picture

There are two phases. Phase 1 is a one-time setup (mostly double-clicking). Phase 2 is the part you'll actually use every day, and it lives entirely inside Claude — no files, no terminal.

```
PHASE 1 (once, ~5 min)          PHASE 2 (every day, inside Claude)
┌───────────────────┐           ┌──────────────────────────────┐
│ Double-click the  │           │ • "What's due this week?"    │
│ installer file →  │  ───────► │ • A live dashboard you open  │
│ answer 2 questions│           │   anytime and hit Reload     │
└───────────────────┘           └──────────────────────────────┘
```

---

## Phase 1 — One-time setup

### Step 1. Double-click the installer
In this same folder there's a file called **`Install Canvas Control.command`**.
Double-click it. A black window (Terminal) opens and starts working on its own.

> **If your Mac says it "can't be opened" or is from an unidentified developer:**
> Right-click the file instead → choose **Open** → click **Open** again. You only do this once.

### Step 2. Answer the two questions
Near the end it asks you for:

1. **Your school's Canvas web address** — open Canvas in your browser and copy the start of the address, e.g. `https://yourschool.instructure.com`
2. **Your Canvas access token** — paste the long code. *It won't show on screen as you type. That's intentional and normal — just paste and press Return.*

### Step 3. Restart Claude
When it says **DONE**, quit Claude completely (**Cmd + Q**), then open it again, come back to this chat, and type:

> **Canvas is connected**

That's it for setup. The black window never needs to be opened again — Claude starts the connection automatically from now on.

---

## Phase 2 — What you'll get (once connected)

- **Just ask, anytime:** "What's due this week?", "Show me everything for [cohort] sorted by date", "What are the instructions for the strategy paper?", "Anything new posted in the last few days?"
- **A live dashboard:** a single page you open inside Claude that lists every upcoming assignment across all your cohorts, sorted by due date, with the instructions one click away. Hit **Reload** and it pulls fresh from Canvas. Claude will build this for you after the connection is live.
- *(Optional later)* a short automatic message each morning telling you what's coming up.

---

## A note on your access token (please read)

That token is like a password to your whole Canvas account. Two things:

1. The token you pasted into the chat earlier should be **regenerated** in Canvas once setup works, so the copy in the chat stops working. (Account → Settings → delete the old "Approved Integration" and make a new token. Re-run the installer with the new one — it's quick.)
2. The token is stored in a settings file on **your** computer only. It is not uploaded anywhere.

---

## If something goes wrong

Take a screenshot of the black window and paste it into this chat. I'll tell you the fix. The installer makes a safety backup of your Claude settings before changing anything, so nothing is lost.
