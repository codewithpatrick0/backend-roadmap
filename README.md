# Backend Roadmap — learning in public

My path through the [roadmap.sh/backend](https://roadmap.sh/backend) topics, with a focus on
**understanding the concepts well enough to review and direct AI-generated code**.

## How I work

For every topic:

1. **Study** the concept → `notes.md` (in my own words).
2. **Delegate** a small lab to AI → `lab/` (50–150 lines that show the concept).
3. **Review** the lab line by line and write down what AI tends to get wrong → `ai-review.md`.
4. Close the topic's **issue** with a **pull request** (one branch per topic).

Progress is tracked here and in the [issues](https://github.com/codewithpatrick0/backend-roadmap/issues) / project board.
Starting a new topic? Copy [`_template/`](_template/).

## Progress

**Done 3 / 29 · In progress 2**

Priority: ★★★ used daily, asked in junior interviews · ★★ understand it well · ★ know what it is
and what problem it solves.
Status: ✅ done · 🟡 in progress · ⬜ pending

### 01 · Fundamentals

| # | Topic | Priority | Status |
|---|---|:-:|:-:|
| 01 | Internet: HTTP, DNS, domains, hosting, browsers | ★★★ | ✅ |
| 02 | Frontend basics: HTML, CSS, JS | ★ | ✅ |
| 03 | Backend language (Python) | ★★★ | ✅ |
| 04 | Git and GitHub | ★★★ | 🟡 |
| 05 | [Relational databases, migrations and the N+1 problem](01-fundamentals/05-relational-databases/) | ★★★ | 🟡 |
| 06 | APIs: REST, JSON, OpenAPI | ★★★ | ⬜ |
| 07 | APIs: GraphQL, gRPC, SOAP | ★ | ⬜ |
| 08 | Authentication: JWT, cookies/sessions, OAuth | ★★★ | ⬜ |
| 09 | Authentication: Basic, Token, OpenID, SAML | ★ | ⬜ |
| 10 | Caching: Redis, CDN, client cache | ★★ | ⬜ |
| 11 | Web servers: Nginx, Apache, Caddy | ★★ | ⬜ |
| 12 | Web security: hashing, HTTPS/TLS, CORS, CSP, OWASP | ★★★ | ⬜ |

### 02 · AI in Development

| # | Topic | Priority | Status |
|---|---|:-:|:-:|
| 01 | Basics: how an LLM works, embeddings, vectors, RAG | ★★ | ⬜ |
| 02 | Coding with AI: prompting, agents, MCP, skills | ★★★ | ⬜ |
| 03 | Applications: code review, refactoring, documentation | ★★★ | ⬜ |
| 04 | AI features: streaming, structured outputs, function calling | ★★ | ⬜ |

### 03 · Advanced Backend

| # | Topic | Priority | Status |
|---|---|:-:|:-:|
| 01 | Testing: unit, integration, functional | ★★★ | ⬜ |
| 02 | CI/CD | ★★ | ⬜ |
| 03 | More databases: transactions, ACID, ORMs, normalization, profiling | ★★★ | ⬜ |
| 04 | Docker | ★★★ | ⬜ |
| 05 | LXC, Kubernetes | ★ | ⬜ |
| 06 | Message brokers: Kafka, RabbitMQ | ★ | ⬜ |
| 07 | Architecture: monolith, microservices, serverless, twelve-factor | ★★ | ⬜ |
| 08 | System design | ★★ | ⬜ |
| 09 | Search engines: Elasticsearch, Solr | ★ | ⬜ |
| 10 | Real time: WebSockets, SSE, polling | ★★ | ⬜ |
| 11 | Scaling databases: indexes, replication, sharding, CAP | ★★ | ⬜ |
| 12 | NoSQL: document, key-value, columnar, graph, time series | ★★ | ⬜ |
| 13 | Scaling the system: observability and mitigation strategies | ★★ | ⬜ |

## Labs

Shared environments used by several topics:

| Lab | What it is | Topics |
|---|---|---|
| [`labs/sql-lab`](labs/sql-lab/) | Kestrel Market: fictional retail DB on PostgreSQL 17 (~256k rows) + SQLAlchemy 2.0 | 01·05, 03·03, 03·11 |

## Source

Original topic list with priorities: [`docs/roadmap-backend.pdf`](docs/roadmap-backend.pdf).
