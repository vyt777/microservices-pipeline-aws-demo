import asyncio
from confluent_kafka import Producer
import grpc
import json
import get_item_pb2, get_item_pb2_grpc


# Set up Kafka and gRPC
producer = Producer({
    'bootstrap.servers': 'localhost:9092'
})
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


async def create_grpc_stub():
    return get_item_pb2_grpc.GetClientServiceStub(grpc.aio.insecure_channel('localhost:50051'))


def delivery_report(err, msg):
    """Callback function to handle delivery reports"""
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')


async def create_client(person):
    """Function to handle "create" requests"""
    print('Sending "create" request...')
    person_json = json.dumps(person)
    producer.produce(create_clients_topic_name, person_json.encode('utf-8'), callback=delivery_report)
    producer.flush()


async def update_client(person):
    """Function to handle "update" requests"""
    print('Sending "update" request...')
    person_json = json.dumps(person)
    producer.produce(update_clients_topic_name, person_json.encode('utf-8'), callback=delivery_report)
    producer.flush()


async def get_client(grpc_stub, person_id):
    """Function to handle "get" requests using gRPC"""
    print('Sending "get" request...')
    request = get_item_pb2.GetClientRequest(id=person_id)
    response = await grpc_stub.GetClient(request)
    print(f'Received response: {response}')


async def main():
    if not check_kafka_connection():
        print("Exiting due to Kafka connection failure")
        exit(1)

    grpc_stub = await create_grpc_stub()

    # # Create clients
    # clients_to_create = [
    #     {'first_name': 'John', 'second_name': 'Doe', 'phone': '555-1234'},
    #     {'first_name': 'Jane', 'second_name': 'Smith', 'phone': '555-5678'},
    #     {'first_name': 'Jim', 'second_name': 'Beam', 'phone': '555-9876'},
    #     {'first_name': 'Jack', 'second_name': 'Daniels', 'phone': '555-6543'},
    #     {'first_name': 'Jill', 'second_name': 'Valentine', 'phone': '555-4321'}
    # ]
    # await asyncio.gather(*(create_client(client) for client in clients_to_create))

    # Get created clients
    # client_ids_to_get = ['1', '2', '3', '4', '5']
    client_ids_to_get = ['test']
    await asyncio.gather(*(get_client(grpc_stub, client_id) for client_id in client_ids_to_get))

    # # Update clients
    # clients_to_update = [
    #     {'first_name': 'John', 'second_name': 'Doe', 'phone': '555-1000'},
    #     {'first_name': 'Jane', 'second_name': 'Smith', 'phone': '555-2000'},
    #     {'first_name': 'Jim', 'second_name': 'Beam', 'phone': '555-3000'},
    #     {'first_name': 'Jack', 'second_name': 'Daniels', 'phone': '555-4000'},
    #     {'first_name': 'Jill', 'second_name': 'Valentine', 'phone': '555-5000'}
    # ]
    # await asyncio.gather(*(update_client(client) for client in clients_to_update))
    #
    # # Get updated clients
    # await asyncio.gather(*(get_client(grpc_stub, client_id) for client_id in client_ids_to_get))


if __name__ == "__main__":
    asyncio.run(main())
