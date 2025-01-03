# Simple_CDC

Change Data Capture (CDC) is a process that identifies changes in data in databases. It helps track modifications made to a table in real-time without directly affecting the operational system.

## Problem

We have an application that performs CRUD operations on a table in our database called `holding`. We want to answer business questions like:
- How many times a user changed their stock type or quantity?
- What is the most common stock sold within a specific period?

It is not good practice to run analysis on the operational databases directly, as it may affect the performance of our application. Additionally, OLTP (Online Transaction Processing) databases are not optimized for analysis. Instead, we will move the data to an OLAP (Online Analytical Processing) database that's optimized for analysis.

We will use PostgreSQL as our database and store the output in a simple `.txt` file (`output_data.txt`).

## Setup

### Postgres

When a transaction occurs, the data change is written to a cache and logged in the Write Ahead Log (WAL) in bulk to keep the latency low. Only the logs (not the data) are written to disk. We will use Docker to run a PostgreSQL instance.

1. **Run Docker container**:
    ```bash
    docker run -d --name postgres -p 5432:5432 -e POSTGRES_USER=oamen -e POSTGRES_PASSWORD=oamenn debezium/postgres:12
    ```

2. **Access the container**:
    ```bash
    docker exec -ti postgres /bin/bash
    ```

3. **Interact with PostgreSQL**:
    ```bash
    docker exec -it postgres bash
    psql -U oamen
    create database bank;
    \c bank
    create schema bank_data;
    set search_path to bank_data,public;
    create table bank_data.holding(
        holding_id int, user_id int, holding_stock text, holding_quantity int, datetime_created timestamp, datetime_updated timestamp
    );
    ```

4. **Set replica identity** to return before and after values:
    ```sql
    alter table bank_data.holding replica identity full;
    ```

5. **Insert sample values into the table**:
    ```sql
    insert into bank_data.holding values (101, 1, 'AFM', 10, now(), now());
    ```

### Kafka

Kafka is a distributed message queue system, run by Zookeeper. Here are the components:
- **Broker**: A collection of distributed message queues, responsible for receiving and sending messages.
- **Topic**: A specific queue within the broker. It categorizes messages.
- **Partition**: A way to distribute content across the cluster.
- **Offset**: A pointer that tells you which message you're on in a topic partition.

To set up Kafka:
1. **Start Zookeeper**:
    ```bash
    docker run -d --name zookeeper -p 2181:2181 -p 2888:2888 -p 3888:3888 debezium/zookeeper:1.1
    ```

2. **Start Kafka broker**:
    ```bash
    docker run -d --name kafka -p 9092:9092 --link zookeeper:zookeeper debezium/kafka:1.1
    ```

### Debezium

Debezium reads changes from source systems. We will use Kafka Connect (a Kafka tool) to run Debezium, which provides a framework for connecting input data sources to Kafka and Kafka to output sinks.

To set up Debezium:
1. **Start Kafka Connect**:
    ```bash
    docker run -d --name connect -p 8083:8083 --link kafka:kafka --link postgres:postgres -e BOOTSTRAP_SERVERS=kafka:9092 -e GROUP_ID=sde_group -e CONFIG_STORAGE_TOPIC=sde_storage_topic -e OFFSET_STORAGE_TOPIC=sde_offset_topic debezium/connect:1.1
    ```

2. **Register a connector**:
    ```bash
    curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" \
    localhost:8083/connectors/ \
    -d '{
        "name": "sde_connector",
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": "postgres",
            "database.port": "5432",
            "database.user": "oamen",
            "database.password": "admin",
            "database.dbname": "bank",
            "database.server.name": "bankserver1",
            "table.whitelist": "bank_data.holding"
        }
    }'
    ```

### Consumer

Now that we have our connector pushing messages into the Kafka broker, we can consume the messages with a consumer.

To set up the consumer:
1. **Look at the first message in the Kafka topic**:
    ```bash
    docker run -it --rm --name consumer --link zookeeper:zookeeper --link kafka:kafka debezium/kafka:1.1 watch-topic -a bankserver1.bank_data.holding --max-messages 1 | findstr /R "^{.*$" | jq
    ```

2. **Example Output**:
    ```json
    {
        "schema": { ... },
        "payload": {
            "before": null,
            "after": {
                "holding_id": 1000,
                "user_id": 1,
                "holding_stock": "VFIAX",
                "holding_quantity": 10,
                "datetime_created": 1735898691035077,
                "datetime_updated": 1735898691035077
            },
            "source": { ... },
            "op": "r"
        }
    }
    ```

3. **Create a Python script (`parse.py`)** to parse the payload.
4. **Take the output from the consumer and parse it into a `.txt` file**:
    ```bash
    docker run -it --rm --name consumer5 --link zookeeper:zookeeper --link kafka:kafka debezium/kafka:1.1 watch-topic -a bankserver1.bank_data.holding --max-messages 10 | findstr /R "^{.*$" | python parse.py > output_data.txt
    ```

## Tools Used

- **Python**
- **Docker**

## Resources

1. [Docker Documentation](https://docs.docker.com/)
2. [Install and Use Curl on Windows](https://stackoverflow.com/questions/9507353/how-do-i-install-and-use-curl-on-windows)
3. [Change PostgreSQL User Password](https://stackoverflow.com/questions/12720967/how-can-i-change-a-postgresql-user-password)
4. [List Tables in PostgreSQL](https://www.illacloud.com/blog/list-tables-in-postgresql/#list-tables-in-the-database-using-dt)
5. [PostgreSQL Error - Fatal Role](https://stackoverflow.com/questions/65222869/how-do-i-solve-this-problem-to-use-psql-psql-error-fatal-role-postgres-d)
6. [Connecting to PostgreSQL in Docker](https://stackoverflow.com/questions/37694987/connecting-to-postgresql-in-a-docker-container-from-outside)
7. [YouTube Video on Kafka Setup](https://www.youtube.com/watch?v=qXIAsgldOB8)
