import redis
import boto3
import json

# Configure DynamoDB
try:
    table = boto3.resource('dynamodb').Table('Clients')
    print(f"Connected to DynamoDB table: {table}")
except Exception as e:
    print(f"Error connecting to DynamoDB: {str(e)}")

# Configure Redis
try:
    redis_client = redis.Redis(host='ec2-54-174-139-195.compute-1.amazonaws.com', port=6379, db=0, socket_timeout=3)
    redis_pong = redis_client.ping()
    print(f"Redis connection successful: {redis_pong}")
except Exception as e:
    print(f"Error connecting to Redis: {str(e)}")


# Threshold for increasing TTL (Time to Live)
TTL_THRESHOLD = 5
# Default TTL in seconds for less frequently accessed data
DEFAULT_TTL = 300
# Extended TTL in seconds for frequently accessed data
EXTENDED_TTL = 1800


def lambda_handler(event, context):
    """Lambda handler"""
    action = event.get('action')
    client_id = event.get('id')

    if action == 'get_client':
        return get_client(client_id)
    elif action == 'create_client':
        client_data = event.get('client_data')
        return create_client(client_id, client_data)
    elif action == 'update_client':
        client_data = event.get('client_data')
        return update_client(client_id, client_data)
    else:
        return {'status': 'error', 'message': 'Invalid action'}


def get_client(client_id):
    """Get client"""
    # Attempt to get data from cache
    print('Get Redis response')
    cached_client = redis_client.get(client_id)
    print(f'Redis returned client: {cached_client}')

    if cached_client:
        # If data is found in cache, increment the counter and update TTL
        redis_client.incr(f"{client_id}:count")
        request_count = int(redis_client.get(f"{client_id}:count"))
        print(f'Redis counter for this data: {request_count}')

        # If request count exceeds threshold, extend TTL
        if request_count > TTL_THRESHOLD:
            redis_client.expire(client_id, EXTENDED_TTL)
        return json.loads(cached_client)
    else:
        # If data is not in cache, fetch it from DynamoDB
        print('Get DynamoDB response')
        response = table.get_item(Key={'id': client_id})
        print(f'DynamoDB response: {response}')
        client = response.get('Item')
        print(f'DynamoDB returned client: {client}')

        if client:
            # Cache the data and set TTL
            redis_client.set(client_id, json.dumps(client))
            redis_client.set(f"{client_id}:count", 1)
            redis_client.expire(client_id, DEFAULT_TTL)
        return client


def create_client(client_id, client_data):
    """Create client"""
    # Save data in DynamoDB
    table.put_item(Item={'id': client_id, **client_data})

    # Cache the data in Redis
    redis_client.set(client_id, json.dumps(client_data))
    redis_client.set(f"{client_id}:count", 1)
    redis_client.expire(client_id, DEFAULT_TTL)
    return {'status': 'success'}


def update_client(client_id, client_data):
    """Update client"""
    # Update data in DynamoDB
    table.update_item(
        Key={'id': client_id},
        UpdateExpression="set info=:i",
        ExpressionAttributeValues={':i': client_data},
        ReturnValues="UPDATED_NEW"
    )

    # Update data in cache
    redis_client.set(client_id, json.dumps(client_data))
    redis_client.delete(f"{client_id}:count")
    redis_client.expire(client_id, DEFAULT_TTL)
    return {'status': 'success'}
