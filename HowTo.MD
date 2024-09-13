## Useful commands

### Docker Commands
#### Create Docker image
```bash
docker build -t pipeline-aws-image .
docker build -t pipeline-aws-image . --progress=plain --no-cache
docker stop pipeline-aws-container; docker rm pipeline-aws-container; sudo docker build -t pipeline-aws-image . --progress=plain
```

#### Run Docker Container
```bash
docker run --env-file app/.env \
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
redis-cli -p 6379 INFO memory
```

### gRPC Commands 
```bash
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext localhost:50051 getitem.GetItemService/GetItem -d '{"id": "example_id"}'
netstat -tuln | grep 50051
```

### Add AWS User EC2, IAM, DynamoDB rights
https://us-east-1.console.aws.amazon.com/iam/home?region=us-east-1#/users/details/Denis?section=permissions
Add Permissions => Attach existing policies directly:
- IAMFullAccess
- AmazonEC2FullAccess
- AmazonDynamoDBFullAccess 
- AWSLambda_FullAccess
- AWSLambdaExecute
- AWSLambdaInvocation-DynamoDB
- AWSLambdaRole
- CloudWatchLogsFullAccess

### AWS Setup Commands
#### AWS User Permissions
https://us-east-1.console.aws.amazon.com/iam/home?region=us-east-1#/users/details/Denis?section=permissions

#### Configure AWS
```bash
aws configure
```

#### Check AWS Credentials in Docker container
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

Turn off auto-updates
```bash
sudo vim /etc/apt/apt.conf.d/20auto-upgrades
```

Make sure both settings set to 0:
```text
APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Unattended-Upgrade "0";
```

Update the remote AWS Ubuntu instance security group rules to open 6379 Redis port
Update the remote AWS Ubuntu instance security group rules to open allow incoming requests to 6379 Redis port from Source of your VPC (IPv4 CIDR): 172.31.0.0/16
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
docker build --build-arg AWS_ACCESS_KEY_ID=$(grep 'aws_access_key_id' ~/.aws/credentials | awk '{print $3}') \
             --build-arg AWS_SECRET_ACCESS_KEY=$(grep 'aws_secret_access_key' ~/.aws/credentials | awk '{print $3}') \
             --build-arg AWS_DEFAULT_REGION=$(grep 'region' ~/.aws/config | awk '{print $3}') \
             -t pipeline-aws-image . --progress=plain
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
docker info
docker image prune -f
docker system prune -f
docker pull denforlight/pipeline-aws-image:latest
docker run -d -p 6379:6379 --name pipeline-aws-container denforlight/pipeline-aws-image:latest
docker exec -it pipeline-aws-container /bin/bash
env | grep AWS
```

Check open ports in the AWS Ubuntu instance (Redis should listen 6379)
```bash
sudo netstat -tuln
ss -tuln
```

Check access to Redis port from local PC and ping it
```bash
nc -zv ec2-54-174-139-195.compute-1.amazonaws.com 6379
redis-cli -h ec2-54-174-139-195.compute-1.amazonaws.com -p 6379 ping
```

### Terraform Commands
```bash
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common curl
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform
cd microservices-pipeline-aws-demo/app/py
mkdir lambda_temp
cd lambda_temp
cp ../lambda_kafka_to_dynamodb.py ./
pip install redis -t ./
rm -rf *dist-info
zip -r ../lambda_kafka_to_dynamodb.zip .
cd ../..
terraform state rm aws_instance.redis_instance
terraform import aws_instance.redis_instance i-03e43a709b7bdca03
terraform import aws_vpc_endpoint.dynamodb_gateway vpce-0821588255b515ba1
terraform init
terraform validate
terraform plan
terraform apply -auto-approve
```

### Check AWS services after applying Terraform
Check Dynamodb tables from local PC
```bash
aws dynamodb list-tables
aws dynamodb describe-table --table-name Clients
aws dynamodb scan --table-name Clients
aws dynamodb put-item \
    --table-name Clients \
    --item '{
        "id": {"S": "test"},
        "first_name": {"S": "John"},
        "second_name": {"S": "Doe"},
        "phone": {"S": "555-1234"}
    }'
aws dynamodb get-item     --table-name Clients     --key '{"id": {"S": "1"}}'
```
Check Lambda from local PC
```bash
aws lambda list-functions
aws lambda invoke --function-name ClientManagementFunction --cli-binary-format raw-in-base64-out --payload '{"action": "get_client", "id": "1"}' /dev/stdout
aws lambda invoke --function-name ClientManagementFunction --cli-binary-format raw-in-base64-out --payload '{"action": "create_client", "id": "test2", "client_data": {"first_name": "John", "second_name": "Doe", "phone": "555-1234"}}' /dev/stdout
aws lambda invoke --function-name ClientManagementFunction --cli-binary-format raw-in-base64-out --payload '{"action": "update_client", "id": "test2", "client_data": {"first_name": "Terry", "second_name": "Doe", "phone": "555-3456"}}' /dev/stdout
aws logs tail /aws/lambda/ClientManagementFunction --follow
```
Check EC2 instances from local PC
```bash
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"
```

#### Watch logs, traffic, cost 
Create VPC logs flow
https://us-east-1.console.aws.amazon.com/vpcconsole/home?region=us-east-1#vpcs:
Actions => Create Flow Log

Watch traffic volume via CloudWatch
https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#metricsV2?graph=~(metrics~(~(~'AWS*2fEC2~'NetworkPacketsOut~'InstanceId~'i-03e43a709b7bdca03)~(~'.~'NetworkPacketsIn~'.~'.))~view~'timeSeries~stacked~false~region~'us-east-1~stat~'Average~period~60~start~'-PT1H~end~'P0D)&query=~'*7bAWS*2fEC2*2cInstanceId*7d

Watch billing and cost 
https://us-east-1.console.aws.amazon.com/costmanagement/home#/home
https://us-east-1.console.aws.amazon.com/billing/home#/freetier

See EC2 instances in all regions
https://us-east-1.console.aws.amazon.com/ec2globalview/home?region=us-east-1#

#### Check your external IP
```bash
curl ifconfig.me
```

### Keep environment variables in the .env file:
```bash
cat ./app/.env 
TF_VAR_kms_key_arn=arn:aws:kms...
```

### Check logs in Docker container
```bash
cat /var/log/zookeeper.log
cat /var/log/kafka.log
cat /var/log/grpc_server.log
cat /var/log/kafka_to_aws_lambda.log
cat /var/log/redis.log
```
