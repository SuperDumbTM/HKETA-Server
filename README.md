# HKETA-Server
A web server built with FastAPI that provides normalised APIs for public transport of Hong Kong.

Additionally, the server utilised mechine learning to give prediction on the accuracy of ETAs (for KMB and MTR Bus only). Dataset (up to three months worth of data) for ML will be automatically gathered periodly.

## Deployment
### Run locally

- Python >= 3.10

Installing dependency
```bash
pip install -r requirements.txt
```

Start the server
```
uvicorn app.src.main:app
```

### Run Using Docker
Build the image
```bash
docker build .
```

Start the container
```bash
docker run "<IMAGE ID>" --name hketa-server
```
