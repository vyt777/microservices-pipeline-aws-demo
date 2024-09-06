package main

import (
    "fmt"
    "log"

    "github.com/confluentinc/confluent-kafka-go/kafka"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/lambda"
)

func main() {

    // Kafka configuration
    kafkaConfig := &kafka.ConfigMap{
        "bootstrap.servers": "localhost:9092",
        "group.id":          "go-consumer-group",
        "auto.offset.reset": "latest",
    }

    // Create a new Kafka consumer
    consumer, err := kafka.NewConsumer(kafkaConfig)
    if err != nil {
        log.Fatalf("Failed to create consumer: %s", err)
    }
    defer consumer.Close()

    // Subscribe to multiple topics
    consumer.SubscribeTopics([]string{"create_clients", "update_clients"}, nil)

    // AWS Lambda configuration
    sess := session.Must(session.NewSession(&aws.Config{
        Region: aws.String("us-east-2"),
    }))
    lambdaSvc := lambda.New(sess)

    fmt.Println("Starting Go subscriber...")

    for {
        // Poll for a message from Kafka
        msg, err := consumer.ReadMessage(-1)
        if err != nil {
            log.Printf("Consumer error: %v (%v)\n", err, msg)
            continue
        }

        // Log the received message and topic
        fmt.Printf("Received message from topic %s: %s\n", *msg.TopicPartition.Topic, string(msg.Value))

        // Process the message in a separate goroutine
        go func(message *kafka.Message) {

            var lambdaFunctionName string

            // Determine which Lambda function to call based on the topic
            switch *message.TopicPartition.Topic {
            case "create_clients":
                lambdaFunctionName = "CreateClientLambdaFunction"
            case "update_clients":
                lambdaFunctionName = "UpdateClientLambdaFunction"
            default:
                log.Printf("Unknown topic: %s\n", *message.TopicPartition.Topic)
                return
            }

            // Prepare the input for the Lambda function
            lambdaInput := &lambda.InvokeInput{
                FunctionName: aws.String(lambdaFunctionName),
                Payload:      message.Value,
            }

            // Invoke the Lambda function
            result, err := lambdaSvc.Invoke(lambdaInput)
            if err != nil {
                log.Printf("Failed to invoke Lambda function: %s", err)
                return
            }

            // Log the response from the Lambda function
            fmt.Printf("Lambda response: %s\n", string(result.Payload))

        }(msg)
    }
}
