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

![alt text](image.png)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Appointat/AgentSched/main/docs\assets\readme\main_architecture.png">
    <img alt="AgentSched" src="https://raw.githubusercontent.com/Appointat/AgentSched/main/docs\assets\readme\main_architecture.png" width=55%>
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

