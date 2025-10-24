# BGE Reranker v2-m3 ModelCar Container

This directory contains files to build a ModelCar container for the BGE Reranker v2-m3 model.

## Model Information

- **Model**: BAAI/bge-reranker-v2-m3
- **Type**: Cross-encoder reranker
- **Size**: ~568M parameters
- **Languages**: 100+ languages
- **License**: MIT
- **Use Case**: Improving retrieval accuracy for log analysis

## Build Instructions

### Prerequisites
- Podman or Docker installed
- Access to quay.io or container registry

### Build the Container

```bash
cd modelcar-build
podman build -t bge-reranker-modelcar:latest --platform linux/amd64 -f Containerfile .
```

### Push to Registry

```bash
# Tag for your registry
podman tag bge-reranker-modelcar:latest quay.io/<your-org>/bge-reranker-modelcar:latest

# Push
podman push quay.io/<your-org>/bge-reranker-modelcar:latest
```

## Deploy to OpenShift AI

Use the InferenceService YAML with:
```yaml
storageUri: oci://quay.io/<your-org>/bge-reranker-modelcar:latest
```

## Model Details

The BGE (BAAI General Embedding) reranker is a state-of-the-art cross-encoder model that:
- Takes query-document pairs and scores their relevance
- Works with vLLM's `task="score"` parameter
- Provides superior accuracy compared to simple similarity scoring
- Requires minimal resources (568M params)

## Integration with AI Troubleshooter v8

This reranker will be used in the multi-agent workflow to:
1. Receive top-N log snippets from hybrid retrieval (BM25 + Vector)
2. Rerank them based on true relevance to the troubleshooting query
3. Pass top-K most relevant snippets to the LLM for analysis

Expected accuracy improvement: 10-15% over baseline retrieval.

