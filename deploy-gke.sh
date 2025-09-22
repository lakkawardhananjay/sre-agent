#!/bin/bash

# GKE Deployment Script for SRE Agent
# This script deploys the SRE Agent application to Google Kubernetes Engine

set -e

# Configuration
PROJECT_ID=${1:-"your-gcp-project"}
CLUSTER_NAME=${2:-"sre-agent-cluster"}
ZONE=${3:-"us-central1-a"}
REGION=${4:-"us-central1"}
GEMINI_API_KEY=${5:-""}

echo "🚀 Starting GKE deployment for SRE Agent"
echo "Project: $PROJECT_ID"
echo "Cluster: $CLUSTER_NAME"
echo "Zone: $ZONE"

# Validate inputs
if [ "$PROJECT_ID" = "your-gcp-project" ]; then
    echo "❌ Please provide a valid GCP Project ID"
    echo "Usage: $0 <PROJECT_ID> [CLUSTER_NAME] [ZONE] [REGION] [GEMINI_API_KEY]"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  Warning: GEMINI_API_KEY not provided. AI features will be disabled."
    echo "You can set it later by updating the secret in Kubernetes."
fi

# Set the project
echo "📝 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required GCP APIs..."
gcloud services enable container.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Create GKE cluster if it doesn't exist
echo "🏗️  Creating GKE cluster (if it doesn't exist)..."
if ! gcloud container clusters describe $CLUSTER_NAME --zone=$ZONE >/dev/null 2>&1; then
    gcloud container clusters create $CLUSTER_NAME \
        --zone=$ZONE \
        --num-nodes=3 \
        --enable-autoscaling \
        --min-nodes=1 \
        --max-nodes=5 \
        --machine-type=e2-standard-2 \
        --disk-size=50GB \
        --enable-autorepair \
        --enable-autoupgrade \
        --enable-network-policy \
        --addons=HorizontalPodAutoscaling,HttpLoadBalancing \
        --workload-pool=$PROJECT_ID.svc.id.goog
    echo "✅ Cluster created successfully"
else
    echo "✅ Cluster already exists"
fi

# Get cluster credentials
echo "🔐 Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE

# Build and push Docker image
echo "🐳 Building and pushing Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/sre-agent:latest .

# Update Kubernetes manifests with project ID
echo "📄 Updating Kubernetes manifests..."
sed -i "s/PROJECT_ID/$PROJECT_ID/g" k8s/deployment.yaml

# Create namespace
echo "🏠 Creating namespace..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: sre-agent
  labels:
    name: sre-agent
EOF

# Create or update secret with Gemini API key
if [ -n "$GEMINI_API_KEY" ]; then
    echo "🔑 Creating secret with Gemini API key..."
    kubectl create secret generic sre-agent-secrets \
        --from-literal=GEMINI_API_KEY=$GEMINI_API_KEY \
        --namespace=sre-agent \
        --dry-run=client -o yaml | kubectl apply -f -
else
    echo "⚠️  Creating empty secret (please update with Gemini API key later)..."
    kubectl create secret generic sre-agent-secrets \
        --from-literal=GEMINI_API_KEY="" \
        --namespace=sre-agent \
        --dry-run=client -o yaml | kubectl apply -f -
fi

# Deploy application
echo "🚀 Deploying application..."
kubectl apply -f k8s/deployment.yaml

# Deploy Prometheus monitoring
echo "📊 Deploying Prometheus monitoring..."
kubectl apply -f k8s/prometheus.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/sre-agent -n sre-agent

# Get service information
echo "📋 Getting service information..."
kubectl get services -n sre-agent
kubectl get ingress -n sre-agent

# Get external IP (if using LoadBalancer)
echo "🌐 Getting external access information..."
echo ""
echo "Application endpoints:"
echo "- Health check: http://<EXTERNAL_IP>/health"
echo "- Metrics: http://<EXTERNAL_IP>/metrics"
echo "- API docs: http://<EXTERNAL_IP>/docs"
echo "- Prometheus: http://<PROMETHEUS_IP>:9090"
echo ""

# Create static IP for ingress (optional)
echo "📍 Creating static IP for ingress..."
if ! gcloud compute addresses describe sre-agent-ip --region=$REGION >/dev/null 2>&1; then
    gcloud compute addresses create sre-agent-ip --region=$REGION
    echo "✅ Static IP created"
else
    echo "✅ Static IP already exists"
fi

STATIC_IP=$(gcloud compute addresses describe sre-agent-ip --region=$REGION --format="value(address)")
echo "Static IP: $STATIC_IP"

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Update DNS to point your domain to: $STATIC_IP"
echo "2. Update the ingress host in k8s/deployment.yaml with your domain"
echo "3. If you didn't provide a Gemini API key, update the secret:"
echo "   kubectl patch secret sre-agent-secrets -n sre-agent -p '{\"data\":{\"GEMINI_API_KEY\":\"<base64-encoded-api-key>\"}}'"
echo "4. Monitor the application:"
echo "   kubectl logs -f deployment/sre-agent -n sre-agent"
echo "5. Access Prometheus at: http://<PROMETHEUS_SERVICE_IP>:9090"