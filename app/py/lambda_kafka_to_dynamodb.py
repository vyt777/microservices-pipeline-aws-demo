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
    item_id = event.get('id')

    if action == 'get':
        return get_item(item_id)
    elif action == 'create':
        item_data = event.get('item_data')
        return create_item(item_id, item_data)
    elif action == 'update':
        item_data = event.get('item_data')
        return update_item(item_id, item_data)
    else:
        return {'status': 'error', 'message': 'Invalid action'}


def get_item(item_id):
    """Get item"""
    # Attempt to get data from cache
    print('Get Redis response')
    cached_item = redis_client.get(item_id)
    print(f'Redis returned item: {cached_item}')

    if cached_item:
        # If data is found in cache, increment the counter and update TTL
        redis_client.incr(f"{item_id}:count")
        request_count = int(redis_client.get(f"{item_id}:count"))
        print(f'Redis counter for this data: {request_count}')

        # If request count exceeds threshold, extend TTL
        if request_count > TTL_THRESHOLD:
            redis_client.expire(item_id, EXTENDED_TTL)
        return json.loads(cached_item)
    else:
        # If data is not in cache, fetch it from DynamoDB
        print('Get DynamoDB response')
        response = table.get_item(Key={'id': item_id})
        print(f'DynamoDB response: {response}')
        item = response.get('Item')
        print(f'DynamoDB returned item: {item}')

        if item:
            # Cache the data and set TTL
            redis_client.set(item_id, json.dumps(item))
            redis_client.set(f"{item_id}:count", 1)
            redis_client.expire(item_id, DEFAULT_TTL)
        return item


def create_item(item_id, item_data):
    """Create item"""
    # Save data in DynamoDB
    table.put_item(Item={'id': item_id, **item_data})

    # Cache the data in Redis
    redis_client.set(item_id, json.dumps(item_data))
    redis_client.set(f"{item_id}:count", 1)
    redis_client.expire(item_id, DEFAULT_TTL)
    return {'status': 'success'}


def update_item(item_id, item_data):
    """Update item"""
    # Update data in DynamoDB
    table.update_item(
        Key={'id': item_id},
        UpdateExpression="set info=:i",
        ExpressionAttributeValues={':i': item_data},
        ReturnValues="UPDATED_NEW"
    )

    # Update data in cache
    redis_client.set(item_id, json.dumps(item_data))
    redis_client.delete(f"{item_id}:count")
    redis_client.expire(item_id, DEFAULT_TTL)
    return {'status': 'success'}
