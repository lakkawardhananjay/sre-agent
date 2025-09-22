#!/usr/bin/env python3
"""
SRE-Agent: Kubernetes Self-Healing Agent
GKE Turns 10 Hackathon - Day 2 MVP + Gemini RCA Integration
"""
import logging
import asyncio
from pythonjsonlogger import jsonlogger
logger = logging.getLogger("sre-agent")
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
import os
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from kubernetes import client, config, watch
from kubernetes.leaderelection import leaderelection
from kubernetes.leaderelection import resourcelock
from kubernetes.client.rest import ApiException
from requests.auth import HTTPBasicAuth
import requests
from starlette_prometheus import PrometheusMiddleware, metrics
from prometheus_client import Counter

# --- NEW: Gemini imports ---
import google.generativeai as genai

from pythonjsonlogger import jsonlogger

# Configure logging
logger = logging.getLogger("sre-agent")
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# --- NEW: Configure Gemini API ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Storage for last RCA
last_rca = {"pod": None, "rca": None}


# ------------------ DATA MODELS ------------------
@dataclass
class HealingRule:
    name: str
    condition: str
    threshold: int
    action: str
    namespace: str = "default"
    enabled: bool = True

@dataclass
class AgentMetrics:
    rules_processed: int = 0
    healing_actions: int = 0
    last_check: Optional[datetime] = None
    errors: int = 0


# ------------------ KUBERNETES CLIENT ------------------
class KubernetesClient:
    """Kubernetes API client wrapper"""
    
    def __init__(self):
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except:
            try:
                config.load_kube_config()
                logger.info("Loaded local Kubernetes config")
            except Exception as e:
                logger.error(f"Failed to load Kubernetes config: {e}")
                raise
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()
    
    async def get_pod_logs(self, pod_name: str, namespace: str = "default", 
                          tail_lines: int = 100) -> str:
        try:
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail_lines
            )
            return logs
        except ApiException as e:
            logger.error(f"Error fetching logs for pod {pod_name}: {e}")
            return f"Error fetching logs: {e}"
    
    async def get_pods_by_status(self, namespace: str = "default") -> Dict[str, List[str]]:
        try:
            pods = self.v1.list_namespaced_pod(namespace=namespace)
            status_map = {}
            
            for pod in pods.items:
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        if container.state.waiting:
                            reason = container.state.waiting.reason
                            if reason not in status_map:
                                status_map[reason] = []
                            status_map[reason].append(pod.metadata.name)
                        elif container.restart_count > 0:
                            if "RestartCount" not in status_map:
                                status_map["RestartCount"] = []
                            status_map["RestartCount"].append(
                                f"{pod.metadata.name}:{container.restart_count}"
                            )
            
            return status_map
        except ApiException as e:
            logger.error(f"Error getting pod status: {e}")
            return {}
    
    async def restart_pod(self, pod_name: str, namespace: str = "default") -> bool:
        try:
            self.v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            logger.info(f"Initiated restart for pod {pod_name} in namespace {namespace}")
            return True
        except ApiException as e:
            logger.error(f"Error restarting pod {pod_name}: {e}")
            return False
    
    async def get_pod_description(self, pod_name: str, namespace: str = "default") -> str:
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            return str(pod)
        except ApiException as e:
            logger.error(f"Error fetching pod description for {pod_name}: {e}")
            return f"Error fetching pod description: {e}"

    async def get_namespace_events(self, namespace: str = "default", limit: int = 20) -> str:
        try:
            events = self.v1.list_namespaced_event(namespace=namespace, limit=limit)
            return str(events)
        except ApiException as e:
            logger.error(f"Error fetching events for namespace {namespace}: {e}")
            return f"Error fetching events: {e}"

    async def scale_deployment(self, deployment_name: str, replicas: int, 
                              namespace: str = "default") -> bool:
        try:
            body = {"spec": {"replicas": replicas}}
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body=body
            )
            logger.info(f"Scaled deployment {deployment_name} to {replicas} replicas")
            return True
        except ApiException as e:
            logger.error(f"Error scaling deployment {deployment_name}: {e}")
            return False


