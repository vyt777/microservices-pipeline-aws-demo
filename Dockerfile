# Base Ubuntu image
FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Denver

# Install, update packages and remove cache
RUN apt-get update && apt-get install -y \
    wget \
    netcat \
    net-tools \
    curl \
    unzip \
    python3 \
    python3-pip \
    git \
    vim \
    jq \
    awscli \
    openjdk-11-jre-headless \
    build-essential \
    software-properties-common \
    redis-server \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN curl -LO https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip \
    && unzip terraform_1.5.0_linux_amd64.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform_1.5.0_linux_amd64.zip

# Download and install the latest Go version
RUN wget https://golang.org/dl/go1.21.1.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.21.1.linux-amd64.tar.gz \
    && rm go1.21.1.linux-amd64.tar.gz

# Set Go environment variables
ENV GOPATH=/go
ENV GOROOT=/usr/local/go
ENV GO111MODULE=on
ENV PATH=$PATH:/usr/local/go/bin:$GOPATH/bin:$GOROOT/bin

# Install pip dependencies
RUN pip3 --timeout=100 install boto3 confluent-kafka grpcio grpcio-tools unittest-xml-reporting pytest pytest-asyncio pytest-html

# Install Kafka
ENV KAFKA_VERSION=3.8.0
ENV SCALA_VERSION=2.13
ENV KAFKA_HOME=/opt/kafka

RUN curl -sSLO "https://downloads.apache.org/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz" \
    && tar -xzf kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz -C /opt \
    && mv /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION} /opt/kafka \
    && rm kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz

# Add Kafka and Zookeeper scripts and configs
COPY kafka/ ${KAFKA_HOME}/

# Create working directory
WORKDIR /app

# Copy application files
COPY app/ /app/

# grpc_server module initialization
WORKDIR /app/go/grpc_server

RUN go mod init grpc_server && \
    go get google.golang.org/grpc && \
    go get github.com/aws/aws-sdk-go/aws && \
    go get github.com/aws/aws-sdk-go/aws/session && \
    go get github.com/aws/aws-sdk-go/service/lambda && \
    go get google.golang.org/protobuf && \
    go mod tidy

# Install Go tools
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest \
    && go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Compile the gRPC server
RUN protoc --proto_path=../../proto --go_out=. --go-grpc_out=. ../../proto/get_item.proto
RUN go build -o grpc_server grpc_server.go

# Install grpcurl
RUN curl -L https://github.com/fullstorydev/grpcurl/releases/download/v1.8.5/grpcurl_1.8.5_linux_x86_64.tar.gz | tar -xz \
    && mv grpcurl /usr/local/bin/

# kafka_to_aws_lambda module initialization
WORKDIR /app/go/kafka_to_aws_lamdba

RUN go mod init kafka_to_aws_lamdba && \
    go get github.com/aws/aws-sdk-go/aws && \
    go get github.com/aws/aws-sdk-go/aws/session && \
    go get github.com/aws/aws-sdk-go/service/lambda && \
    go get github.com/confluentinc/confluent-kafka-go/kafka && \
    go mod tidy

# Compile the Kafka to AWS Lambda service
RUN go build -o kafka_to_aws_lambda kafka_to_aws_lamdba.go

# Return to working directory
WORKDIR /app

# Generate Python gRPC client from .proto
RUN python3 -m grpc_tools.protoc -I./proto --python_out=./py --grpc_python_out=./py ./proto/get_item.proto

# Set environment variables
ENV PATH=$PATH:${KAFKA_HOME}/bin
ENV PYTHONUNBUFFERED=1
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_DEFAULT_REGION
ENV AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
    AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
    AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION

# Make scripts executable
RUN chmod +x ${KAFKA_HOME}/kafka-server-start-custom.sh \
    && mkdir -p $KAFKA_HOME/logs

# Expose Redis port for external access
EXPOSE 6379

# Start Kafka, Zookeeper, Redis, gRPC server, and keep the container alive
CMD ["/bin/sh", "-c", "${KAFKA_HOME}/kafka-server-start-custom.sh & \
                      redis-server --logfile /var/log/redis.log --daemonize yes --maxmemory 128mb --maxmemory-policy allkeys-lru && \
                      while ! nc -z localhost 6379; do sleep 1; done && \
                      redis-cli -p 6379 CONFIG SET protected-mode no && \
                      /app/go/grpc_server/grpc_server > /var/log/grpc_server.log 2>&1 & \
                      while ! nc -z localhost 9092; do sleep 1; done && \
                      /app/go/kafka_to_aws_lamdba/kafka_to_aws_lambda > /var/log/kafka_to_aws_lambda.log 2>&1 & \
                      tail -f /dev/null"]
