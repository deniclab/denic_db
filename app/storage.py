from app import app


def upload_file_to_s3(f, acl="public-read"):
    try:
        s3.upload_fileobj(f, app.config['S3_BUCKET'], f.filename,
                          ExtraArgs={"ACL": acl,
                                     "ContentType": f.content_type})
    except Exception as e:
        # This is a catch all exception, edit this part to fit your needs.
        print("Something Happened: ", e)
        return e
    return "{}{}".format(app.config["S3_LOCATION"], f.filename)
