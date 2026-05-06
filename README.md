# AI Builder EvalFramework

This folder contains the implementation and resources for Evaluating content genreation via Miki endpoint via `ci-truefoundry-endpoints`.


## Overview

Miki + Mannual evalution needed

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
docker build -t ai-builder-evaluator . 
```

```bash
docker run -p 8501:8501 --env-file .env asset_builder
```

```bash
docker run -it ai-builder-evaluator /bin/bash
```

