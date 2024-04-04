# HKETA-Server

## Requirement
- Python >= 3.10

## Run locally
Installing dependency
```bash
pip install -r requirements.txt
```

Start the server
```
uvicorn app.src.main:app
```

## Run Using Docker
Build the image
```bash
docker build .
```

Start the container
```bash
docker run "<IMAGE ID>" --name hketa-server
```
