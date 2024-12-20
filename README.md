# DIG (BioIndex) Indexer

This lambda function makes use of the code in the [BioIndex][bioindex] project to index files in S3 in parallel to dramatically speed up the process of indexing buckets.

## Quickstart

Install [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) if not already installed.  Then you package the lambda with: 
```bash
sam build
```

Then, you should be able to build and deploy the lambda function with (with project root as your workind directory):

```bash
sam deploy
```

If you make any changes and need to update the existing lambda function, simply follow the above steps again.

## Invoking

The lambda function should never be invoked directly. Instead, it should be called from the [BioIndex][bioindex] project when indexing via the CLI:

```bash
$ bioindex index <index_name> --use-lambda --workers 10
```

The `--workers` parameter defaults to 3, and is the number of parallel lambdas that will execute. This can be increased fairly high (e.g. 50) if necessary.

## Dependencies

The `requirements.txt` file contains all the Python (PIP) dependencies needed for the lambda function to execute. This should only really consist of:

1. The [BioIndex][bioindex] GitHub repository, tagged to a specific SHA (`@master` can be used, but updating can prove difficult).

2. The [PyMySQL][pymysql] module. This isn't needed by the BioIndex code, but it is necessary to make the lambda work.

## The Lambda

The actual lambda function code is in `handler.py` and is fairly straight-forward. It takes the parameters passed to it (the `event` parameter) and then proceeds to:

1. Lookup the secret for the RDS instance to connect to.
2. Connect to the RDS instance.
3. Lookup the index passed in the `event`.
4. Index the S3 bucket/key passed in to the `event`.
5. Write the index records to the database.
6. Return success, the key, and # of records written.

## Lambda Configuration

[template.yaml](template.yaml) is a cloud formation template that SAM uses to define the lambda and its dependencies.
The lambda needs to read files from s3, get secrets from the secrets manager, and write to an RDS instance. The first two requirements are handled via the Policies section.  The RDS connectivity is managed thanks to the VPC Config + AWSLambdaVPCAccessExecutionRole under policies. 

> VPC Lambda Internet Access
>
> By default, when a Lambda function is executed inside a VPC, it loses internet access and some resources inside AWS may become unavailable. In order for S3 resources and DynamoDB resources to be available for your Lambda function running inside the VPC, a VPC end point needs to be created. For more information please check VPC Endpoint for Amazon S3. In order for other services such as Kinesis streams to be made available, a NAT Gateway needs to be configured inside the subnets that are being used to run the Lambda, for the VPC used to execute the Lambda...

Two end-points for the correct AWS VPC have already been created (for S3 and the Secrets Manager). But, if something starts not working (timeouts), this is likely the culprit!!



