#!/bin/bash
# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
cub kafka-ready -b kafka:29092 1 60

echo "Creating NEXUS Kafka topics..."

kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists \
  --topic nexus.collection.raw \
  --partitions 4 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists \
  --topic nexus.entities.extracted \
  --partitions 4 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists \
  --topic nexus.events \
  --partitions 2 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists \
  --topic nexus.alerts \
  --partitions 2 \
  --replication-factor 1 \
  --config retention.ms=2592000000

echo "Topics created:"
kafka-topics --bootstrap-server kafka:29092 --list

echo "Kafka topic initialization complete."
