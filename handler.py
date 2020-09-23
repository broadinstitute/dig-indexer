import json
import os
import pymysql

from bioindex.lib.aws import connect_to_db, secret_lookup
from bioindex.lib.config import Config
from bioindex.lib.tables import lookup_index
from bioindex.lib.index import _index_object, _bulk_insert
from bioindex.lib.s3 import read_object


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
    index_name = event.get('index')
    rds_instance = event.get('rds_instance')
    s3_bucket = event.get('s3_bucket')
    s3_obj = event.get('s3_obj')

    # get _mysql
    pymysql.install_as_MySQLdb()

    # test secrets
    print(f'Loading connection settings for {rds_instance}')
    rds_connection_settings = secret_lookup(rds_instance)

    # connect to the BioIndex MySQL database
    print(f'Connecting to {rds_instance}')
    engine = connect_to_db(**rds_connection_settings)
    assert engine, 'Failed to connect to RDS instance'

    # find the index by name
    print(f'Looking up index {index_name}')
    index = lookup_index(engine, index_name)
    assert index, 'Failed to find index'

    # get the list of records to insert
    print(f'Indexing s3://{s3_bucket}/{s3_obj["Key"]}')
    s3_key, records = _index_object(engine, s3_bucket, s3_obj, index)
    records = list(records)

    # bulk insert them into the table
    print(f'Inserting {len(records):,} records')
    _bulk_insert(engine, index.table, records)

    print('Done!')
    return {
        'statusCode': 200,
        'body': {
            'key': s3_key,
            'records': len(records),
            'size': s3_obj['Size'],
        },
    }


if __name__ == '__main__':
    main({
        'index': 'genes',
        'rds_instance': 'dig-bio-index',
        's3_bucket': 'dig-bio-index',
        's3_obj': {
            'Key': 'genes/part-00000-7aba68ef-0133-4e4d-82ce-1fe9f9e5fb8b-c000.json',
        },
    })
