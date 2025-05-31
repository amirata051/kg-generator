# Knowledge Graph Generator

![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Kafka](https://img.shields.io/badge/Kafka-7.5-orange)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 🚀 Project Overview

This project implements a **scalable, containerized Knowledge Graph Generator** that processes PDF documents, extracts semantic information, and constructs an evolving knowledge graph. It leverages:

- **GraphRAG-SDK** for knowledge graph construction,
- **Unstructured-IO** for robust PDF parsing,
- **FalkorDB** as the graph database backend,
- **Kafka** for scalable asynchronous task processing,
- **MinIO** for object storage,
- and exposes a REST API and interactive frontend for uploading PDFs and visualizing the knowledge graph.

All components — backend API, worker, frontend UI, and dependencies — run in isolated Docker containers orchestrated by Docker Compose for ease of deployment and scaling.

---

## 🧠 Technology Stack & Why These?

| Technology           | Purpose                                             | Why Chosen                                                                                          |
|----------------------|-----------------------------------------------------|---------------------------------------------------------------------------------------------------|
| **FastAPI**          | Backend REST API                                   | Ultra-fast async framework, automatic docs, easy to extend                                       |
| **GraphRAG-SDK**     | Knowledge graph creation and management             | Dedicated SDK with advanced graph processing capabilities                                        |
| **Unstructured-IO**  | PDF content extraction                               | High-quality extraction from complex PDFs, supports many layouts                                 |
| **FalkorDB**         | Graph database                                      | Efficient, Redis-protocol-compatible, built for graph workloads                                  |
| **Kafka**            | Distributed messaging queue                          | Reliable, scalable async task orchestration                                                     |
| **MinIO**            | S3-compatible object storage                         | Simple, scalable object storage ideal for PDFs                                                  |
| **Redis**            | State management (deduplication hashes)             | Fast in-memory store for tracking processed files and elements                                  |
| **Streamlit**        | Frontend UI                                         | Rapid, Pythonic frontend to upload files and visualize graphs                                   |
| **Docker & Compose** | Containerization & orchestration                     | Unified environment, easy multi-service management, ensures consistency across machines         |

---

## 📁 Project Structure

```

amirata051-kg-generator/
├── README.md
├── docker-compose.yml       # Orchestrates all containers
├── Dockerfile.api           # Backend container definition
├── Dockerfile.worker        # Kafka worker container definition
├── requirements.txt         # Python dependencies for backend & worker
├── test\_connection.py       # Kafka connectivity test
├── app/                    # Backend app code (FastAPI, services, workers)
│   ├── main.py              # FastAPI app entrypoint
│   ├── config.py            # Environment & service configs
│   ├── api/                 # API routes (upload, graph)
│   ├── services/            # Kafka, MinIO, Redis clients
│   └── workers/             # Kafka consumer logic & incremental KG processing
└── frontend/
├── app\_frontend.py      # Streamlit frontend app
└── Dockerfile.frontend  # Frontend container definition

````

---

## ⚙️ Setup & Run (All-in-One with Docker Compose)

### Prerequisites

- **Docker** (v20+)
- **Docker Compose** (v2+)

### Steps

1. **Clone the repo**

```bash
git clone https://github.com/amirata051/kg-generator.git
cd kg-generator
````

2. **Configure environment variables**

Create a `.env` file in the root directory (same level as docker-compose.yml) with:

```env
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=pdf_tasks

FALKORDB_HOST=falkordb
FALKORDB_PORT=6379
KG_NAME=kg

REDIS_HOST=redis
REDIS_PORT=6380
REDIS_DB=0
```

> **Note:** Use the Docker Compose service names (e.g., `kafka`, `minio`, `falkordb`, `redis`) as hosts for internal container networking.

3. **Start all services**

```bash
docker-compose up -d --build
```

This command builds and starts:

* Zookeeper & Kafka (message queueing)
* MinIO (PDF file storage)
* FalkorDB (graph database)
* Redis (state & deduplication store)
* Backend API service (`kg-api`)
* Kafka Worker service (`kg-worker`) that processes PDFs and updates KG incrementally
* Streamlit Frontend UI (`kg-frontend`) for file upload and graph visualization

4. **Access services**

* API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
* Frontend UI: [http://localhost:8501](http://localhost:8501)

5. **Upload PDFs via UI or API** and watch the system process them asynchronously, updating the knowledge graph stored in FalkorDB.

6. **View logs (optional)**

```bash
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f frontend
```

7. **Stop all services**

```bash
docker-compose down
```

---

## 🧩 How It Works (Data Flow)

1. User uploads PDFs (via frontend or direct API call).
2. PDF files are saved to MinIO (object storage).
3. A Kafka message with file metadata is produced.
4. The Kafka consumer worker downloads the PDF, extracts content with Unstructured-IO, and deduplicates new textual elements using Redis.
5. New content is converted into an ontology using GraphRAG-SDK with a Lite LLM model.
6. The knowledge graph is incrementally updated and saved into FalkorDB.
7. The frontend fetches and visualizes the current knowledge graph via API calls.

---

## ⚡ Scaling Workers for High Throughput

To turbocharge your Knowledge Graph processing pipeline, you can effortlessly spin up multiple worker instances that consume Kafka tasks in parallel — maximizing throughput and minimizing latency.

### How to launch 5 worker instances concurrently?

With Docker Compose’s powerful scaling capability, simply run:

```bash
docker-compose up --scale worker=5 -d
```

This command will:

* **Spawn 5 independent worker containers**
* Automatically **balance Kafka message consumption** across these workers using the shared consumer group (`pdf_worker_group`)
* Enable efficient **parallel PDF processing** and incremental Knowledge Graph updates

### Pro Tip:

If you’re running in a **Docker Swarm or Kubernetes environment**, leverage native orchestration by adding a `deploy` section with replicas to your `docker-compose.yml`:

```yaml
worker:
  build:
    context: .
    dockerfile: Dockerfile.worker
  deploy:
    replicas: 5
  command: ["python", "-m", "app.workers.worker"]
  depends_on:
    - kafka
    - minio
    - falkordb
    - redis
```

Then deploy with:

```bash
docker swarm init  # if not already initialized
docker stack deploy -c docker-compose.yml kg_stack
```

---

Scaling is seamless and gives you the flexibility to handle heavier workloads without any code changes — just spin up more workers and watch the pipeline roar!

---

## 🛠️ Engineering Highlights

* **Incremental Updates:** Deduplication via Redis ensures efficient graph updates only on new content.
* **Asynchronous, Scalable Architecture:** Kafka decouples upload and processing.
* **Containerized for Production:** Docker Compose handles deployment with clear service isolation.
* **Robust Error Handling & Logging:** Across upload, processing, and messaging.
* **Clean API Design:** RESTful endpoints with FastAPI, including OpenAPI docs.
* **Interactive Frontend:** Streamlit for rapid user interaction without heavy frontend frameworks.

---

## 📞 Contact & Support

Feel free to open issues or contact the maintainer for questions or feature requests.

---

