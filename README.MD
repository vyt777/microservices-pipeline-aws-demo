# Microservices Pipeline AWS Demo

![Test Status](https://github.com/vyt777/microservices-pipeline-aws-demo/actions/workflows/ci-cd.yml/badge.svg)

[Test Report](https://vyt777.github.io/microservices-pipeline-aws-demo/report.html)

## Project Overview
This project demonstrates a microservices architecture pipeline for managing client data using technologies like Python, Go, Kafka, gRPC, AWS Lambda, Redis, PostgreSQL, and DynamoDB. The core functionality involves handling and storing client information in AWS DynamoDB and PostgreSQL, leveraging a variety of modern tools with Terraform for AWS EC2 deployment (t2.micro). CI/CD is managed through GitHub Actions.

**Note:** The project is designed to operate within the limits of AWS FreeTier, ensuring no usage of paid services during testing and deployment.

## Purpose
This demo project intentionally showcases a complex architecture to serve as a **framework** or an **example** for building scalable, high-load, and maintainable microservices applications. While a simple client data storage task (used in this project) could be done with a single Python service and a local DynamoDB/PostgreSQL setup, this project illustrates how microservices interact with distributed components, offering a reusable skeleton for more advanced features such as authentication, analytics, and additional services.

## Project Architecture
### Get Requests:
```mermaid
graph TD;
  subgraph Docker container in EC2 instance
    A[Python Test Script]
    B[gRPC Go Service]
    D[Redis Cache]
  end
  subgraph AWS cloud services
    C[AWS Lambda]
    E[DynamoDB]
  end
    A -- **1** Get Client Data --> B
    B -- **2** Get Client Action --> C
    C -- **3** Check If Client Data Exists --> D
    D -- **4 Cache Hit,** Return Client Data --> C
    C -- **4.0 Cache Miss,** Get Client Item --> E
    E -- **4.1** Return Client Data --> C
    C -- **4.2** Update Redis Cache With Client Data --> D
    C -- **5** Return Client Data --> B
    B -- **6** Return Client Data --> A
```

### Create/Update Requests:
```mermaid
graph TD;
  subgraph Docker container in EC2 instance
    A[Python Test Script]
    B[Kafka]
    C[Kafka Go Subscriber]
    E[Redis Cache]
  end
  subgraph AWS cloud services
    D[AWS Lambda]
    F[DynamoDB]
  end
    A -- **1** Create/Update Client --> B
    B -- **2** Create/Update Client Topic --> C
    C -- **3** Create/Update Client Actions --> D
    D -- **4** Update Redis Cache With Client Data --> E
    D -- **5** Put/Update Client Item --> F
```

### CI/CD Flow:
```mermaid
graph TD;
  subgraph trigger
    A[Git Push to Master]
  end
  subgraph terraform job
    B[GitHub Actions: Terraform Setup AWS Lambda, DynamoDB, Routing]
  end
  subgraph build-and-push-docker job
    C[Build Docker Image With Services]
    D[Push Docker Image To Docker Hub]
  end
  subgraph deploy-and-test-aws job
    E[AWS EC2: Pull Docker Image]
    F[AWS EC2: Run Docker Container]
    G[AWS EC2: Run Tests in Docker Container]
    H[Create Test Report]
    I[Clean up AWS Cloud: Stop/Remove Docker container and image]
  end
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
```

### Example Client Data:
```json
{
    "id": "1",
    "first_name": "John",
    "second_name": "Doe",
    "phone": "555-1234"
}
```

## Prerequisites
- Docker
- AWS account and credentials (~/.aws/credentials)
- Terraform installed
- Go 1.21.1+
- Python 3.10+
- Redis
- Kafka

## Additional Features for Production

In a production environment, additional components and features may be required to ensure the robustness, security, and scalability of the application. Some of these additions include:

- **Monitoring and Logging**: Tools like Prometheus, Grafana, the ELK Stack (Elasticsearch, Logstash, Kibana), or AWS CloudWatch can be integrated to monitor application performance, track logs, and set up alerts for any issues that arise.
  
- **Authentication and Authorization**: Services like AWS Cognito, OAuth, or JWT (JSON Web Token) can be added to provide secure access to the application, ensuring that only authorized users can interact with the system.

- **Data Backup and Recovery**: Implementing AWS Backup or S3 for regular backups will help ensure that client data is secure and can be restored in case of data loss or corruption.

- **Scalability and Orchestration**: In production, the ability to scale the application based on demand is crucial. Tools like Kubernetes or AWS ECS (Elastic Container Service) can be used to automatically manage container scaling and orchestration.

- **Testing (Unit and Load Testing)**: For production-readiness, unit tests (JUnit, pytest) and load testing (Locust) can be added to ensure that the application performs well under expected traffic and stress scenarios.

- **Configuration Management**: AWS Parameter Store or HashiCorp Vault can be used to manage application configurations and sensitive data (e.g., API keys, credentials) securely, preventing hard-coding of secrets.

- **Secrets Management**: AWS Secrets Manager can be used to store and manage sensitive information such as database credentials, API keys, or third-party service tokens in a secure and scalable way.

These additions will enhance the application's production-readiness by ensuring better security, scalability, and performance management.