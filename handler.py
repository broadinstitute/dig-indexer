import json
import os
import pymysql

from bioindex.lib.config import Config
from bioindex.lib.migrate import migrate
from bioindex.lib.index import Index


# This lambda uses the dig-bioindex repository code to index a single
# S3 object into an index table. It is only ever intended to be invoked
# from the dig-bioindex package using the index command:
#
#  $ bioindex index <index_name> [args] --use-lambda
#
# The package will discover all the objects that need indexed and then
# invoke a lambda for each one so they can be indexed in parallel very
# quickly.
#
# Upon success, it returns the KEY of the S3 object that was indexed
# and the number of records that were inserted into the database.


def main(event, context):
    pymysql.install_as_MySQLdb()

    # extract environment settings
    index_name = event.get('index')
    rds_secret = event.get('rds_secret')
    rds_schema = event.get('rds_schema')
    s3_bucket = event.get('s3_bucket')
    s3_obj = event.get('s3_obj')

    # setup the configuration object
    config = Config(
        BIOINDEX_S3_BUCKET=s3_bucket,
        BIOINDEX_RDS_SECRET=rds_secret,
        BIOINDEX_BIO_SCHEMA=rds_schema,
    )

    # connect to the BioIndex MySQL database
    print(f'Connecting to {rds_secret}/{rds_schema}...')
    engine = migrate(config)
    assert engine, 'Failed to connect to RDS instance'

    # find the index by name
    print(f'Looking up index {index_name}')
    index = Index.lookup(engine, index_name)
    assert index, 'Failed to find index'

    # get the list of records to insert
    print(f'Indexing s3://{s3_bucket}/{s3_obj["Key"]}')
    s3_key, records = index.index_object(engine, s3_bucket, s3_obj)
    records = list(records)

    # bulk insert them into the table
    print(f'Inserting {len(records):,} records')
    index.insert_records_batched(engine, records)

    # done
    print('Done!')

    # return the key, record count, and total size
    return {
        'statusCode': 200,
        'body': {
            'key': s3_key,
            'records': len(records),
            'size': s3_obj['Size'],
        },
    }
