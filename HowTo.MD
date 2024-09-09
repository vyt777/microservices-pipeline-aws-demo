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
#### Setup EC2
Launch Ubuntu instance https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#Home: with "my-ip" security group rule

Update permissions to your key and ssh-in into the remote AWS Ubuntu instance
```bash
chmod 400 /path/to/your-key.pem
ssh -i /path/to/your-key.pem ubuntu@ec2-54-174-139-195.compute-1.amazonaws.com
```

Update the remote AWS Ubuntu instance security group rules to open 6378 Redis port
https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#SecurityGroup:group-id=sg-05f550060decbf6d0

Install and enable Docker on the remote AWS Ubuntu instance
```bash
sudo apt update
sudo apt install docker.io
sudo systemctl start docker
sudo systemctl enable docker
```

#### Upload Docker image on AWS via Docker Hub
Register yourself on Docker Hub https://hub.docker.com/

Build the image and push to Docker Hub
```bash
docker login
sudo docker build -t pipeline-aws-image . --progress=plain
docker tag pipeline-aws-image denforlight/pipeline-aws-image:latest
docker push denforlight/pipeline-aws-image:latest
```

The image is accessible here now:
https://hub.docker.com/repository/docker/denforlight/pipeline-aws-image/general

SSH-in to the AWS Ubuntu instance, pull the image and run it
```bash
ssh -i /path/to/your-key.pem ubuntu@ec2-54-174-139-195.compute-1.amazonaws.com
sudo usermod -aG docker ubuntu
newgrp docker
docker login
docker stop pipeline-aws-container; docker rm pipeline-aws-container; docker rmi $(docker images -q)
docker images
docker pull denforlight/pipeline-aws-image:latest
docker run -d -p 6379:6379 --name pipeline-aws-container denforlight/pipeline-aws-image:latest
docker exec -it pipeline-aws-container /bin/bash
```

Check open ports in the AWS Ubuntu instance (Redis should listen 6379)
```bash
sudo netstat -tuln
ss -tuln
```

#### Check your external IP
```bash
curl ifconfig.me
```

### Keep environment variables in the .env file:
```bash
cat ./app/.env 
TF_VAR_kms_key_arn=arn:aws:kms...
```

### Check logs
```bash
cat /var/log/zookeeper.log
cat /var/log/kafka.log
cat /var/log/grpc_server.log
cat /var/log/kafka_to_aws_lambda.log
```
