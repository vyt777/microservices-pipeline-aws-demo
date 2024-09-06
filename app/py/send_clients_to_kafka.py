import asyncio
from confluent_kafka import Producer
import grpc
import json
import get_item_pb2, get_item_pb2_grpc


# Set up Kafka and gRPC
producer = Producer({
    'bootstrap.servers': 'localhost:9092'
})
channel = grpc.insecure_channel('localhost:50051')
grpc_stub = get_item_pb2_grpc.GetItemServiceStub(channel)
create_clients_topic_name = 'create_clients'
update_clients_topic_name = 'update_clients'


def check_kafka_connection():
    """Check Kafka connection and topics"""
    try:
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

        return topics_exist
    except Exception as e:
        print(f'Failed to connect to Kafka: {e}')
        return False

def delivery_report(err, msg):
    """Callback function to handle delivery reports"""
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')


async def send_create_request(person):
    """Function to handle "create" requests"""
    print('Sending "create" request...')
    person_json = json.dumps(person)
    producer.produce(create_clients_topic_name, person_json.encode('utf-8'), callback=delivery_report)
    producer.flush()


async def send_update_request(person):
    """Function to handle "update" requests"""
    print('Sending "update" request...')
    person_json = json.dumps(person)
    producer.produce(update_clients_topic_name, person_json.encode('utf-8'), callback=delivery_report)
    producer.flush()


async def send_get_request(grpc_stub, person_id):
    """Function to handle "get" requests using gRPC"""
    print('Sending "get" request...')
    request = get_item_pb2.GetItemRequest(item_id=person_id)
    response = grpc_stub.GetItem(request)
    print(f'Received data: {response.item}')


async def main():
    if not check_kafka_connection():
        print("Exiting due to Kafka connection failure")
        exit(1)

    # Create clients
    clients_to_create = [
        {'First name': 'John', 'Second name': 'Doe', 'phone': '555-1234'},
        {'First name': 'Jane', 'Second name': 'Smith', 'phone': '555-5678'},
        {'First name': 'Jim', 'Second name': 'Beam', 'phone': '555-9876'},
        {'First name': 'Jack', 'Second name': 'Daniels', 'phone': '555-6543'},
        {'First name': 'Jill', 'Second name': 'Valentine', 'phone': '555-4321'}
    ]
    await asyncio.gather(*(send_create_request(client) for client in clients_to_create))

    # Get created clients
    client_ids_to_get = ['1', '2', '3', '4', '5']
    await asyncio.gather(*(send_get_request(grpc_stub, client_id) for client_id in client_ids_to_get))

    # Update clients
    clients_to_update = [
        {'First name': 'John', 'Second name': 'Doe', 'phone': '555-1000'},
        {'First name': 'Jane', 'Second name': 'Smith', 'phone': '555-2000'},
        {'First name': 'Jim', 'Second name': 'Beam', 'phone': '555-3000'},
        {'First name': 'Jack', 'Second name': 'Daniels', 'phone': '555-4000'},
        {'First name': 'Jill', 'Second name': 'Valentine', 'phone': '555-5000'}
    ]
    await asyncio.gather(*(send_update_request(client) for client in clients_to_update))

    # Get updated clients
    await asyncio.gather(*(send_get_request(grpc_stub, client_id) for client_id in client_ids_to_get))


if __name__ == "__main__":
    asyncio.run(main())
