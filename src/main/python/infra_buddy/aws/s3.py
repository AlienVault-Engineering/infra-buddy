import mimetypes
import os
import tempfile
import urlparse
from zipfile import ZipFile

import boto3
import botocore
from boto3.s3.transfer import S3Transfer

from infra_buddy.utility import print_utility


class S3Buddy(object):
    def __init__(self, deploy_ctx, root_path, bucket_name):
        super(S3Buddy, self).__init__()
        self.deploy_ctx = deploy_ctx
        self.s3 = boto3.resource('s3', region_name=self.deploy_ctx.region)
        self.bucket = self.s3.Bucket(bucket_name)
        try:
            print_utility.info("S3Buddy using bucket_name={}, root_path={}".format(bucket_name, root_path))
            configuration = self._get_bucket_configuration()
            if configuration:
                self.bucket.create(CreateBucketConfiguration=configuration)
            else:
                self.bucket.create()
        except (botocore.exceptions.ValidationError, botocore.exceptions.ClientError) as err:
            if 'BucketAlreadyOwnedByYou' not in str(err):
                print_utility.info("Error during bucket create - {}".format(str(err)))
        self.bucket_name = bucket_name
        self.deploy_ctx = deploy_ctx
        self.s3 = boto3.resource('s3', region_name=self.deploy_ctx.region)
        self.key_root_path = root_path
        self.url_base = self._get_url_base()

    def _get_url_base(self):
        if self.deploy_ctx.region == 'us-east-1':
               return "https://s3.amazonaws.com/{bucket_name}".format(region=self.deploy_ctx.region,
                                                                      bucket_name=self.bucket_name)
        return "https://s3-{region}.amazonaws.com/{bucket_name}".format(region=self.deploy_ctx.region,
                                                                        bucket_name=self.bucket_name)

    def _get_bucket_configuration(self):
        if self.deploy_ctx.region == 'us-east-1':
            return None
        return {'LocationConstraint': self.deploy_ctx.region}

    def upload(self, file, key_name=None):
        key_name = self._get_upload_bucket_key_name(file, key_name)
        args = {"Key":key_name, "Body":open(file, 'rb')}
        content_type = self._guess_content_type(file)
        if content_type:
            args['ContentType'] = content_type
        self.bucket.put_object(**args)
        print_utility.info("Uploaded file to S3 - Bucket: {} Key: {} Content-Type: {}".format(self.bucket_name,
                                                                                              key_name,
                                                                                              content_type))
        return "{}/{}".format(self.url_base, key_name)

    def _get_upload_bucket_key_name(self, file, key_name=None):
        key_name = (key_name if key_name else os.path.basename(file))
        if self.key_root_path and self.key_root_path is not '':
            return "{path}/{key_name}".format(path=self.key_root_path,
                                              key_name=key_name)
        return key_name

    def get_file_as_string(self, filename):
        obj = self._get_s3_object(filename)
        return obj['Body'].read()

    def _get_s3_object(self, filename):
        key_name = self._get_upload_bucket_key_name(file=None, key_name=filename)
        obj = self.s3.meta.client.get_object(Bucket=self.bucket_name, Key=key_name)
        return obj

    def _guess_content_type(self,filename):
        """Given a filename, guess it's content type.
        If the type cannot be guessed, a value of None is returned.
        """
        try:
            return mimetypes.guess_type(filename)[0]
        # This catches a bug in the mimetype libary where some MIME types
        # specifically on windows machines cause a UnicodeDecodeError
        # because the MIME type in the Windows registery has an encoding
        # that cannot be properly encoded using the default system encoding.
        # https://bugs.python.org/issue9291
        #
        # So instead of hard failing, just log the issue and fall back to the
        # default guessed content type of None.
        except UnicodeDecodeError:
            LOGGER.debug(
                'Unable to guess content type for %s due to '
                'UnicodeDecodeError: ', filename, exc_info=True
            )



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
    print_utility.info("Downloading zip from s3: {} - {}:{}".format(s3_url, key, temp_file_path))
    s3.Bucket(bucket).download_file(key, temp_file_path)
    with ZipFile(temp_file_path) as zf:
        zf.extractall(destination)
