# Kubernetes deployment

These manifests deploy the API, dashboard and persistent local GGUF worker, with probes, non-root containers, bounded resources, a protected model PVC, autoscaling and ingress restrictions. They require an existing Kubernetes cluster, ingress-nginx, a metrics server for HPA, a DNS name/TLS certificate, external PostgreSQL/Redis/Elasticsearch services and a storage class for the model PVC. No cluster is assumed or modified by the local launcher.

1. Build and push the API and web Dockerfiles to your registry. Replace both image references with your actual image digests.
2. Change the host and TLS secret name in `ingress.yaml` to your configured DNS/TLS resources.
3. Create the namespace first. Supply `darktracex-runtime` from a secret manager, or create it from a private env file using the keys in `runtime.env.example`. Never commit the populated env file. URL-encode special characters in database credentials. Create a separate `darktracex-llm-runtime` secret containing only the same `COPILOT_WORKER_KEY` value; do not pass cloud API keys or database credentials to the model worker.
4. Upload the approved GGUF file to the `darktracex-llm-model` PVC as `/models/selected.gguf` using your cluster's controlled storage workflow. The worker starts `OFFLINE` until the file is present and never downloads a model itself. Replace the local-LLM image reference with a reviewed, signed digest.
5. Apply with `kubectl apply -k infra/k8s`, then wait for the API, web and local-LLM rollouts. Confirm your ingress controller namespace matches the network policy selector.
5. Register the first workspace account through HTTPS; it becomes that tenant's administrator. Create subsequent users from Administration.

The schema bootstrap serializes PostgreSQL table creation with an advisory lock. Back up existing databases before upgrades; this bootstrap creates new tables but is not a general migration engine for arbitrary future column changes. Use a managed database's backups, encryption, failover and retention controls for production. Elasticsearch authentication can be supplied with server-side connection configuration; private network reachability and trusted certificates are required.

Validation on the development machine covers manifest parsing and application builds. Cluster scheduling, TLS, external secrets, HPA and network policy enforcement must be validated on your deployment cluster before production use.
