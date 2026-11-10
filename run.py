"""Run locally: python run.py. No external services are required."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("stock.web:create_app", factory=True, host="127.0.0.1", port=8765)
