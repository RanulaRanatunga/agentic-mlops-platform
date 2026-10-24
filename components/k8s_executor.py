from haystack import component
from haystack.dataclasses import ChatMessage
from kubernetes import client, config
import json

@component
class K8sExecutor:
    def __init__(self):
        try:
            config.load_kube_config()
        except:
            pass
        self.v1 = client.CoreV1Api()

    @component.output_types(result=str)
    def run(self, replies: list[ChatMessage] | list[str]):
        if not replies:
            return {"result": "No replies received from LLM"}
        first_reply = replies[0]
        action_payload = getattr(first_reply, "text", str(first_reply))
        try:
            clean_json = action_payload.replace('```json', '').replace('```', '').strip()
            command = json.loads(clean_json)
            
            action = command.get("action")
            target = command.get("target")
            ns = command.get("namespace", "default")
            
            if action == "restart_pod":
                self.v1.delete_namespaced_pod(name=target, namespace=ns)
                return {"result": f"Successfully deleted pod {target} in {ns}"}
            else:
                return {"result": f"Unrecognized action: {action}"}
        except Exception as e:
            return {"result": f"Execution failed: {str(e)}"}