# ------------------ PROMETHEUS CLIENT ------------------
class PrometheusClient:
    """Prometheus API client"""
    
    def __init__(self, prometheus_url: str, username: str = None, password: str = None):
        self.prometheus_url = prometheus_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password) if username and password else None
    
    async def query(self, query: str) -> Dict[str, Any]:
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {'query': query}
            
            response = requests.get(url, params=params, auth=self.auth, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return {}
    
    async def get_pod_restart_count(self, namespace: str = "default") -> Dict[str, int]:
        query = f'kube_pod_container_status_restarts_total{{namespace="{namespace}"}}'
        try:
            result = await self.query(query)
            restart_counts = {}
            
            if result.get('status') == 'success':
                for item in result['data']['result']:
                    pod_name = item['metric']['pod']
                    count = int(float(item['value'][1]))
                    restart_counts[pod_name] = count
            
            return restart_counts
        except Exception as e:
            logger.error(f"Error getting restart counts: {e}")
            return {}


# ------------------ RULE ENGINE ------------------
class RuleEngine:
    """Rule evaluation and execution engine"""
    
    def __init__(self, k8s_client: KubernetesClient, prometheus_client: PrometheusClient):
        self.k8s_client = k8s_client
        self.prometheus_client = prometheus_client
        self.rules: List[HealingRule] = []
        self.metrics = AgentMetrics()
        self.action_cooldowns: Dict[str, datetime] = {}
    
    def load_rules(self, rules_config: List[Dict[str, Any]]):
        self.rules = []
        for rule_config in rules_config:
            rule = HealingRule(
                name=rule_config['name'],
                condition=rule_config['condition'],
                threshold=rule_config['threshold'],
                action=rule_config['action'],
                namespace=rule_config.get('namespace', 'default'),
                enabled=rule_config.get('enabled', True)
            )
            self.rules.append(rule)
        
        logger.info(f"Loaded {len(self.rules)} healing rules")
    
    async def evaluate_rules(self):
        self.metrics.last_check = datetime.now()
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                self.metrics.rules_processed += 1
                should_heal = await self._evaluate_condition(rule)
                
                if should_heal:
                    logger.info(f"Rule '{rule.name}' triggered, executing action: {rule.action}")
                    success = await self._execute_action(rule)
                    if success:
                        self.metrics.healing_actions += 1
            
            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.name}': {e}")
                self.metrics.errors += 1
    
    async def _evaluate_condition(self, rule: HealingRule) -> bool:
        if rule.condition == "CrashLoopBackOff":
            pod_statuses = await self.k8s_client.get_pods_by_status(rule.namespace)
            crash_pods = pod_statuses.get("CrashLoopBackOff", [])
            return len(crash_pods) > rule.threshold
        
        elif rule.condition == "RestartCount":
            restart_counts = await self.prometheus_client.get_pod_restart_count(rule.namespace)
            high_restart_pods = [pod for pod, count in restart_counts.items() 
                               if count > rule.threshold]
            return len(high_restart_pods) > 0
        
        elif rule.condition == "PodPending":
            pod_statuses = await self.k8s_client.get_pods_by_status(rule.namespace)
            pending_pods = pod_statuses.get("Pending", [])
            return len(pending_pods) > rule.threshold
        
        return False
    
    async def _execute_action(self, rule: HealingRule) -> bool:
        # --- NEW: Safety checks ---
        healing_enabled = os.getenv("HEALING_ENABLED", "false").lower() == "true"
        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

        if not healing_enabled:
            logger.info(f"DRY_RUN: Healing is globally disabled. Would have performed action '{rule.action}'.")
            return False

        if dry_run:
            logger.info(f"DRY_RUN: Agent is in dry-run mode. Would have performed action '{rule.action}'.")
            return False
        # --- END NEW ---

        if rule.action == "restart_pod":
            if rule.condition == "CrashLoopBackOff":
                pod_statuses = await self.k8s_client.get_pods_by_status(rule.namespace)
                crash_pods = pod_statuses.get("CrashLoopBackOff", [])
                
                for pod_name in crash_pods[:1]: # Note: We'll improve this later
                    # --- NEW: Cooldown check ---
                    cooldown_key = f"restart_pod:{rule.namespace}/{pod_name}"
                    now = datetime.now()
                    if cooldown_key in self.action_cooldowns:
                        if now < self.action_cooldowns[cooldown_key] + timedelta(minutes=15): # 15 min cooldown
                            logger.warning(f"Cooldown active for {cooldown_key}. Skipping action.")
                            return False
                    # --- END NEW ---
                    
                    success = await self.k8s_client.restart_pod(pod_name, rule.namespace)

                    if success:
                        self.action_cooldowns[cooldown_key] = now # Set the cooldown timer
                        # --- NEW: Increment the Prometheus metric ---
                        HEALING_ACTIONS_TOTAL.labels(rule_name=rule.name, action=rule.action, namespace=rule.namespace).inc()

                    # --- NEW: RCA Step ---
                    logs = await self.k8s_client.get_pod_logs(pod_name, rule.namespace)
                    alerts = await self.prometheus_client.query('up == 0')
                    pod_description = await self.k8s_client.get_pod_description(pod_name, rule.namespace)
                    events = await self.k8s_client.get_namespace_events(rule.namespace)
                    rca_text = await analyze_root_cause(logs, alerts, pod_description, events)
                    last_rca["pod"] = pod_name
                    last_rca["rca"] = rca_text
                    logger.info(f"🤖 RCA for {pod_name}: {rca_text}")

                    return success
        
        elif rule.action.startswith("scale_deployment"):
            parts = rule.action.split(":")
            if len(parts) == 3:
                deployment_name = parts[1]
                replicas = int(parts[2])
                return await self.k8s_client.scale_deployment(
                    deployment_name, replicas, rule.namespace
                )
        
        return False


