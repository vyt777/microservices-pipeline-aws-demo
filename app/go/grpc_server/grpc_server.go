package main

import (
    "context"
    "fmt"
    "log"
    "net"
    "os"
    "encoding/json"

    pb "grpc_server/proto"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/credentials"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/lambda"
    "google.golang.org/grpc"
)

type server struct {
    pb.GetClientServiceServer
    lambdaClient *lambda.Lambda
}

type Client struct {
    Id         string `json:"id"`
    FirstName  string `json:"first_name"`
    SecondName string `json:"second_name"`
    Phone      string `json:"phone"`
}

func (s *server) GetClient(ctx context.Context, in *pb.GetClientRequest) (*pb.GetClientResponse, error) {
    clientID := in.GetId()

    log.Printf("Received GetClient request for ID: %s", clientID)

    payload := fmt.Sprintf(`{"action": "get_client", "id": "%s"}`, clientID)

    result, err := s.lambdaClient.Invoke(&lambda.InvokeInput{
        FunctionName: aws.String("ClientManagementFunction"),
        Payload:      []byte(payload),
    })

    if err != nil {
        log.Printf("Error invoking Lambda function: %s", err)
        return nil, err
    }

    log.Printf("Lambda function response: %s", string(result.Payload))

    var client Client
    err = json.Unmarshal(result.Payload, &client)
    if err != nil {
        log.Printf("Error unmarshaling Lambda response: %s", err)
        return nil, err
    }

    return &pb.GetClientResponse{
        Id:         client.Id,
        FirstName:  client.FirstName,
        SecondName: client.SecondName,
        Phone:      client.Phone,
    }, nil
}

func main() {
    lis, err := net.Listen("tcp", ":50051")
    if err != nil {
        log.Fatalf("failed to listen: %v", err)
    }

    s := grpc.NewServer()

    awsAccessKeyID := os.Getenv("AWS_ACCESS_KEY_ID")
    awsSecretAccessKey := os.Getenv("AWS_SECRET_ACCESS_KEY")
    awsRegion := os.Getenv("AWS_DEFAULT_REGION")

    sess := session.Must(session.NewSession(&aws.Config{
        Region:      aws.String(awsRegion),
        Credentials: credentials.NewStaticCredentials(awsAccessKeyID, awsSecretAccessKey, ""),
    }))
    lambdaClient := lambda.New(sess)

    pb.RegisterGetClientServiceServer(s, &server{
        lambdaClient: lambdaClient,
    })

    log.Printf("server listening at %v", lis.Addr())
    if err := s.Serve(lis); err != nil {
        log.Fatalf("failed to serve: %v", err)
    }
}
