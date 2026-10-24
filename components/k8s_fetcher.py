from haystack import component
from kubernetes import client, config

@component
class K8sLogFetcher:
    def __init__(self):
        try:
            config.load_kube_config()
        except Exception as e:
            print(f"Warning: Could not load local kubeconfig: {e}")
        self.v1 = client.CoreV1Api()

    @component.output_types(logs=str)
    def run(self, pod_name: str, namespace: str):
        try:
            logs = self.v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=50)
            return {"logs": logs}
        except Exception as e:
            return {"logs": f"Error fetching logs for {pod_name}: {str(e)}"}