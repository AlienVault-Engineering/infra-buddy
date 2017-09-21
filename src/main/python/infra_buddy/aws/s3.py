import os
import tempfile
import urlparse
from zipfile import ZipFile

import boto3
import botocore

from infra_buddy.utility import print_utility


class S3Buddy(object):
    def __init__(self, deploy_ctx, root_path, bucket_name):
        super(S3Buddy, self).__init__()
        self.deploy_ctx = deploy_ctx
        self.s3 = boto3.resource('s3', region_name=self.deploy_ctx.region)
        self.bucket = self.s3.Bucket(bucket_name)
        try:
            self.bucket.create(CreateBucketConfiguration={'LocationConstraint': self.deploy_ctx.region})
        except (botocore.exceptions.ValidationError, botocore.exceptions.ClientError) as err:
            if 'BucketAlreadyOwnedByYou' not in str(err):
                print_utility.info("Error during bucket create - {}".format(str(err)))
        self.bucket_name = bucket_name
        self.deploy_ctx = deploy_ctx
        self.s3 = boto3.resource('s3', region_name=self.deploy_ctx.region)
        self.key_root_path = root_path
        self.url_base = "https://s3-{region}.amazonaws.com/{bucket_name}".format(region=self.deploy_ctx.region,
                                                                                 bucket_name=self.bucket_name)


    def upload(self, file, key_name=None):
        key_name = self._get_upload_bucket_key_name(file, key_name)
        self.bucket.put_object(Key=key_name, Body=open(file, 'rb'))
        print_utility.info("Uploaded file to S3 - Bucket: {} Key: {}".format(self.bucket_name, key_name))
        return "{}/{}".format(self.url_base, key_name)

    def _get_upload_bucket_key_name(self, file, key_name=None):
        key_name = (key_name if key_name else os.path.basename(file))
        if self.key_root_path and self.key_root_path is not '':
            return "{path}/{key_name}".format(path=self.key_root_path,
                                              key_name=key_name)
        return key_name

    def get_file_as_string(self, filename):
        key_name = self._get_upload_bucket_key_name(file=None, key_name=filename)
        return self.s3.meta.client.get_object(Bucket=self.bucket_name, Key=key_name)['Body'].read()


class CloudFormationDeployS3Buddy(S3Buddy):
    def __init__(self, deploy_ctx, ):
        super(CloudFormationDeployS3Buddy, self).__init__(deploy_ctx=deploy_ctx,
                                                          root_path=deploy_ctx.cf_deploy_resource_path,
                                                          bucket_name=deploy_ctx.cf_bucket_name)


def download_zip_from_s3_url(s3_url, destination):
    # type: (str, dest_directory) -> None
    parsed = urlparse.urlparse(s3_url)
    bucket = parsed.hostname
    key = parsed.path[1:]  # strip leading /
    s3 = boto3.resource('s3')
    with tempfile.NamedTemporaryFile() as temporary_file:
        temp_file_path = temporary_file.name
    s3.Bucket(bucket).download_file(key, temp_file_path)
    with ZipFile(temp_file_path) as zf:
        zf.extractall(destination)
