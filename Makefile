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
    terraform refresh && \
    if ! terraform state show aws_iam_role.lambda_exec > /dev/null 2>&1; then \
      terraform import aws_iam_role.lambda_exec lambda_exec_role; \
    fi && \
    if ! terraform state show aws_dynamodb_table.clients > /dev/null 2>&1; then \
      terraform import aws_dynamodb_table.clients Clients; \
    fi && \
    if ! terraform state show aws_vpc_endpoint.dynamodb_gateway > /dev/null 2>&1; then \
      terraform import aws_vpc_endpoint.dynamodb_gateway vpce-0821588255b515ba1; \
    fi && \
    if ! terraform state show aws_iam_role_policy.lambda_vpc_access_policy > /dev/null 2>&1; then \
      terraform import aws_iam_role_policy.lambda_vpc_access_policy lambda_exec_role:lambda_vpc_access_policy; \
    fi && \
    if ! terraform state show aws_iam_role_policy_attachment.lambda_dynamodb_access > /dev/null 2>&1; then \
      terraform import aws_iam_role_policy_attachment.lambda_dynamodb_access lambda_exec_role/arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess; \
    fi && \
    if ! terraform state show aws_iam_role_policy_attachment.lambda_policy_attachment > /dev/null 2>&1; then \
      terraform import aws_iam_role_policy_attachment.lambda_policy_attachment lambda_exec_role/arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole; \
    fi && \
    if ! terraform state show aws_instance.redis_instance > /dev/null 2>&1; then \
      terraform import aws_instance.redis_instance i-03e43a709b7bdca03; \
    fi && \
    if ! terraform state show aws_lambda_function.client_lambda > /dev/null 2>&1; then \
      terraform state rm aws_lambda_function.client_lambda || true && \
      terraform import aws_lambda_function.client_lambda ClientManagementFunction || echo "Lambda function does not exist in the cloud. Skipping import."; \
    fi && \
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
		docker run -d -p 6379:6379 --name $(DOCKER_CONTAINER) $(DOCKER_HUB_USER)/$(DOCKER_IMAGE):latest && \
		sleep 30"

# Run tests in Docker container on EC2 and save Pytest report
run-tests-ec2:
	set -e
    # Run tests inside the container with debugging output, generate HTML report, and continue even if tests fail
	ssh -o StrictHostKeyChecking=no $(EC2_USER)@$(EC2_IP) \
		"docker exec -t $(DOCKER_CONTAINER) bash -c 'set +e; \
		pytest -s --capture=tee-sys --asyncio-mode=auto \
		--html=/app/py/test-reports/report.html --self-contained-html /app/py/tests.py; set -e'"
	# Copy the HTML report back from the Docker container to the local machine
	ssh -o StrictHostKeyChecking=no $(EC2_USER)@$(EC2_IP) \
		"docker cp $(DOCKER_CONTAINER):/app/py/test-reports/report.html /home/$(EC2_USER)/report.html"
	# Ensure the local directory for reports exists
	mkdir -p ./test-reports
	# Copy the report from the EC2 instance to the local machine (Github Actions Instance)
	scp $(EC2_USER)@$(EC2_IP):/home/$(EC2_USER)/report.html ./test-reports/report.html || true


# Clean up Docker containers on EC2 (save the AWS computing power)
docker-clean-ec2:
	set -e
	echo "$$EC2_SSH_KEY" > /tmp/ssh_key.pem && \
	chmod 600 /tmp/ssh_key.pem && \
	ssh -i /tmp/ssh_key.pem -o StrictHostKeyChecking=no $(EC2_USER)@$(EC2_IP) \
		"docker stop $(DOCKER_CONTAINER) || true && \
		docker rm $(DOCKER_CONTAINER) || true && \
		docker rmi \$$(docker images -q) || true" ; \
	rm -f /tmp/ssh_key.pem

# Full build, deploy and test process
all: terraform-apply docker-build docker-push deploy-docker-ec2 run-tests-ec2 docker-clean-ec2
