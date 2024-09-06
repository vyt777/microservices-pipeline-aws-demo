#!/bin/bash

# Create Kafka topic
$KAFKA_HOME/bin/kafka-topics.sh --create --topic create_clients --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 > $KAFKA_HOME/logs/kafka.log 2>&1 &
$KAFKA_HOME/bin/kafka-topics.sh --create --topic update_clients --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 > $KAFKA_HOME/logs/kafka.log 2>&1 &

# Launch Zookeeper
$KAFKA_HOME/bin/zookeeper-server-start.sh $KAFKA_HOME/config/zookeeper.properties > /var/log/zookeeper.log 2>&1 &

# Launch Kafka on the foreground
$KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties > /var/log/kafka.log 2>&1 & 

# Wait for Zookeeper and Kafka to start
sleep 3