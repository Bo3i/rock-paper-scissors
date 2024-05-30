# Rock Paper Scissors Game

This is a multiplayer Rock Paper Scissors game implemented in Python using Pygame for the client-side GUI and RabbitMQ for server-client communication.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.6 or higher
- Pygame
- Pika (RabbitMQ Python client)

You can install the Python dependencies with pip:

```bash
pip install pygame pika
```

### Installing

Clone the repository to your local machine:

```bash
git clone https://github.com/Bo3i/rock-paper-scissors.git
```

Install the RabbitMQ server:

```bash
choco install rabbitmq
```

### Running the game

1. Navigate to the project directory:

```bash
cd rock-paper-scissors
```

2. Run the server:

```bash
python src/server.py
```

3. Run the game client:

```bash
python src/client.py
```

## Game Rules

- Rock beats Scissors
- Scissors beats Paper
- Paper beats Rock

The game is a draw if both players choose the same move

## Build With

- [Pygame](https://www.pygame.org/news) - A set of Python modules designed for writing video games
- [RabbitMQ](https://www.rabbitmq.com/) - An open-source message-broker software that originally implemented the Advanced Message Queuing Protocol
- [Pika](https://pika.readthedocs.io/en/stable/) - A pure-Python implementation of the AMQP 0-9-1 protocol

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details


