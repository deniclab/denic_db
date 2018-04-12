from app import app
import boto3
import os

# initialize connection to S3 using the AWS python API
s3 = boto3.client('s3', aws_access_key_id=app.config['S3_ACCESS_KEY'],
                  aws_secret_access_key=app.config['S3_SECRET_KEY'])


def upload_file_to_s3(f, bucket_name, folder=None, acl='public-read'):
    """Upload a file object to an S3 storage bucket."""
    if folder:
        save_key = os.path.join(folder, f.filename)
    else:
        save_key = f.filename
    try:
        s3.upload_fileobj(
            f, bucket_name, save_key,
            ExtraArgs={'ACL': acl, 'ContentType': f.content_type})
    except Exception as e:
        # Catch-all exception.
        print('Something happened: ', e)
        return e

    return "{}{}".format(app.config['S3_LOCATION'], save_key)


def download_file_from_s3(filename, bucket_name, folder=None):
    """Download a file from S3 storage."""
    if folder:
        source_path = os.path.join(folder, filename)
    else:
        source_path = filename
    s3.download_file(bucket_name, source_path, filename)
