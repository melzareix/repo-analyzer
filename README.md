# Turing Data Engineering Challenge

## Table Of Contents
- [Turing Data Engineering Challenge](#turing-data-engineering-challenge)
    + [1. Introduction](#1-introduction)
    + [2. Architecture](#2-architecture)
    + [3. Installation](#3-installation)
      - [3.1 Dependencies](#31-dependencies)
      - [3.2 Steps](#32-steps)
    + [4. Usage](#4-usage)
      - [1. Non-Docker](#1-non-docker)
      - [2. Docker](#2-docker)

### 1. Introduction
In this challenge, We download 100,000 public Github repositories and perform processing on the downloaded code.
For each repository, our goal is to compute the following statistics for the Python code present.

1. Number of lines of code **[this excludes comments, whitespaces, blank lines]**.
2. List of external libraries/packages used.
3. The Nesting factor for the repository: the Nesting factor is the average depth of a nested for loop throughout the code.
4. Code duplication: What percentage of the code is duplicated per file. If the same 4 consecutive lines of code (disregarding blank lines, comments, etc. other non code items) appear in multiple places in a file, all the occurrences except the first occurence are considered to be duplicates.
5. Average number of parameters per function definition in the repository.
6. Average Number of variables defined per line of code in the repository.

### 2. Architecture
1. To calculate the code statistics python's `ast` module is used to generate an `Abstract Syntax Tree`, which is then visited to calculate 5 statistics. To calculate the code duplicate we use python dict `hashmap` implementation to compare every 4 lines of code in the repo.

2. To perform the processing we use `Kubernetes`, `Docker` and `RabbitMQ`. We have the `producer` add a message to queue for every repo that needs processing, then using kubernetes we run several `workers` [5-10] to take messages from the queue, clone the repo, calculate the statistics then add the calculated result to another results queue in rabbitmq.

3. The `results_parser` is responsible for consuming messages from the results queue and append it to the json file.

4. The final results are found in `results/results.json`.

### 3. Installation
#### 3.1 Dependencies
- RabbitMQ
- Python 3
- Docker [recommended]

#### 3.2 Steps

1. Clone this repository
```
git clone https://github.com/melzareix/turing-data-challenge.git
cd turing-data-challenge
```

2. Create `.env` file with the following variables (you can also add these variables via docker)
```
RABBIT_USERNAME=user
RABBIT_PASSWORD=user
RABBIT_HOST=127.0.0.1
RABBIT_PORT=5672
QUEUE_NAME=URLS_QUEUE_NAME
RESULTS_QUEUE=RESULTS_QUEUE_NAME
```

3. If you use don't use docker, use pip to install dependencies
```
pip3 install -r requirements.txt
```

4. If you are using docker then build the container
```
docker build -t data-challenge .
```

### 4. Usage
#### 1. Non-Docker
  1. Run producer to add urls to queue.
  ```
  python3 src/producer.py
  ```
  
  2. Run worker to process urls.
  ```
  python3 src/worker.py
  ```
  
  3. After the worker finishes, run results parser to parse results.
  ```
  python3 src/results_parser.py
  ```
 #### 2. Docker
   1. Run producer to add urls to queue.
  ```
  docker run -it --rm data-challenge /bin/sh -c "python3 src/producer.py"
  ```
  
  2. Run worker to process urls.
  ```
  docker run -it --rm data-challenge
  ```
  
  3. After the worker finishes, run results parser to parse results.
  ```
  docker run -it --rm --name data-container data-challenge /bin/sh -c "python3 src/results_parser.py"
  ```
  4. Copy results file from container to your machine.
  ```
  docker cp data-container:/results/results_100000.json results.json
  ```
