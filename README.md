# agentic-mlops-platform

A lightweight prototype exploring autonomous Kubernetes incident remediation using Haystack AI and GPT-4o.

## The Idea

When a pod crashes in a cluster (for example, an ML job runs out of memory or a service panics on startup), the typical engineer response is:
1. Receive an alert from Alertmanager, Datadog, or PagerDuty.
2. Check `kubectl logs <pod>` to see what blew up.
3. Apply a fix—often starting with restarting the pod, clearing a lock, or rolling back.

This repo is a minimal proof-of-concept that automates that triage loop:
- Exposes a webhook endpoint (`POST /webhook`) that receives failure alerts.
- Uses the Kubernetes Python client to pull recent logs directly from the failing pod.
- Hands the logs to an LLM via a Haystack 3 pipeline to diagnose the error and propose an action.
- Executes the chosen action (e.g., deleting the crashing pod so the ReplicaSet spins up a fresh one).

## Project Layout

- `main.py` - FastAPI entrypoint running the webhook receiver.
- `pipeline/agent_pipeline.py` - Wires up the Haystack pipeline: log fetcher &rarr; prompt template &rarr; OpenAI chat &rarr; action executor.
- `components/k8s_fetcher.py` - Haystack component that reads logs from the Kubernetes CoreV1 API.
- `components/k8s_executor.py` - Haystack component that parses the model's JSON response and executes cluster operations.
- `k8s/test_deployment.yaml` - A minimal deployment running a busybox container that prints a simulated `OOMKilled` error and exits with code 1 for testing.

## Prerequisites

1. **A Kubernetes cluster running locally**:
   - If using **Docker Desktop**, go to **Settings &rarr; Kubernetes** and check **Enable Kubernetes**.
   - Alternatively, use **Minikube** (`minikube start`) or **kind**.
   - Verify it's ready: `kubectl get nodes`
2. **Python 3.10+**
3. **OpenAI API Key** with GPT-4o access.

## Quickstart

### 1. Set up the virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. Start the webhook server

Set your OpenAI API key and run `main.py`:

```powershell
$env:OPENAI_API_KEY = "sk-..."
python main.py
```

The server will start on `http://localhost:8000`.

### 3. Deploy the crashing test app

In a second terminal, deploy the test workload:

```powershell
kubectl apply -f k8s/test_deployment.yaml
```

Check the pod status:
```powershell
kubectl get pods -l app=crashing-ml-app
```
You should see the pod crashing with `Error` or `CrashLoopBackOff`.

### 4. Trigger the remediation webhook

Grab the name of the failing pod and simulate an alert trigger:

```powershell
$POD = (kubectl get pods -l app=crashing-ml-app -o jsonpath="{.items[0].metadata.name}")

curl.exe -X POST "http://localhost:8000/webhook" `
  -H "Content-Type: application/json" `
  -d "{`"pod_name`": `"$POD`", `"namespace`": `"default`"}"
```

### What happens behind the scenes

1. FastAPI receives the alert payload (`pod_name`, `namespace`).
2. `K8sLogFetcher` pulls the tail logs from the pod via `CoreV1Api.read_namespaced_pod_log()`:
   ```text
   Starting ML Inference...
   FATAL ERROR: Out of memory (OOMKilled)
   ```
3. Haystack formats the prompt and sends it to GPT-4o, which responds with structured JSON:
   ```json
   {
     "action": "restart_pod",
     "target": "crashing-ml-app-...",
     "namespace": "default",
     "reason": "Process exited due to fatal out of memory error."
   }
   ```
4. `K8sExecutor` parses the action and deletes the pod via `delete_namespaced_pod()`.
5. The Kubernetes deployment controller notices the deleted pod and starts a replacement replica.

## Notes & Future Ideas

- **Production safety**: Currently, the agent immediately deletes pods when requested. In a real-world setup, you'd want guardrails, an allowed namespace whitelist, rate limiting, and human-in-the-loop approvals for non-trivial workloads.
- **Smarter remediation**: Simply restarting an OOM pod usually just leads back into another crash. A natural progression is patching the Deployment's memory limits or switching to a lighter model checkpoint.
- **Alertmanager integration**: Configure this endpoint directly as a webhook receiver in Prometheus Alertmanager to handle `KubePodCrashLooping` alerts automatically.
