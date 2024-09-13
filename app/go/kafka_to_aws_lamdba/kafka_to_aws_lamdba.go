package main

import (
    "encoding/json"
    "fmt"
    "log"
    "os"

    "github.com/confluentinc/confluent-kafka-go/kafka"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/credentials"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/lambda"
)

// Client struct to match the data format
type Client struct {
    ID         string `json:"id"`
    FirstName  string `json:"first_name"`
    SecondName string `json:"second_name"`
    Phone      string `json:"phone"`
}

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

    // AWS Lambda configuration with credentials from environment variables
    awsAccessKeyID := os.Getenv("AWS_ACCESS_KEY_ID")
    awsSecretAccessKey := os.Getenv("AWS_SECRET_ACCESS_KEY")
    awsRegion := os.Getenv("AWS_DEFAULT_REGION")
    sess := session.Must(session.NewSession(&aws.Config{
        Region:      aws.String(awsRegion),
        Credentials: credentials.NewStaticCredentials(awsAccessKeyID, awsSecretAccessKey, ""),
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

        // Deserialize message into a Client struct
        var client Client
        err = json.Unmarshal(msg.Value, &client)
        if err != nil {
            log.Printf("Failed to unmarshal client data: %s", err)
            continue
        }

        // Process the message in a separate goroutine
        go func(client Client, topic string) {
            var action string

            // Determine which action to send to Lambda based on the topic
            switch topic {
            case "create_clients":
                action = "create_client"
            case "update_clients":
                action = "update_client"
            default:
                log.Printf("Unknown topic: %s\n", topic)
                return
            }

            // Prepare the payload for the Lambda function
            lambdaPayload := map[string]interface{}{
                "action":      action,
                "id":          client.ID,
                "client_data": client,
            }

            payload, err := json.Marshal(lambdaPayload)
            if err != nil {
                log.Printf("Failed to marshal client for Lambda: %s", err)
                return
            }

            lambdaInput := &lambda.InvokeInput{
                FunctionName: aws.String("ClientManagementFunction"), // Using the single Lambda function
                Payload:      payload,
            }

            // Invoke the Lambda function
            result, err := lambdaSvc.Invoke(lambdaInput)
            if err != nil {
                log.Printf("Failed to invoke Lambda function: %s", err)
                return
            }

            // Log the response from the Lambda function
            fmt.Printf("Lambda response: %s\n", string(result.Payload))

        }(client, *msg.TopicPartition.Topic)
    }
}
