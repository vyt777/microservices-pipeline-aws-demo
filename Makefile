# Variables
DOCKER_HUB_USER=denforlight
DOCKER_IMAGE=pipeline-aws-image
DOCKER_CONTAINER=pipeline-aws-container
EC2_USER=ubuntu

# Terraform Init and Apply
terraform-apply:
	set -e
	cd app/py/ && \
	current_hash=$$(shasum -a 256 lambda_kafka_to_dynamodb.py | awk '{print $$1}') && \
	saved_hash=$$(cat lambda_kafka_to_dynamodb_hash.txt || echo "") && \
	if [ "$$current_hash" != "$$saved_hash" ]; then \
		mkdir -p lambda_temp && \
		cp lambda_kafka_to_dynamodb.py lambda_temp/ && \
		cd lambda_temp && \
		zip -r ../lambda_kafka_to_dynamodb.zip ./lambda_kafka_to_dynamodb.py && \
		echo "$$current_hash" > ../lambda_kafka_to_dynamodb_hash.txt; \
    	cd ../../ && \
		echo "Lambda ZIP updated."; \
	else \
    	cd ../ && \
		echo "No changes in Lambda source code. ZIP not updated."; \
	fi && \
    terraform init && \
    terraform plan && \
    terraform apply -auto-approve

# Docker login
docker-login:
	set -e
	@echo "${DOCKER_HUB_ACCESS_TOKEN}" | docker login -u "${DOCKER_HUB_USER}" --password-stdin

# Build Docker image with AWS credentials
docker-build:
	set -e
	@docker build --build-arg AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY_ID) \
               --build-arg AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY) \
               --build-arg AWS_DEFAULT_REGION=$(AWS_DEFAULT_REGION) \
               -t $(DOCKER_HUB_USER)/$(DOCKER_IMAGE):latest . --progress=plain

# Push Docker image to Docker Hub
docker-push:
	set -e
	@docker push $(DOCKER_HUB_USER)/$(DOCKER_IMAGE):latest

# SSH into EC2 and pull Docker image
deploy-docker-ec2:
	set -e
	ssh -o StrictHostKeyChecking=no $(EC2_USER)@$(EC2_IP) \
		"docker pull $(DOCKER_HUB_USER)/$(DOCKER_IMAGE):latest && \
		docker stop $(DOCKER_CONTAINER) || true && \
		docker rm $(DOCKER_CONTAINER) || true && \
		docker run -d -p 6379:6379 --name $(DOCKER_CONTAINER) $(DOCKER_HUB_USER)/$(DOCKER_IMAGE):latest &&\
		sleep 30"

# Run tests in Docker container on EC2
run-tests-ec2:
	set -e
	ssh -o StrictHostKeyChecking=no $(EC2_USER)@$(EC2_IP) \
		"docker exec $(DOCKER_CONTAINER) bash -c 'python3 /app/py/clear_dynamodb.py && python3 /app/py/test.py'"
		  
# Clean up Docker containers on EC2
docker-clean-ec2:
	set -e
	echo "$$EC2_SSH_KEY" > /tmp/ssh_key.pem && \
	chmod 600 /tmp/ssh_key.pem && \
	ssh -i /tmp/ssh_key.pem -o StrictHostKeyChecking=no $(EC2_USER)@$(EC2_IP) \
		"docker stop $(DOCKER_CONTAINER) && \
		docker rm $(DOCKER_CONTAINER) && \
		docker rmi $(docker images -q) || true" && \
	rm -f /tmp/ssh_key.pem

# Full build, deploy and test process
all: terraform-apply docker-build docker-push deploy-docker-ec2 run-tests-ec2 docker-clean-ec2
