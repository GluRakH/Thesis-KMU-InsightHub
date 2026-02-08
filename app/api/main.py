from fastapi import FastAPI

app = FastAPI(title="InsightHub API")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}
