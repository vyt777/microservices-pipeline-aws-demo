import boto3
from time import sleep

table_name = 'Clients'
dynamodb = boto3.client('dynamodb')


def delete_table(table_name):
    try:
        dynamodb.delete_table(TableName=table_name)
        print(f'Table "{table_name}" deletion initiated')
    except dynamodb.exceptions.ResourceNotFoundException:
        print(f'Table "{table_name}" not found, skipping deletion')


def wait_for_table_deletion(table_name):
    while True:
        try:
            dynamodb.describe_table(TableName=table_name)
            print(f'Table "{table_name}" still exists, waiting...')
            sleep(5)
        except dynamodb.exceptions.ResourceNotFoundException:
            print(f'Table "{table_name}" deleted successfully')
            break


def recreate_table(table_name):
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'  # Primary key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'  # String type for 'id'
            }
        ],
        BillingMode='PAY_PER_REQUEST'  # Change to 'PROVISIONED' if you want to manually set capacity units
    )
    print(f'Table "{table_name}" creation initiated')


print(f'Deleting table "{table_name}"')
delete_table(table_name)
print('Waiting for the table to be deleted')
wait_for_table_deletion(table_name)
print(f'Creating new table "{table_name}"')
recreate_table(table_name)
print('Done')