"""
This module contains code for creating the required DynamoDB tables and load the tables with sample data
"""

import json
import boto3
import time
import uuid
from botocore.exceptions import ClientError
from dynamodb_json import json_util as ddb_json
#from retrying import retry
import csv
import os
import argparse


def read_csv_file(file_path: str):
    """
    read and process a csv file
    Args:
        file_path: the path to the csv file
    """
    print('current dir: ', os.getcwd())
    print('items in current directory', os.listdir())
    data_list = []
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                data_list.append(row)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return data_list


class DynamoDBTables:
    """
    Support class that allows for:
        - creation of the dynamodb table
        - Loading data to the dynamodb tables
        - Deletion of all resources created
    """

    def __init__(self, suffix=None):
        """
        Class initializer
        """
        boto3_session = boto3.session.Session()
        self.region_name = boto3_session.region_name
        self.iam_client = boto3_session.client("iam", region_name=self.region_name)
        self.account_number = (
            boto3.client("sts", region_name=self.region_name)
            .get_caller_identity()
            .get("Account")
        )
        if suffix is not None:
            self.suffix = suffix
        else:
            self.suffix = str(uuid.uuid4())[:4]
        self.identity = boto3.client(
            "sts", region_name=self.region_name
        ).get_caller_identity()["Arn"]
        self.dynamo_db_client = boto3_session.client(
            "dynamodb", region_name=self.region_name
        )

        self.ddb_table_name = None

    #@retry(wait_random_min=1000, wait_random_max=2000, stop_max_attempt_number=7)
    def create_dynamo_db_tables(
        self,
        ddb_table_name: str,
        ddb_partition_key: str = None,
        ddb_sort_key: str = None
    ):
        """
        Function used to create a new DynamoDB Table

        Args:
            ddb_table_name: DynamoDB Table Name - required
            ddb_partition_key: Partition Key for the table - required
            ddb_sort_key: Sort Key for the table - optional

        Returns:
            creation_status: True or False
        """
        # create a dynamodb table
        key_schema = [
            {
                "AttributeName": ddb_partition_key,
                "KeyType": "HASH",
            },
        ]
        attribute_definitions = [
                    {
                        "AttributeName": ddb_partition_key,
                        "AttributeType": "S",
                    },
                ]
        if ddb_sort_key is not None:
            key_schema.append(
                {
                    "AttributeName": ddb_sort_key,
                    "KeyType": "RANGE",
                }
            )
            attribute_definitions.append(
                {
                    "AttributeName": ddb_sort_key,
                    "AttributeType": "S",
                }
            )
        try:
            self.dynamo_db_client.create_table(
                TableName=ddb_table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            )
            print(f"Created DynamoDB Table: {ddb_table_name}")
            self.ddb_table_name = ddb_table_name
            return True
        except Exception as e:
            list_table_response = self.dynamo_db_client.list_tables(
                ExclusiveStartTableName=ddb_table_name,
                Limit=1
            )
            if len(list_table_response['TableNames']) == 1:
                self.dynamo_db_client.describe_table(
                    TableName=ddb_table_name
                )
                print(f"DynamoDB Table already exists: {ddb_table_name}. creation skipped")
                return True
            else:
                print(f"Error creating DynamoDB Table: {ddb_table_name}. Error: {e}")
                return False

    def load_data(self, ddb_table_name, ddb_file_path, ddb_file_type):
        """
        Load data to the DynamoDB table
        """
        # ensure that the kb is available
        i_status = ["CREATING", "DELETING", "UPDATING"]
        max_timeout = 300  # 5 minutes maximum timeout
        start_time = time.time()
        
        while (
            self.dynamo_db_client.describe_table(
                TableName=ddb_table_name
            )["Table"]["TableStatus"] in i_status
        ):
            # Check if we've exceeded the maximum timeout
            if time.time() - start_time > max_timeout:
                raise TimeoutError(
                    f"Timeout waiting for DynamoDB table '{ddb_table_name}' to become available. "
                    f"Table status check exceeded {max_timeout} seconds."
                )
            time.sleep(10) # nosemgrep
        # Start an ingestion job
        if ddb_file_type == 'csv':
            # read csv file and load data to dynamodb table
            table_data = read_csv_file(ddb_file_path)
            items_added = 0
            # create a dynamodb table with the list of items
            for table_item in table_data:
                ddb_table_item = ddb_json.dumps(table_item)
                json_table_data = json.loads(ddb_table_item)
                self.dynamo_db_client.put_item(
                    TableName=ddb_table_name,
                    Item=json_table_data,
                )
                items_added += 1
            print(f"Total items added: {items_added}")

    def delete_table(
        self,
        ddb_name: str,
    ):
        """
        Delete the DynamoDB Table
        Args:
            ddb_name: name of the DynamoDB Table to be deleted
        """
        try:
            self.dynamo_db_client.delete_table(TableName=ddb_name)
            print(f"Deleted DynamoDB Table: {ddb_name}")
        except ClientError as e:
            print(f"Error deleting DynamoDB Table: {e}")


if __name__ == "__main__":
    ddb_tables = DynamoDBTables()
    ddb_table_data = {
        "anycompany_product_inventory": {
            "file_path": "data_files/product_inventory/product_inventory.csv",
            "file_type": "csv",
            "partition_key": "product_id"
        },
        "anycompany_product_reviews": {
            "file_path": "data_files/product_reviews/product_reviews.csv",
            "file_type": "csv",
            "partition_key": "product_id"
        }
    }

    parser = argparse.ArgumentParser(description="Dynamo DB handler")
    parser.add_argument(
        "--mode",
        required=True,
        help="DynamoDB Helper Module. One for: create, delete.",
    )

    args = parser.parse_args()

    if args.mode == "load":
        tables_to_create = ddb_table_data.keys()
        for table_name in tables_to_create:
            ddb_tables.table_name = table_name
            #table_creation_status = ddb_tables.create_dynamo_db_tables(
            #    ddb_table_name=table_name,
            #    ddb_partition_key=ddb_table_data[table_name]["partition_key"],
            #    ddb_sort_key=ddb_table_data[table_name].get("sort_key", None)
            #)
            if True:
                ddb_tables.load_data(
                    ddb_table_name=table_name,
                    ddb_file_path=ddb_table_data[table_name]["file_path"],
                    ddb_file_type=ddb_table_data[table_name]["file_type"]
                    )
            else:
                print(f"Table {table_name} creation failed")
                exit(1)

    if args.mode == "delete":
        tables_to_create = ddb_table_data.keys()
        for table_name in tables_to_create:
            ddb_tables.table_name = table_name
            ddb_tables.delete_table(table_name)