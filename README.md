# SRE Agent

A comprehensive FastAPI application designed for Site Reliability Engineering (SRE) operations, integrating with Kubernetes API and Google Gemini AI for intelligent cluster analysis and monitoring.

## Features

- 🚀 **FastAPI Framework**: High-performance, modern API with automatic documentation
- ☸️ **Kubernetes Integration**: Direct API access for cluster monitoring and analysis
- 🤖 **AI-Powered Analysis**: Google Gemini integration for intelligent cluster insights
- 📊 **Prometheus Metrics**: Built-in metrics collection and monitoring
- 🐳 **Containerized**: Docker support for easy deployment
- ☁️ **GKE Ready**: Optimized for Google Kubernetes Engine deployment
- 🔒 **Security**: RBAC, security contexts, and best practices implemented
- 🏥 **Health Checks**: Comprehensive health monitoring endpoints

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional, for containerization)
- kubectl (for Kubernetes deployment)
- Google Cloud SDK (for GKE deployment)
- Gemini API Key (optional, for AI features)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/lakkawardhananjay/sre-agent.git
   cd sre-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   python -m uvicorn src.sre_agent.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Metrics: http://localhost:8000/metrics

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t sre-agent:latest .
   ```

2. **Run with Docker Compose** (includes Prometheus)
   ```bash
   docker-compose up -d
   ```

3. **Access services**
   - SRE Agent: http://localhost:8000
   - Prometheus: http://localhost:9090

### GKE Deployment

1. **Quick deployment**
   ```bash
   ./deploy-gke.sh YOUR_PROJECT_ID cluster-name us-central1-a us-central1 YOUR_GEMINI_API_KEY
   ```

2. **Manual deployment**
   ```bash
   # Build and push image
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/sre-agent:latest .
   
   # Update deployment.yaml with your project ID
   sed -i 's/PROJECT_ID/YOUR_PROJECT_ID/g' k8s/deployment.yaml
   
   # Deploy to cluster
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/prometheus.yaml
   ```

## API Endpoints

### Core Endpoints

- `GET /` - API information and available endpoints
- `GET /health` - Health check with component status
- `GET /metrics` - Prometheus metrics endpoint
- `GET /docs` - Interactive API documentation

### Kubernetes Operations

- `GET /cluster/pods?namespace=default` - List pods in namespace
- `GET /cluster/namespaces` - List all namespaces
- `POST /analyze` - AI-powered cluster analysis

### Example API Usage

**Health Check**
```bash
curl http://localhost:8000/health
```

**List Pods**
```bash
curl "http://localhost:8000/cluster/pods?namespace=kube-system"
```

**AI Analysis**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze the current cluster health and suggest optimizations",
    "namespace": "default"
  }'
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Application environment | `development` |
| `PORT` | Server port | `8000` |
| `GEMINI_API_KEY` | Google Gemini API key | - |
| `KUBERNETES_SERVICE_HOST` | K8s API host (auto-detected in cluster) | - |

### Kubernetes Configuration

The application requires specific RBAC permissions to access Kubernetes APIs:
- `pods`, `services`, `endpoints`, `namespaces`, `nodes` (get, list, watch)
- `deployments`, `replicasets` (get, list, watch)
- `ingresses` (get, list, watch)

## Monitoring

### Prometheus Metrics

The application exposes the following metrics:

- `http_requests_total` - Total HTTP requests counter
- `http_request_duration_seconds` - Request duration histogram
- `kubernetes_pods_total` - Total number of Kubernetes pods
- `application_health_status` - Application health status gauge

### Health Checks

The `/health` endpoint provides detailed health information:
- Kubernetes connectivity
- Gemini API availability
- Overall application status

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Kubernetes    │    │   Google AI     │
│                 │◄──►│      API        │    │    (Gemini)     │
│  - Health       │    │                 │    │                 │
│  - Metrics      │    │  - Pods         │    │  - Analysis     │
│  - Analysis     │    │  - Services     │    │  - Insights     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│   Prometheus    │
│   Monitoring    │
│                 │
│  - Metrics      │
│  - Alerts       │
└─────────────────┘
```

## Development

### Project Structure

```
sre-agent/
├── src/
│   └── sre_agent/
│       ├── __init__.py
│       └── main.py          # FastAPI application
├── k8s/
│   ├── deployment.yaml      # Kubernetes manifests
│   └── prometheus.yaml      # Prometheus deployment
├── monitoring/
│   └── prometheus.yml       # Prometheus configuration
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Local development
├── requirements.txt         # Python dependencies
├── deploy-gke.sh           # GKE deployment script
└── README.md               # This file
```

### Adding New Features

1. Update the FastAPI application in `src/sre_agent/main.py`
2. Add new endpoints following the existing patterns
3. Update Kubernetes manifests if needed
4. Test locally with Docker Compose
5. Deploy to GKE using the deployment script

### Testing

```bash
# Install test dependencies
pip install pytest httpx

# Run tests (when available)
pytest

# Test health endpoint
curl http://localhost:8000/health

# Test metrics
curl http://localhost:8000/metrics
```

## Security

- Non-root container user
- Read-only root filesystem
- Security contexts with dropped capabilities
- RBAC with minimal required permissions
- Secret management for API keys

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the [API documentation](http://localhost:8000/docs)
2. Review the health endpoint status
3. Check application logs: `kubectl logs -f deployment/sre-agent -n sre-agent`
4. Open an issue in the repository

## Roadmap

- [ ] Advanced AI analysis capabilities
- [ ] Alert management integration
- [ ] Multi-cluster support
- [ ] Custom metrics and dashboards
- [ ] Integration with other monitoring tools
- [ ] GitOps workflow support