## Useful commands

### Docker Commands
#### Create Docker image
```bash
sudo docker build -t pipeline-aws-image .
sudo docker build -t pipeline-aws-image . --progress=plain --no-cache
docker stop pipeline-aws-container; docker rm pipeline-aws-container; sudo docker build -t pipeline-aws-image . --progress=plain
```
#### Run Docker Container
```bash
sudo docker run --env-file app/.env \
  -v ~/.aws:/root/.aws \
  -d --name pipeline-aws-container pipeline-aws-image
docker logs pipeline-aws-container
docker exec -it pipeline-aws-container /bin/bash
```

### Kafka and Zookeper Commands
#### Check Zookeper 
```bash
echo ruok | nc localhost 2181
```
#### Kafka Commands
```bash
$KAFKA_HOME/bin/kafka-topics.sh --create --topic create_clients --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
$KAFKA_HOME/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
$KAFKA_HOME/bin/kafka-console-producer.sh --topic create_clients --bootstrap-server localhost:9092
echo "Hello Kafka!" | $KAFKA_HOME/bin/kafka-console-producer.sh --topic test --bootstrap-server localhost:9092 > /dev/null
$KAFKA_HOME/bin/kafka-console-consumer.sh --topic create_clients --from-beginning --bootstrap-server localhost:9092
$KAFKA_HOME/bin/kafka-console-consumer.sh --topic update_clients --from-beginning --bootstrap-server localhost:9092
$KAFKA_HOME/bin/kafka-topics.sh --describe --topic create_clients --bootstrap-server localhost:9092
$KAFKA_HOME/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
$KAFKA_HOME/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group go-consumer-group
```

### Redis Commands
```bash
redis-cli ping
```

### gRPC Commands 
```bash
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext localhost:50051 getitem.GetItemService/GetItem -d '{"id": "example_id"}'
netstat -tuln | grep 50051
```

### Terraform Commands
```bash
terraform init
terraform validate
terraform plan
terraform apply
```

### AWS Setup Commands
#### AWS User Permissions
https://us-east-1.console.aws.amazon.com/iam/home?region=us-east-1#/users/details/Denis?section=permissions
#### Configure AWS
```bash
aws configure
```
#### Check AWS Credentials in Container
```bash
aws sts get-caller-identity
cat ~/.aws/c*
```

### Keep environment variables in the .env file:
```bash
cat ./app/.env 
TF_VAR_kms_key_arn=arn:aws:kms...
```