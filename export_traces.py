import json
from dotenv import load_dotenv
from langsmith import Client

load_dotenv()  # loads LANGSMITH_API_KEY (and others) from .env
client = Client()

PROJECT = "langchain-research-agent"

runs = list(client.list_runs(
    project_name=PROJECT,
    is_root=True,           # top-level runs only (one per graph invocation)
    limit=20,
))

for run in runs:
    safe_name = run.name.replace(" ", "_").replace("/", "-")[:40]
    filename = f"traces/{run.id}_{safe_name}.json"
    with open(filename, "w") as f:
        json.dump(run.dict(), f, indent=2, default=str)
    share_url = client.share_run(run.id)
    print(f"Saved: {filename}")
    print(f"  Share URL: {share_url}")