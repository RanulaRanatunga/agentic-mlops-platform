from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from components.k8s_fetcher import K8sLogFetcher
from components.k8s_executor import K8sExecutor

def build_remediation_pipeline():
    fetcher = K8sLogFetcher()
    executor = K8sExecutor()
    
    prompt_template = """
    You are an autonomous DevOps Agent.
    A Kubernetes pod has failed or triggered an alert. Analyze the following logs.
    
    Logs:
    {{ logs }}
    
    Determine the best course of action to fix the pod. You must output ONLY a raw JSON object with the following format, no other text:
    {
        "action": "restart_pod",
        "target": "pod_name",
        "namespace": "default",
        "reason": "brief explanation of the failure"
    }
    """
    
    prompt_builder = PromptBuilder(template=prompt_template)
    llm = OpenAIChatGenerator(model="gpt-4o")
    
    pipeline = Pipeline()
    pipeline.add_component("log_fetcher", fetcher)
    pipeline.add_component("prompt", prompt_builder)
    pipeline.add_component("llm", llm)
    pipeline.add_component("executor", executor)
    
    pipeline.connect("log_fetcher.logs", "prompt.logs")
    pipeline.connect("prompt.prompt", "llm.messages")
    pipeline.connect("llm.replies", "executor.replies")
    
    return pipeline