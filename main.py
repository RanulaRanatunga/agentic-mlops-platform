from fastapi import FastAPI
from pydantic import BaseModel
from pipeline.agent_pipeline import build_remediation_pipeline
import os

app = FastAPI(title="Agentic Auto-Remediation Webhook Gateway")
mlops_agent = build_remediation_pipeline()

class AlertPayload(BaseModel):
    pod_name: str
    namespace: str = "default"
    alert_name: str = "PodCrashAlert"

@app.post("/webhook")
async def handle_alert(payload: AlertPayload):
    if not os.getenv("OPENAI_API_KEY"):
        return {"error": "OPENAI_API_KEY environment variable is missing."}
        
    pipeline_result = mlops_agent.run({
        "log_fetcher": {
            "pod_name": payload.pod_name,
            "namespace": payload.namespace
        }
    })
    
    return {
        "status": "Remediation Pipeline Executed",
        "action_taken": pipeline_result
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)