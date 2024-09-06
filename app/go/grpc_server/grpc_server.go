package main

import (
    "context"
    "fmt" 
    "log"
    "net"

    pb "grpc_server/proto"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/lambda"
    "google.golang.org/grpc"
)

type server struct {
    pb.GetItemServiceServer
    lambdaClient *lambda.Lambda
}

func (s *server) GetItem(ctx context.Context, in *pb.GetItemRequest) (*pb.GetItemResponse, error) {
    itemID := in.GetItemId()

    log.Printf("Received GetItem request for ID: %s", itemID)

    payload := fmt.Sprintf(`{"action": "get", "id": "%s"}`, itemID)

    result, err := s.lambdaClient.Invoke(&lambda.InvokeInput{
        FunctionName: aws.String("MyLambdaFunction"),
        Payload:      []byte(payload),
    })

    if err != nil {
        log.Printf("Error invoking Lambda function: %s", err)
        return nil, err
    }

    log.Printf("Lambda function response: %s", string(result.Payload))

    return &pb.GetItemResponse{ItemId: itemID, ItemName: string(result.Payload)}, nil
}

func main() {
    lis, err := net.Listen("tcp", ":50051")
    if err != nil {
        log.Fatalf("failed to listen: %v", err)
    }

    s := grpc.NewServer()

    sess := session.Must(session.NewSession(&aws.Config{
        Region: aws.String("us-east-2"),
    }))
    lambdaClient := lambda.New(sess)

    pb.RegisterGetItemServiceServer(s, &server{
        lambdaClient: lambdaClient,
    })

    log.Printf("server listening at %v", lis.Addr())
    if err := s.Serve(lis); err != nil {
        log.Fatalf("failed to serve: %v", err)
    }
}
