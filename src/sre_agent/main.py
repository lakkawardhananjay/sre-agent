"""
SRE Agent FastAPI Application

A FastAPI application that integrates with Kubernetes API and Google Gemini API,
providing health checks and Prometheus metrics.
"""

import os
import time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import google.generativeai as genai
from kubernetes import client, config
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
KUBERNETES_PODS = Gauge('kubernetes_pods_total', 'Total number of Kubernetes pods')
HEALTH_STATUS = Gauge('application_health_status', 'Application health status (1=healthy, 0=unhealthy)')

# Models
class HealthResponse(BaseModel):
    status: str
    timestamp: float
    checks: Dict[str, bool]

class AnalysisRequest(BaseModel):
    query: str
    namespace: Optional[str] = "default"

class AnalysisResponse(BaseModel):
    query: str
    analysis: str
    kubernetes_context: Dict[str, Any]
    timestamp: float

# Global clients
k8s_client = None
gemini_model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global k8s_client, gemini_model
    
    # Initialize Kubernetes client
    try:
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            # Running inside Kubernetes cluster
            config.load_incluster_config()
        else:
            # Running outside cluster (development)
            config.load_kube_config()
        k8s_client = client.CoreV1Api()
        print("Kubernetes client initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Kubernetes client: {e}")
        k8s_client = None
    
    # Initialize Gemini
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel('gemini-pro')
            print("Gemini client initialized successfully")
        else:
            print("GEMINI_API_KEY not found in environment variables")
            gemini_model = None
    except Exception as e:
        print(f"Failed to initialize Gemini client: {e}")
        gemini_model = None
    
    yield
    
    # Cleanup (if needed)
    print("Application shutdown")

# FastAPI app
app = FastAPI(
    title="SRE Agent",
    description="A FastAPI application for SRE operations with Kubernetes and AI integration",
    version="1.0.0",
    lifespan=lifespan
)

def get_kubernetes_client():
    """Dependency to get Kubernetes client"""
    if k8s_client is None:
        raise HTTPException(status_code=503, detail="Kubernetes client not available")
    return k8s_client

def get_gemini_model():
    """Dependency to get Gemini model"""
    if gemini_model is None:
        raise HTTPException(status_code=503, detail="Gemini client not available")
    return gemini_model

@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Middleware to collect Prometheus metrics"""
    start_time = time.time()
    
    # Increment request counter
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    
    # Process request
    response = await call_next(request)
    
    # Record request duration
    duration = time.time() - start_time
    REQUEST_DURATION.observe(duration)
    
    return response

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    checks = {
        "kubernetes": k8s_client is not None,
        "gemini": gemini_model is not None,
    }
    
    # Test Kubernetes connection
    if k8s_client:
        try:
            k8s_client.list_namespace()
            checks["kubernetes_connectivity"] = True
        except Exception:
            checks["kubernetes_connectivity"] = False
    else:
        checks["kubernetes_connectivity"] = False
    
    # Determine overall health
    all_healthy = all(checks.values())
    status = "healthy" if all_healthy else "unhealthy"
    
    # Update health metric
    HEALTH_STATUS.set(1 if all_healthy else 0)
    
    return HealthResponse(
        status=status,
        timestamp=time.time(),
        checks=checks
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # Update Kubernetes pods metric
    if k8s_client:
        try:
            pods = k8s_client.list_pod_for_all_namespaces()
            KUBERNETES_PODS.set(len(pods.items))
        except Exception:
            pass
    
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SRE Agent API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "analyze": "/analyze",
            "docs": "/docs"
        }
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_cluster(
    request: AnalysisRequest,
    k8s: client.CoreV1Api = Depends(get_kubernetes_client),
    gemini: Any = Depends(get_gemini_model)
):
    """Analyze Kubernetes cluster with AI assistance"""
    try:
        # Gather Kubernetes context
        kubernetes_context = {}
        
        # Get pods in namespace
        try:
            pods = k8s.list_namespaced_pod(namespace=request.namespace)
            kubernetes_context["pods"] = [
                {
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "ready": sum(1 for condition in (pod.status.conditions or []) 
                               if condition.type == "Ready" and condition.status == "True"),
                    "restarts": sum(container.restart_count or 0 
                                  for container in (pod.status.container_statuses or []))
                }
                for pod in pods.items
            ]
        except Exception as e:
            kubernetes_context["pods_error"] = str(e)
        
        # Get services in namespace
        try:
            services = k8s.list_namespaced_service(namespace=request.namespace)
            kubernetes_context["services"] = [
                {
                    "name": svc.metadata.name,
                    "type": svc.spec.type,
                    "ports": [{"port": port.port, "target_port": port.target_port} 
                             for port in (svc.spec.ports or [])]
                }
                for svc in services.items
            ]
        except Exception as e:
            kubernetes_context["services_error"] = str(e)
        
        # Generate AI analysis
        prompt = f"""
        As an SRE expert, analyze the following Kubernetes cluster information and answer this query: {request.query}
        
        Namespace: {request.namespace}
        Kubernetes Context: {kubernetes_context}
        
        Please provide a comprehensive analysis including:
        1. Current state assessment
        2. Potential issues or concerns
        3. Recommendations for improvement
        4. Best practices suggestions
        """
        
        try:
            response = gemini.generate_content(prompt)
            analysis = response.text
        except Exception as e:
            analysis = f"AI analysis failed: {str(e)}"
        
        return AnalysisResponse(
            query=request.query,
            analysis=analysis,
            kubernetes_context=kubernetes_context,
            timestamp=time.time()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/cluster/pods")
async def list_pods(
    namespace: str = "default",
    k8s: client.CoreV1Api = Depends(get_kubernetes_client)
):
    """List pods in a namespace"""
    try:
        pods = k8s.list_namespaced_pod(namespace=namespace)
        return {
            "namespace": namespace,
            "pods": [
                {
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "node": pod.spec.node_name,
                    "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                    "labels": pod.metadata.labels or {}
                }
                for pod in pods.items
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pods: {str(e)}")

@app.get("/cluster/namespaces")
async def list_namespaces(k8s: client.CoreV1Api = Depends(get_kubernetes_client)):
    """List all namespaces"""
    try:
        namespaces = k8s.list_namespace()
        return {
            "namespaces": [
                {
                    "name": ns.metadata.name,
                    "status": ns.status.phase,
                    "created": ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else None,
                    "labels": ns.metadata.labels or {}
                }
                for ns in namespaces.items
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list namespaces: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )