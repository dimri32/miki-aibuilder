# Realtime Streaming

This folder contains the implementation and resources for real-time streaming functionality in the `ci-truefoundry-endpoints` project.


## Overview

The real-time streaming module is designed to handle continuous data streams efficiently. It integrates with external streaming platforms and provides tools for processing, transforming, and analyzing data in real-time.

### Key Features
- **Data Ingestion**: Supports multiple data sources for real-time ingestion.
- **Stream Processing**: Implements transformations and analytics on the fly.
- **Scalability**: Designed to handle high-throughput data streams.
- **Extensibility**: Easily customizable for additional use cases.

## Getting Started

### Prerequisites
- Python 3.10.18 or any stable version after that
- Required dependencies listed in `requirements.txt`

### Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/your-repo/ci-truefoundry-endpoints.git
    cd ci-truefoundry-endpoints/realtime_streaming
    ```
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Usage
1. uvicorn src:app --reload


## Testing
Run the test suite to ensure everything is working correctly:
```bash
pytest tests/
```

## Docker Local Testing
### Backend
```bash
docker build -f Dockerfile -t asset_builder .
```

```bash
docker run -p 8501:8501 --env-file .env asset_builder
```

### UI
```bash
docker build -f Dockerfile -t asset_builder-ui .
```

```bash
docker run -p 8501:8501 --env-file .env asset_builder-ui
```

