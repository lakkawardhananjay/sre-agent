
🤖 Project: Self-Healing SRE Agent on Bank of Anthos

🎯 Objective
The goal is to build an AI-driven Self-Healing System for a cloud-native banking application (Bank of Anthos).
 The system should:
Detect failures in the application or infrastructure.


Automatically heal them using predefined playbooks.


Explain the healing actions in plain English.


Test resilience by injecting failures (chaos engineering).


Provide an interactive chatbot for SRE queries.


This project demonstrates AI-assisted Site Reliability Engineering (SRE) in a Kubernetes environment.

🏗️ Scope of Work
The project is divided into five lightweight services, each with a clear boundary:
Metrics Collector


Collects application + system metrics (CPU, memory, latency).


Feeds data into monitoring dashboards (Grafana).


Scope limit: Only standard metrics (no custom exporters).


Playbook Runner


Executes automated healing rules.


Example: Restart pods if they crash too often.


Scope limit: Max 3 healing actions (restart, scale, drain).


Explain Agent


Uses AI to generate short explanations of healing actions.


Example: “Pod payment-api was OOMKilled. Restarted at 14:20.”


Scope limit: Two-sentence explanations, not full reports.


Chaos Agent


Injects failures into the system to test resilience.


Example: Kill a pod or introduce latency.


Scope limit: 3 types of chaos experiments only.


SRE Copilot


Chat interface (Slack bot or web UI).


Answers queries like:


“Why was pod X restarted?”


“What chaos tests ran today?”


Scope limit: 3 query types only.




📊 Deliverables
Technical Deliverables


Deployed Bank of Anthos application.


Monitoring dashboards (Grafana).


Auto-healing workflows (Playbook Runner).


AI-generated healing explanations (Explain Agent).


AI-curated chaos tests (Chaos Agent).


Interactive chatbot (SRE Copilot).


Business Deliverables


Demonstration of reduced downtime (self-healing).


Explainable AI actions → transparency for reliability.


Operational efficiency → AI helps SREs handle incidents.


Risk testing → Chaos agent validates resilience.



🚦 Success Criteria
When a failure occurs, the system auto-heals within seconds.


Grafana dashboard + Slack show clear explanations of actions taken.


Judges can ask Copilot “Why was pod X restarted?” and get a meaningful AI response.


Chaos agent injects failures and the system recovers automatically.



⚖️ Risk & Mitigation
Risk: Over-engineering services → delays.


Mitigation: Scope limited to 3 rules, 3 chaos scenarios, 3 queries.


Risk: Demo failure due to infra issues.


Mitigation: Record backup demo video.



🏆 Demo Flow (Hackathon)
Show Bank of Anthos app running normally.


Trigger chaos (e.g., kill a pod).


Healing agent detects & fixes issue.


Grafana/Slack shows AI explanation.


Judge asks chatbot → “What happened?” → AI responds live.


Impact: Judges see a future-ready, AI-powered reliability system.





























1. metrics-collector
📍 Scope: Collect just enough metrics + logs for healing & AI
Include


Prometheus scrape config for Bank of Anthos services (latency, CPU, memory).


Node Exporter + cAdvisor (basic infra metrics).


eBPF integration → optional (limit to 1 metric like network latency).


Stop Here


Don’t build custom exporters.


Don’t build full observability pipeline.


MVP Deliverable


Grafana shows pod health, request latency, node memory usage.



2. playbook-runner
📍 Scope: Execute only a few simple healing actions
Include


Define 3–4 healing rules:


Pod CrashLoop > 3 → kubectl rollout restart.


Pod latency > 1s → kubectl scale.


Node NotReady > 5m → drain node.


DB down → redeploy DB pod.


Rule engine → YAML config or hardcoded if/else.


Stop Here


Don’t make a DSL for rules.


Don’t implement complex dependency graphs.


MVP Deliverable


Pod crash is auto-healed with restart.


Grafana/Slack shows “playbook-runner executed restart.”



3. explain-agent
📍 Scope: AI-generated short explanations of healing actions
Include


Input: logs + metrics snapshot when healing triggers.


Prompt AI: “Analyze failure → explain cause + action in 2 sentences.”


Output:


Grafana annotation → “Pod payment-api OOMKilled. Restarted at 14:20.”


Slack message → “AI: Restarted pod due to OOM (memory > 512Mi).”


Stop Here


Don’t build full RCA (root cause analysis) system.


Don’t store explanations long-term.


MVP Deliverable


Every healing action gets an AI explanation in Grafana + Slack.



4. chaos-agent
📍 Scope: AI-curated but limited chaos scenarios
Include


Query cluster resources (kubectl get pods).


AI picks from 2–3 chaos types:


Kill pod.


Inject latency.


Stress CPU.


Run scenario via Chaos Mesh or LitmusChaos.


Stop Here


Don’t implement 10+ scenarios.


Don’t do multi-resource chaos chains.


MVP Deliverable


Chaos Agent suggests → “frontend pod looks critical, killing 1 pod.”


Chaos Mesh runs that experiment.



5. sre-copilot
📍 Scope: Minimal interactive assistant with 2–3 key queries
Include


Slack bot or Web UI with FastAPI backend.


2–3 hardwired queries:


“Why was pod X restarted?”


“What chaos tests ran today?”


“What was the last healing action?”


Stop Here


Don’t build full conversational memory.


Don’t support freeform complex queries.


MVP Deliverable


Judge types /sre why pod frontend restarted? → Copilot fetches logs + explanation + replies.



✅ Balanced Engineering Targets
metrics-collector → stop at 3–4 signals.


playbook-runner → stop at 3 healing rules.


explain-agent → stop at 2-sentence explanations.


chaos-agent → stop at 3 chaos types.


sre-copilot → stop at 3 queries.