# ------------------ GEMINI RCA HELPER ------------------
async def analyze_root_cause(logs: str, alerts: dict, pod_description: str, events: str) -> str:
    prompt = f"""
    As an expert Google SRE, your task is to provide a root cause analysis (RCA) for a failing Kubernetes pod.
    Analyze the following contextual information to determine the most likely cause of failure and suggest a concrete solution.

    **Context 1: Pod Description**
    This is the output of `kubectl describe pod`. It contains the pod's configuration, status, and associated node information.
    ```
    {pod_description}
    ```

    **Context 2: Recent Pod Logs (Last 100 lines)**
    These are the logs emitted by the application running inside the container just before it was restarted.
    ```
    {logs}
    ```

    **Context 3: Recent Kubernetes Events**
    These are events from the pod's namespace, which might include scheduling failures, health check probes failing (Liveness/Readiness), or volume mounting issues.
    ```
    {events}
    ```
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"RCA analysis failed: {str(e)}"


# ------------------ FASTAPI APP ------------------
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- your startup code ---
    global k8s_client, prometheus_client, rule_engine
    k8s_client = KubernetesClient()
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
    prometheus_user = os.getenv("PROMETHEUS_USER")
    prometheus_pass = os.getenv("PROMETHEUS_PASSWORD")
    prometheus_client = PrometheusClient(prometheus_url, prometheus_user, prometheus_pass)
    rule_engine = RuleEngine(k8s_client, prometheus_client)
    await load_healing_playbook()
    # --- leader election setup ---
    pod_name = os.getenv("POD_NAME", "sre-agent-pod-1") # Default for local dev
    namespace = os.getenv("NAMESPACE", "default")
    lock_name = "sre-agent-leader-election-lock"

    lock = resourcelock.ConfigMapLock(
        k8s_client.v1,
        lock_name,
        namespace,
        pod_name
    )

    lec = leaderelection.LeaderElectionConfig(
        lock=lock,
        lease_duration=15,
        renew_deadline=10,
        retry_period=2,
        callbacks=leaderelection.LeaderCallbacks(
            start_leading=become_leader,
            stop_leading=revoke_leader,
        )
    )

    le = leaderelection.LeaderElector(lec)
    asyncio.create_task(le.run())

    yield
    # (Optional) cleanup code here

app = FastAPI(
    title="SRE-Agent",
    description="Kubernetes Self-Healing Agent for GKE with Gemini RCA",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics) # This replaces your custom /metrics endpoint

# --- NEW: Custom Metrics ---
HEALING_ACTIONS_TOTAL = Counter("sre_agent_healing_actions_total", "Total healing actions taken", ["rule_name", "action", "namespace"])
k8s_client = None
prometheus_client = None
rule_engine = None
_rule_evaluation_task = None

# --- NEW: Leader Election Callbacks ---
def become_leader():
    """Callback function when this instance becomes the leader."""
    global _rule_evaluation_task
    logger.info("This pod is now the leader!")
    _rule_evaluation_task = asyncio.create_task(rule_evaluation_loop())

def revoke_leader():
    """Callback function when this instance stops being the leader."""
    global _rule_evaluation_task
    logger.warning("This pod is no longer the leader!")
    if _rule_evaluation_task:
        _rule_evaluation_task.cancel()

async def load_healing_playbook():
    playbook_path = os.getenv("PLAYBOOK_PATH", "/app/healing-playbook.yaml")
    
    try:
        with open(playbook_path, 'r') as file:
            playbook = yaml.safe_load(file)
            rule_engine.load_rules(playbook.get('rules', []))
    except FileNotFoundError:
        logger.warning(f"Playbook file not found at {playbook_path}, using default rules")
        default_rules = [
            {
                "name": "restart-crashloop-pods",
                "condition": "CrashLoopBackOff",
                "threshold": 0,
                "action": "restart_pod",
                "namespace": "default",
                "enabled": True
            }
        ]
        rule_engine.load_rules(default_rules)

async def rule_evaluation_loop():
    while True:
        try:
            await rule_engine.evaluate_rules()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Error in rule evaluation loop: {e}")
            await asyncio.sleep(60)


# ------------------ API ENDPOINTS ------------------
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}



@app.get("/pods/{namespace}")
async def get_pods_status(namespace: str = "default"):
    try:
        status_map = await k8s_client.get_pods_by_status(namespace)
        return {"namespace": namespace, "pod_statuses": status_map}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{namespace}/{pod_name}")
async def get_pod_logs(namespace: str, pod_name: str, tail_lines: int = 100):
    try:
        logs = await k8s_client.get_pod_logs(pod_name, namespace, tail_lines)
        return {"pod": pod_name, "namespace": namespace, "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/heal/{namespace}/{pod_name}")
async def manual_heal_pod(namespace: str, pod_name: str):
    try:
        success = await k8s_client.restart_pod(pod_name, namespace)
        if success:
            return {"status": "success", "message": f"Pod {pod_name} restart initiated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to restart pod")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/prometheus/query")
async def query_prometheus(query: dict):
    try:
        result = await prometheus_client.query(query["query"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- NEW: RCA API ---
@app.get("/rca")
async def get_last_rca():
    return last_rca




