# AgentSched

AgentSched is a high-performance scheduler designed for LLM-based agents, optimizing message routing through load balancing, connection pooling, and dynamic scaling to improve concurrent processing and efficient communication with Large Language Models (LLMs).

## Features

- **Intelligent Load Balancing**: Efficiently distribute workload across multiple agents and LLMs.
- **Optimized Connection Pooling**: Manage and reuse connections to maximize resource utilization.
- **Dynamic Scaling**: Automatically adjust resources based on demand.
- **High Concurrency Support**: Handle multiple agent requests simultaneously.
- **Efficient Message Routing**: Ensure messages are delivered to the appropriate LLM quickly and reliably.
- **LLM Integration Optimization**: Streamline the process of communicating with various LLM providers.

## Architecture

Our system architecture leverages Kafka for robust message handling and Kubernetes for scalable deployments:

``` mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#ffffff', 'primaryColor': '#f0f0f0', 'primaryTextColor': '#000000' }}}%%

graph TD
    classDef default fill:#f0f0f0,stroke:#333,stroke-width:1px,color:#000000;
    classDef kafka fill:#e6f3e6,stroke:#4caf50,stroke-width:2px,color:#000000;
    classDef component fill:#e6f2ff,stroke:#2196f3,stroke-width:2px,color:#000000;
    classDef agent fill:#fff0e6,stroke:#ff9800,stroke-width:2px,color:#000000;
    classDef groupbox fill:none,stroke:#999,stroke-width:2px,stroke-dasharray: 5 5;

    subgraph ExternalSystems [External Systems]
        ExtUsers[External Users]
        LoadBal[Load Balancer]
    end

    subgraph AgentLayer [Agent Layer]
        AgentDist{Agent Distributor}
        PrimaryAgent[Primary Agent]
        ClonedAgents[Cloned Agents]
    end

    subgraph KafkaInfra [Kafka Infrastructure]
        MsgBroker{Message Broker}
        Queue1[Queue 1]
        Queue2[Queue 2]
        Queue3[Queue 3]
        ReplyQueue[Reply Queue]
    end

    subgraph ResourceMgmt [Resource Management]
        Scheduler[Scheduler]
        ConnPool[Connection Pool]
    end

    subgraph LLMLayer [LLM Model Layer]
        ModelDist{Model Distributor}
        VLLM1[vllm Instance 1]
        GPT4T[GPT-4 Turbo]
        VLLM2[vllm Instance 2]
    end

    subgraph ResultHandling [Result Handling]
        ResultProc[Result Processor]
        ResultsQueue[Results Queue]
        OutputHandler[Output Handler]
    end

    %% Main flow
    ExtUsers -->|Requests| LoadBal
    LoadBal -->|Distribute| AgentDist
    AgentDist --> PrimaryAgent & ClonedAgents
    PrimaryAgent & ClonedAgents -->|Produce| MsgBroker
    MsgBroker --> Queue1 & Queue2 & Queue3
    Queue1 & Queue2 & Queue3 -->|Consume| Scheduler
    Scheduler <--> ConnPool
    ConnPool -->|Assign| ModelDist
    ModelDist --> VLLM1 & GPT4T & VLLM2
    VLLM1 & GPT4T & VLLM2 -->|Results| ResultProc
    ResultProc --> ResultsQueue
    ResultsQueue --> OutputHandler
    OutputHandler -->|Return| ExtUsers

    %% Kafka Request-Reply
    PrimaryAgent & ClonedAgents -.->|Request| MsgBroker
    MsgBroker -.->|Reply| ReplyQueue
    ReplyQueue -.->|Consume| PrimaryAgent & ClonedAgents

    %% Admin and Monitoring
    AdminClient[Admin Client] -.->|Manage| MsgBroker

    subgraph Monitoring [Monitoring & Logging]
        MonitorSys[Monitoring System]
    end

    MonitorSys -.->|Monitor| ExternalSystems & AgentLayer & KafkaInfra & ResourceMgmt & LLMLayer & ResultHandling

    %% Styling
    class MsgBroker kafka;
    class LoadBal,Scheduler,ConnPool,ResultProc,OutputHandler component;
    class AgentDist,PrimaryAgent,ClonedAgents agent;
    class ExternalSystems,AgentLayer,KafkaInfra,ResourceMgmt,LLMLayer,ResultHandling,Monitoring groupbox;
```

``` mermaid
graph TB
    subgraph Scheduler[Scheduler]
        direction TB
        C[Consumer]
        LB[Load Balancer]
        P[Producer]
        direction LR
        C --> LB
        LB --> P
    end

    subgraph KafkaCluster[Kafka Cluster]
        RT[Request Topics]
        RST[Response Topic]
    end

    subgraph LLMPool[LLM Pool]
        LLM1[LLM Model 1]
        LLM2[LLM Model 2]
        LLM3[LLM Model 3]
    end

    Agent1[Agent 1] -->|1-Send Request| RT
    Agent2[Agent 2] -->|1-Send Request| RT
    RT -->|2-Consume| C
    LB -->|3-Assign Task| LLMPool
    LLMPool -->|4-Return Result| LB
    P -->|5-Produce Response| RST
    RST -->|6-Consume| Agent1
    RST -->|6-Consume| Agent2

    Scheduler -.->|Manage| KafkaCluster
    Scheduler -.->|Manage| LLMPool

    style Scheduler fill:#f9f,stroke:#333,stroke-width:4px
    style KafkaCluster fill:#bfe,stroke:#333,stroke-width:2px
    style LLMPool fill:#ffe,stroke:#333,stroke-width:2px
```

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/readme/main_architecture.png">
    <img alt="AgentSched" src="docs/assets/readme/main_architecture.png" width=55%>
  </picture>
</p>

## Installation

```bash
pip install agentsched
```

## Quick Start

```python
from agentsched import AgentScheduler

# Initialize the scheduler
scheduler = AgentScheduler(config_path='config.yaml')

# Start the scheduler
scheduler.start()

# Send a message to an LLM agent
response = scheduler.send_message(agent_id='agent1', message='Hello, world!')

# Stop the scheduler
scheduler.stop()
```

## Configuration

AgentSched uses a YAML configuration file. Here's a sample configuration:

```yaml
kafka:
  bootstrap_servers:
    - "localhost:9092"
  topics:
    - "agent_messages"

agents:
  - id: "agent1"
    model: "gpt-3.5-turbo"
  - id: "agent2"
    model: "gpt-4"

scaling:
  min_agents: 2
  max_agents: 10
  scaling_factor: 1.5

load_balancing:
  strategy: "round_robin"

connection_pool:
  max_connections: 100
  timeout: 30
```

For more detailed usage instructions, please refer to our [documentation](link-to-docs).

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for more details.

## License

AgentSched is released under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Contact

If you have any questions or feedback, please open an issue on this GitHub repository.

