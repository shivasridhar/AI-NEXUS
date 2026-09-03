Let's start from zero. I'll explain each piece, why it exists, and then walk through one concrete example so it clicks.

## First — what are you actually building?

You're building a **mini version of a company's security team**, using software. In a real company:

- Someone (or something) tries to break in → **Attacker**
- The company has computers/servers being targeted → **Victim**
- Tools watch the network traffic for suspicious activity → **Suricata**
- Tools watch what's happening *inside* the computer (logins, file changes, processes) → **Wazuh**
- Tools scan systems for known weaknesses before an attack happens → **OpenVAS**
- All these alerts flood in from different tools — someone needs to collect them, make sense of them, and show a single dashboard → **that's your SentinelAI app**

Your project's whole point is: **simulate an attack happening, and show that your system detects and reports it end-to-end.**

## Why 4 separate machines/VMs instead of one laptop?

Because in real life, the attacker's computer is never the same computer as the victim, and the security tools live on their own separate servers too. If everything is on one laptop, it doesn't behave like a real network — traffic doesn't actually "travel" anywhere. Using separate VMs makes the attack and detection *real*, not simulated on paper.

## The 5 pieces you need, explained simply

| Piece | What it is | Why you need it |
|---|---|---|
| **Kali Linux (Attacker)** | A Linux system preloaded with hacking tools | Used to *launch* attacks (scans, brute force, etc.) |
| **Victim machine** | A normal Ubuntu server | The "target" — this is what gets attacked |
| **Suricata** | Watches network traffic | Detects attacks happening *over the network* (like port scans) |
| **Wazuh** | Watches activity *on* a machine (logs, logins) | Detects attacks happening *on* the machine (like brute-force login attempts) |
| **OpenVAS** | Scans a machine for known weaknesses | Finds vulnerabilities *before* they're exploited (e.g. outdated software) |
| **SentinelAI (your app)** | Collects alerts from all of the above | Shows everything in one dashboard, correlates it |

## Concrete example (this is the whole demo, in one scenario)

Let's say your attack story is: **"An attacker scans our network, finds a weak server, and tries to brute-force its way in."**

