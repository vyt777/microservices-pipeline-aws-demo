provider "aws" {
  region = "us-east-1"
}

# Use existing VPC instead of creating a new one
data "aws_vpc" "existing_vpc" {
  id = "vpc-02c6973e498a1240d"
}

# Use existing subnet for Lambda and Redis
data "aws_subnet" "existing_subnet" {
  id = "subnet-067fcd4f2133d5a42"
}

# Use existing security group instead of creating a new one
data "aws_security_group" "existing_security_group" {
  id = "sg-05f550060decbf6d0"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"
  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [{
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }]
  })
}

# IAM policy for VPC access
resource "aws_iam_role_policy" "lambda_vpc_access_policy" {
  name = "lambda_vpc_access_policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        "Resource": "*"
      }
    ]
  })
}

# Attach basic execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach policy for DynamoDB full access to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_dynamodb_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

# Lambda function configuration with VPC access
resource "aws_lambda_function" "client_lambda" {
  function_name = "ClientManagementFunction"
  runtime       = "python3.10"
  handler       = "lambda_kafka_to_dynamodb.lambda_handler"
  role          = aws_iam_role.lambda_exec.arn

  environment {
    variables = {
      REDIS_HOST     = "ec2-54-174-139-195.compute-1.amazonaws.com"
      REDIS_PORT     = "6379"
      DYNAMODB_TABLE = aws_dynamodb_table.clients.name
    }
  }

  timeout = 5

  vpc_config {
    subnet_ids         = [data.aws_subnet.existing_subnet.id]
    security_group_ids = [data.aws_security_group.existing_security_group.id]
  }

  # Update Lambda function only if the ZIP file content changes
  filename      = "${path.module}/py/lambda_kafka_to_dynamodb.zip"
  source_code_hash = filebase64sha256("${path.module}/py/lambda_kafka_to_dynamodb.zip")
}

# Reuse existing EC2 instance for Redis
resource "aws_instance" "redis_instance" {
  ami           = "ami-0a0e5d9c7acc336f1"
  instance_type = "t2.micro"

  vpc_security_group_ids = [data.aws_security_group.existing_security_group.id]
  subnet_id              = data.aws_subnet.existing_subnet.id

  tags = {
    Name = "microservices-pipeline-aws-demo"
  }
}

# DynamoDB table configuration for clients
resource "aws_dynamodb_table" "clients" {
  name           = "Clients"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# VPC Gateway Endpoint for DynamoDB access
resource "aws_vpc_endpoint" "dynamodb_gateway" {
  vpc_id       = "vpc-02c6973e498a1240d"
  service_name = "com.amazonaws.us-east-1.dynamodb"
  vpc_endpoint_type = "Gateway"

  route_table_ids = ["rtb-0d162cc66b86bcb2e"]

  tags = {
    Name = "DynamoDBGatewayEndpoint"
  }
}
