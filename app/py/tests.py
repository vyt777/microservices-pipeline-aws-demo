import os
import subprocess
import asyncio
from time import sleep
import json
import xmlrunner
import pytest
from confluent_kafka import Producer
import grpc
import get_item_pb2, get_item_pb2_grpc

# Kafka topics
create_clients_topic_name = 'create_clients'
update_clients_topic_name = 'update_clients'


def create_kafka_connection():
    """Create Kafka connection and check topics"""
    try:
        producer = Producer({
            'bootstrap.servers': 'localhost:9092'
        })
        metadata = producer.list_topics(timeout=5)
        topics_exist = True

        if create_clients_topic_name not in metadata.topics:
            print(f'Topic "{create_clients_topic_name}" does not exist')
            topics_exist = False

        if update_clients_topic_name not in metadata.topics:
            print(f'Topic "{update_clients_topic_name}" does not exist')
            topics_exist = False

        if topics_exist:
            print(f'Topics "{create_clients_topic_name}" and "{update_clients_topic_name}" exist')
            return producer

        return False
    except Exception as e:
        print(f'Failed to connect to Kafka: {e}')
        return False


async def create_grpc_stub():
    """Create gRPC stub for asynchronous usage"""
    return get_item_pb2_grpc.GetClientServiceStub(grpc.aio.insecure_channel('localhost:50051'))


def delivery_report(err, msg):
    """Callback function to handle delivery reports"""
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')


def send_to_kafka(producer, topic_name, message):
    """Synchronous function to send message to Kafka"""
    producer.produce(topic_name, message.encode('utf-8'), callback=delivery_report)
    producer.flush()


async def create_client(producer, client):
    """Asynchronous function to handle 'create' requests"""
    print(f'Sending "create" request with the client: {client}')
    client_json = json.dumps(client)
    await asyncio.to_thread(send_to_kafka, producer, create_clients_topic_name, client_json)


async def update_client(producer, client):
    """Asynchronous function to handle 'update' requests"""
    print(f'Sending "update" request with the client: {client}')
    client_json = json.dumps(client)
    await asyncio.to_thread(send_to_kafka, producer, update_clients_topic_name, client_json)


async def get_client(grpc_stub, client_id):
    """Asynchronous function to handle 'get' requests using gRPC"""
    print('Sending "get" request...')
    request = get_item_pb2.GetClientRequest(id=client_id)
    response = await grpc_stub.GetClient(request)
    print(f'Received response: {response}')
    return response


@pytest.fixture(scope="session", autouse=True)
async def setup():
    """Setup working environment before starting tests"""
    print("Clearing DynamoDB...")
    clear_dynamodb_script = os.path.join(os.path.dirname(__file__), 'clear_dynamodb.py')
    result = subprocess.run(['python3', clear_dynamodb_script], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error while clearing DynamoDB: {result.stderr}")
    else:
        print(f"Success: {result.stdout}")

    # Create the directory if it doesn't exist
    report_dir = os.path.join(os.path.dirname(__file__), 'test-reports')
    os.makedirs(report_dir, exist_ok=True)
    sleep(10)  # Wait for DynamoDB to be ready


@pytest.fixture(scope="function", autouse=True)
async def setup_connections():
    """Setup Kafka and gRPC connections before each test"""
    print("Establishing connection...")
    producer = create_kafka_connection()
    if not producer:
        pytest.fail("Failed to connect to Kafka")

    grpc_stub = await create_grpc_stub()
    return producer, grpc_stub


@pytest.mark.asyncio
async def test_create_and_verify_clients(setup_connections):
    """Create and get to check clients"""
    producer, grpc_stub = setup_connections
    clients_to_create = [
        {'id': '1', 'first_name': 'John', 'second_name': 'Doe', 'phone': '555-1234'},
        {'id': '2', 'first_name': 'Jane', 'second_name': 'Smith', 'phone': '555-5678'},
        {'id': '3', 'first_name': 'Jim', 'second_name': 'Beam', 'phone': '555-9876'},
        {'id': '4', 'first_name': 'Jack', 'second_name': 'Daniels', 'phone': '555-6543'},
        {'id': '5', 'first_name': 'Jill', 'second_name': 'Valentine', 'phone': '555-4321'}
    ]
    # Create clients
    await asyncio.gather(*(create_client(producer, client) for client in clients_to_create))
    sleep(5)  # Wait for DynamoDB to be updated

    # Verify clients
    for client in clients_to_create:
        response = await get_client(grpc_stub, client['id'])
        assert response.first_name == client['first_name']
        assert response.second_name == client['second_name']
        assert response.phone == client['phone']


@pytest.mark.asyncio
async def test_update_and_verify_clients(setup_connections):
    """Update and get to check clients"""
    producer, grpc_stub = setup_connections
    clients_to_update = [
        {'id': '1', 'first_name': 'John', 'second_name': 'Doe', 'phone': '555-1000'},
        {'id': '2', 'first_name': 'Jane', 'second_name': 'Smith', 'phone': '555-2000'},
        {'id': '3', 'first_name': 'Jim', 'second_name': 'Beam', 'phone': '555-3000'},
        {'id': '4', 'first_name': 'Jack', 'second_name': 'Daniels', 'phone': '555-4000'},
        {'id': '5', 'first_name': 'Jill', 'second_name': 'Valentine', 'phone': '555-5000'}
    ]
    # Update clients
    await asyncio.gather(*(update_client(producer, client) for client in clients_to_update))
    sleep(5)  # Wait for DynamoDB to be updated

    # Verify updated clients
    for client in clients_to_update:
        response = await get_client(grpc_stub, client['id'])
        assert response.first_name == client['first_name']
        assert response.second_name == client['second_name']
        assert response.phone == client['phone']