1. **Attacker (Kali)** runs a scan: `nmap <victim-ip>` — this looks for open doors on the Victim.
2. **Suricata**, sitting on/near the Victim, sees this scan happening on the network and raises an alert: *"Port scan detected."*
3. **OpenVAS** had already scanned the Victim earlier and found: *"SSH is running an old, vulnerable version."*
4. **Attacker** then tries to guess the Victim's SSH password repeatedly (a brute-force attack) using a tool like Hydra.
5. **Wazuh**, running on the Victim, sees many failed login attempts in the system logs and raises an alert: *"Possible brute-force attack."*
6. **SentinelAI** receives all 3 alerts (Suricata's scan alert, OpenVAS's vulnerability report, Wazuh's brute-force alert), combines them, and shows on the dashboard: *"High-risk incident: Victim Server was scanned, found vulnerable, and is now under active brute-force attack."*

That's your entire demo story. Everything you build is in service of making this flow work and appear on screen.

## Step-by-step: how to actually set this up

**Step 1 — Connect the machines to one network**
Every machine (attacker, victim, Wazuh, OpenVAS) needs to be able to reach each other. Easiest beginner way: install **Tailscale** on all laptops/VMs (free app, takes 5 minutes). It gives each machine a private address they can use to talk to each other, no matter what Wi-Fi they're on.

**Step 2 — Set up the Victim**
Install Ubuntu Server as a VM (using VirtualBox, which is free). This is your "target." Nothing special needed yet — just a normal working Linux machine.

**Step 3 — Install Wazuh Agent on the Victim, Wazuh Manager elsewhere**
The Agent is a small program on the Victim that reports activity. The Manager is the server that collects those reports and decides "this looks like an attack." They're two different roles, so put the Manager on a different VM.

**Step 4 — Install Suricata on the Victim (or a VM sitting between Attacker and Victim)**
Suricata watches network packets and flags suspicious ones (scans, known attack patterns).

**Step 5 — Install OpenVAS on its own VM**
Point it at the Victim's address and run a scan. It will produce a report of weaknesses.

**Step 6 — Set up Kali as the Attacker**
This is where you'll run the actual attack commands (scan, brute-force) during the demo.

**Step 7 — Build small "collector" scripts**
Each tool (Wazuh, Suricata, OpenVAS) can send its alerts somewhere — you write a small script for each one that reads the tool's alert/log and sends it to your SentinelAI app in a common format (JSON). This is the "glue" that connects everything to your app.

**Step 8 — Build SentinelAI's dashboard**
It receives alerts from the 3 collectors, correlates them (realizes they're about the same Victim), and displays them together.

**Step 9 — Rehearse the attack flow**
Run the Nmap scan → Hydra brute-force → watch the alerts appear in your dashboard live.

## How the 4 team members should split this

- **Member 1 (you)**: Owns SentinelAI — the dashboard, correlation logic, and receiving alerts from all collectors.
- **Member 2**: Owns Wazuh — installs Manager + Agent, makes sure alerts get generated and sent to SentinelAI.
- **Member 3**: Owns Suricata + the Victim machine — sets up the target, makes sure network alerts work.
- **Member 4**: Owns OpenVAS + the Attacker (Kali) — runs vulnerability scans and executes the live attack during the demo.

Each person can build and test their own piece **on their own machine independently** first (without needing everyone online at once) — only at the end do you all connect together and test the full flow.

Want me to go deeper into any one part — like how to actually write the "collector" script that sends Wazuh/Suricata alerts to your app, or how to design SentinelAI's dashboard/schema?

# SentinelAI Stage 1: Team Split-Up & Proof of Concept Workflow

This document outlines the roles, responsibilities, and step-by-step instructions for each team member to successfully demonstrate the SentinelAI Stage 1 architecture.

---

## 👨‍💻 Member 1 (You) — SentinelAI Dashboard
**Role:** Central Hub & Correlation Engine

- [ ] **1. Network Setup:** Set up Tailscale, note your machine's IP, and share it with the team.
- [ ] **2. Dashboard App:** Build a simple web app (Flask/Node/Express) with one API endpoint: `POST /alerts`.
- [ ] **3. Data Contract:** Ensure the endpoint accepts JSON in the following format:
      ```json
      { 
        "source": "wazuh", 
        "type": "brute_force", 
        "target_ip": "192.168.x.x", 
        "details": "..." 
      }
      ```
- [ ] **4. UI & Storage:** Store incoming alerts in a list or lightweight database. Display them on a simple dashboard page that auto-refreshes every few seconds.
- [ ] **5. Correlation Logic:** Add basic correlation: if 2+ alerts arrive for the same `target_ip` within a short time window, flag it as a **"High Risk Incident."**
- [ ] **6. Mock Testing:** Test the endpoint using Postman. Send fake JSON alerts manually to confirm they appear on the dashboard before connecting other tools.
- [ ] **7. Integration:** Once Members 2, 3, and 4 have real alerts generating, instruct them to point their collector scripts to: `http://<your-tailscale-ip>:<port>/alerts`.

---

## 🛡️ Member 2 — Wazuh (Manager)
**Role:** Host Intrusion Detection System (HIDS)

- [ ] **1. Infrastructure:** Set up a VM (Ubuntu). Install Tailscale and note its IP.
- [ ] **2. Wazuh Installation:** Install Wazuh Manager and Wazuh Dashboard using the official Docker quickstart.
- [ ] **3. Agent Provisioning:** Give Member 3 your Tailscale IP so they can point their Wazuh Agent to your Manager.
- [ ] **4. Verification:** Confirm in your Wazuh dashboard that the Victim's agent (Member 3) shows as "active."
- [ ] **5. Alert Testing:** Trigger a test event on the Victim (e.g., input the wrong SSH password 3–4 times) and confirm Wazuh raises an alert internally.
- [ ] **6. Integration Script:** Write a small Python script that:
      - Calls Wazuh's REST API (`https://<manager-ip>:55000`) every few seconds.
      - Pulls new alerts.
      - Reformats them into the agreed-upon JSON structure (from Member 1).
      - Sends them via `POST` to SentinelAI's endpoint.
- [ ] **7. End-to-End Test:** Cause a failed login on the Victim and confirm it successfully appears on the SentinelAI dashboard.

---

## 🎯 Member 3 — Victim + Suricata
**Role:** Target Machine & Network Intrusion Detection (NIDS)

- [ ] **1. Infrastructure:** Set up a VM (Ubuntu Server) to act as the "Victim." Install Tailscale and note its IP.
- [ ] **2. Wazuh Agent:** Install the Wazuh Agent on this VM and point it at Member 2's Manager IP.
- [ ] **3. Suricata Setup:** Install Suricata on this VM. Run `suricata-update` to fetch the latest detection rules.
- [ ] **4. Vulnerability Sowing:** Intentionally leave one service outdated or misconfigured (e.g., an old OpenSSH version) so OpenVAS and the attacker have a target.
- [ ] **5. NIDS Verification:** Start Suricata and confirm it is actively logging to `eve.json`.
- [ ] **6. Integration Script:** Write a small Python script that:
      - `tail`s the `eve.json` file.
      - Filters for alert-type events.
      - Reformats them to the shared JSON structure.
      - `POST`s them to SentinelAI's endpoint.
- [ ] **7. End-to-End Test:** From any machine, run `nmap <victim-ip>`. Confirm Suricata logs it locally, and then confirm it appears on SentinelAI's dashboard.
- [ ] **8. IP Sharing:** Provide your Victim VM's Tailscale IP to Member 4 (so they can configure their OpenVAS scan target and Kali attacker).

---

## ⚔️ Member 4 — OpenVAS + Attacker (Kali)
**Role:** Vulnerability Scanner & Active Threat

- [ ] **1. Scanner Setup:** Set up a VM with OpenVAS/GVM (the Docker image is recommended). Install Tailscale and note its IP.
- [ ] **2. Vulnerability Scan:** Point a scan at the Victim's Tailscale IP (from Member 3). Run the scan and generate a vulnerability report.
- [ ] **3. Integration Script:** Write a script that pulls the scan results via GVM's API, reformats them into the shared JSON, and `POST`s them to SentinelAI. *(Note: This script only needs to run once before the live demo, not continuously).*
- [ ] **4. Attacker Setup:** Set up a second VM with Kali Linux to act as the Attacker.
- [ ] **5. Attack Preparation:** On Kali, prepare the following two commands to run live:
      ```bash
      # Port scan
      nmap -sS <victim-ip>
      
      # SSH Brute Force
      hydra -l root -P rockyou.txt ssh://<victim-ip>
      ```
- [ ] **6. Pre-flight Check:** Test both commands against the Victim beforehand to ensure Suricata and Wazuh both react as expected.

---

## 🚀 Final Step — The Live Demo (All 4 Together)

- [ ] **1. Connectivity:** Ensure everyone's VM is running and successfully connected via Tailscale.
- [ ] **2. Execution:** Member 4 executes the Nmap scan followed by the Hydra brute-force attack from Kali.
- [ ] **3. Monitoring:** Watch the SentinelAI dashboard (on Member 1's screen). It should light up with alerts originating from Suricata and Wazuh.
- [ ] **4. Correlation:** Ensure the dashboard successfully correlates these events into a single "High Risk Incident."
- [ ] **5. Backup:** Record this full run as a backup video before presenting it live.
