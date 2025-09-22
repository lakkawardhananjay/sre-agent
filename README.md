# 🚀 SRE-Agent: A Kubernetes Self-Healing Operator for Financial Services

SRE-Agent is a **Kubernetes-native operator** that brings **automated self-healing** and **AI-powered root cause analysis (RCA)** to the demanding environment of **financial services applications**.  
It was built as part of the **Bank of Anthos** project to demonstrate how Site Reliability Engineering (SRE) principles can improve reliability and resilience in **mission-critical banking systems**.

---

## 🌍 Why SRE Matters in Banking

In financial services, downtime is **extremely costly**—not just financially, but also reputationally.  
As banks adopt **cloud-native** technologies and **microservices**, complexity increases and failures become harder to manage.

### Key Challenges:
- ⚠️ **Slow Incident Response** – Manual fixes can take hours.
- 😓 **Toil & Burnout** – Repetitive manual ops cause fatigue and errors.
- 🛑 **Reactive Mode** – Teams firefight instead of preventing issues.

---

## 💰 The Financial Impact of Downtime

- **$152M/year** – Average annual loss due to downtime for large financial firms.  
- **$9,000/minute** – Average cost of downtime across industries.  
- **$5M/hour** – Potential cost of outages in banking/finance.  
- **48%** of financial firms experience a “high-impact” outage **weekly**.  

👉 These numbers make **automation and self-healing a necessity**.

---

## 🎯 Why We Built SRE-Agent

We designed SRE-Agent to:

- 🤖 **Automate Incident Response** – Detect & remediate failures (pod crashes, resource contention) instantly.  
- 🔄 **Reduce Toil** – Free ops teams from repetitive fixes.  
- 🧠 **Provide Actionable Insights** – AI-powered RCA via **Google Gemini API**.  
- ⚙️ **Stay Flexible** – YAML-based healing rules for easy customization.  

---

## 🧠 AI + SRE: A New Era

- 🔍 **AI-Powered RCA** – Analyze logs & metrics with `kubectl-ai` + Gemini.  
- 🛠️ **Automated Remediation** – Take corrective actions automatically.  
- 💸 **FinOps & Cost Optimization** – Identify and remove waste.  

---

## ✨ Features

- 📜 **Rule-Based Healing** – YAML playbooks for custom rules.  
- ☸️ **Kubernetes-Native Operator** – Uses Kubernetes API.  
- 📊 **Prometheus Integration** – Metric-driven healing actions.  
- 🤖 **AI-Powered RCA** – Google Gemini integration.  
- 🔒 **Leader Election** – Prevents conflicting actions.  
- 🧩 **Configurable & Extensible** – Add new rules easily.  
- 🧪 **Dry-Run Mode** – Safe testing before applying fixes.  
- 🌐 **REST API** – For manual interventions & status checks.  

---

## 📊 Impact & ROI

- ⏱️ **Reduce MTTR** – 5x faster incident resolution (inspired by Netflix/Etsy practices).  
- 💸 **Cut Cloud Costs** – Up to **28–32% savings** via automation.  
- 😌 **Reduce Toil** – More focus on strategy, less on firefighting.  

---

## 🏗️ Architecture

The SRE-Agent integrates with Kubernetes and Prometheus to detect, heal, and analyze failures automatically.  

### Visual Flow
<img width="648" height="730" alt="Image" src="https://github.com/user-attachments/assets/793de75f-21af-44e1-86af-e7818520aa67" />


````markdown
## ⚡ Getting Started

### ✅ Prerequisites
- A Kubernetes cluster (GKE preferred)  
- `kubectl` configured  
- Prometheus installed (optional)  
- Google Cloud project with Gemini API enabled  

---

### ⚙️ Configuration

**Define healing rules:**
```bash
kubectl create configmap sre-agent-playbook --from-file=healing-playbook.yaml
````

**Set Gemini API key:**

```bash
export GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>
```

---

### 🚀 Deployment

**Build & push Docker image:**

```bash
docker build -t gcr.io/<YOUR_PROJECT_ID>/sre-agent:latest .
docker push gcr.io/<YOUR_PROJECT_ID>/sre-agent:latest
```

**Apply Kubernetes manifests:**

```bash
kubectl apply -f kubernetes-manifests/sre-agent.yaml
```

---

### 🧩 How It Works

* Runs as a Kubernetes Deployment
* Uses leader election for high availability (HA)
* Continuously monitors cluster events & metrics
* Executes healing rules (e.g., restarts `CrashLoopBackOff` pods)
* Triggers RCA via Gemini API for detailed insights
